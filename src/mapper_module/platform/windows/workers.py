from __future__ import annotations
import queue
from typing import TYPE_CHECKING

from mapper_module.utils import (
    MOUSE_MOVE_RELATIVE,
    MOUSE_MOVE_ABSOLUTE,
    MOUSE_VIRTUAL_DESKTOP,
    LEFT_BUTTON_DOWN,
    LEFT_BUTTON_UP,
    RIGHT_BUTTON_DOWN,
    RIGHT_BUTTON_UP,
    MIDDLE_BUTTON_DOWN,
    MIDDLE_BUTTON_UP,
    NT_TIMER_RES,
)

if TYPE_CHECKING:
    from multiprocessing import Queue

MAX_COALESCE = 20
DOWN_TUPLE = (LEFT_BUTTON_DOWN, RIGHT_BUTTON_DOWN, MIDDLE_BUTTON_DOWN)

# In seconds
CONSTANT_DWELL = 0.001
MIN_BUTTON_DWELL = 0.025
MAX_BUTTON_DWELL = 0.04
MIN_MOUSE_DWELL = 0.0008
MAX_MOUSE_DWELL = 0.0012


# Worker: Keyboard (Isolated)
def keyboard_worker(k_queue: Queue):
    """Dedicated process for Keyboard events only (Windows Interception driver)."""

    from interception.interception import Interception
    from interception.strokes import KeyStroke

    k_ctx = Interception()
    k_handle = k_ctx.keyboard
    # Keep track of keys we've pressed so we know what to release
    pressed_keys = set()
    running = True

    while running:
        try:
            code, state = k_queue.get(timeout=15.0)

            # Windows logic sends state=0 for down, state=1 for up.
            if state == 0:
                pressed_keys.add(code)
            else:
                pressed_keys.discard(code)

            k_ctx.send(k_handle, KeyStroke(code, state))

        except queue.Empty:
            # 15 seconds passed with no input. Flush keys just in case.
            if pressed_keys:
                print(
                    f"\n[UTILITY] - Keyboard worker timed out. Releasing {len(pressed_keys)} keys."
                )
                for code in list(pressed_keys):
                    k_ctx.send(k_handle, KeyStroke(code, 1))
                pressed_keys.clear()
            continue

        except Exception as e:
            # Fatal error/crash
            print(f"\n[UTILITY] - Keyboard Worker crashed: {e}")
            if pressed_keys:
                print(f"[UTILITY] - Releasing {len(pressed_keys)} keys before exit.")
                for code in list(pressed_keys):
                    k_ctx.send(k_handle, KeyStroke(code, 1))
            running = False


# Worker: Mouse (Isolated with Coalescing + Lock-Free Pipe)
def mouse_worker(m_pipe_child):
    """Dedicated process for Mouse events only (Windows Interception driver)."""

    import ctypes
    from time import sleep as _sleep
    from random import uniform as _uniform
    from interception.interception import Interception
    from interception.strokes import MouseStroke

    ctypes.windll.ntdll.NtSetTimerResolution(
        NT_TIMER_RES, 1, ctypes.byref(ctypes.c_ulong())
    )
    m_ctx = Interception()
    m_handle = m_ctx.mouse

    acc_dx, acc_dy = 0, 0
    pending_task = None

    left_down = False
    right_down = False
    middle_down = False
    running = True

    while running:
        try:
            # Check for a pending task from the previous coalesce loop
            if pending_task:
                task, data = pending_task
                pending_task = None  # CRITICAL FIX: Clear the task
            else:
                # Wait up to 15 seconds for new data
                if m_pipe_child.poll(15.0):
                    task, data = m_pipe_child.recv()
                else:
                    # 15 seconds passed with no input. Release stuck buttons
                    pressed_buttons = sum([left_down, right_down, middle_down])
                    if pressed_buttons > 0:
                        print(f"\n[UTILITY] - Mouse worker timed out. Releasing {pressed_buttons} buttons.")
                        if left_down:
                            m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, LEFT_BUTTON_UP, 0, 0, 0))
                        if right_down:
                            m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, RIGHT_BUTTON_UP, 0, 0, 0))
                        if middle_down:
                            m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, MIDDLE_BUTTON_UP, 0, 0, 0))
                        left_down = right_down = middle_down = False
                    continue

            if task == "button":
                if data == LEFT_BUTTON_DOWN:
                    left_down = True
                elif data == LEFT_BUTTON_UP:
                    left_down = False
                elif data == RIGHT_BUTTON_DOWN:
                    right_down = True
                elif data == RIGHT_BUTTON_UP:
                    right_down = False
                elif data == MIDDLE_BUTTON_DOWN:
                    middle_down = True
                elif data == MIDDLE_BUTTON_UP:
                    middle_down = False

                m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, data, 0, 0, 0))

                if data in DOWN_TUPLE:
                    _sleep(_uniform(MIN_BUTTON_DWELL, MAX_BUTTON_DWELL))
                else:
                    _sleep(CONSTANT_DWELL)

            elif task == "move_rel":
                acc_dx += data
                acc_dy += data

                coalesce_count = 0
                # Use poll() instead of empty() - practically zero overhead
                while m_pipe_child.poll() and coalesce_count < MAX_COALESCE:
                    next_task, next_data = m_pipe_child.recv()
                    
                    if next_task == "move_rel":
                        acc_dx += next_data
                        acc_dy += next_data
                        coalesce_count += 1
                    else:
                        pending_task = (next_task, next_data)
                        break

                if acc_dx != 0 or acc_dy != 0:
                    m_ctx.send(
                        m_handle,
                        MouseStroke(
                            MOUSE_MOVE_RELATIVE, MOUSE_MOVE_RELATIVE, 0, acc_dx, acc_dy
                        ),
                    )
                    acc_dx, acc_dy = 0, 0

                _sleep(_uniform(MIN_MOUSE_DWELL, MAX_MOUSE_DWELL))

            elif task == "move_abs":
                x, y = data
                m_ctx.send(
                    m_handle,
                    MouseStroke(
                        MOUSE_MOVE_ABSOLUTE | MOUSE_VIRTUAL_DESKTOP,
                        MOUSE_MOVE_ABSOLUTE,
                        0,
                        x,
                        y,
                    ),
                )
                _sleep(CONSTANT_DWELL)

        except EOFError:
            # The parent closed the pipe (Scorched Earth reset)
            print("\n[UTILITY] - Mouse Pipe closed by parent.")
            running = False

        except Exception as e:
            # Fatal error/crash
            pressed_buttons = sum([left_down, right_down, middle_down])
            print(f"\n[UTILITY] - Mouse Worker crashed: {e}")
            if pressed_buttons > 0:
                print(f"[UTILITY] - Releasing {pressed_buttons} buttons before exit.")
                if left_down:
                    m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, LEFT_BUTTON_UP, 0, 0, 0))
                if right_down:
                    m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, RIGHT_BUTTON_UP, 0, 0, 0))
                if middle_down:
                    m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, MIDDLE_BUTTON_UP, 0, 0, 0))
            running = False