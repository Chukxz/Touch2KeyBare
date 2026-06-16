from __future__ import annotations
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
    from multiprocessing.connection import Connection

MAX_COALESCE = 20
DOWN_TUPLE = (LEFT_BUTTON_DOWN, RIGHT_BUTTON_DOWN, MIDDLE_BUTTON_DOWN)

# In seconds
CONSTANT_DWELL = 0.001
MIN_BUTTON_DWELL = 0.025
MAX_BUTTON_DWELL = 0.04
MIN_MOUSE_DWELL = 0.0008
MAX_MOUSE_DWELL = 0.0012


def _release_all_keys(k_ctx, k_handle, K_Stroke, keys_set, reason=""):
    """Helper to cleanly release all currently pressed keys."""
    print(f"\n[UTILITY] - {reason}.")
    if keys_set:
        print("\n[UTILITY] - Releasing {len(keys_set)} keys.")
        for code in list(keys_set):
            k_ctx.send(k_handle, K_Stroke(code, 1))  # 1 = UP
        keys_set.clear()


def _release_all_buttons(
    m_ctx, m_handle, M_Stroke, left_down, right_down, middle_down, reason=""
):
    print(f"\n[UTILITY] - {reason}.")
    buttons_set_sum = sum([left_down, right_down, middle_down])
    if buttons_set_sum > 0:
        print(f"\n[UTILITY] - Releasing {buttons_set_sum} buttons.")
        if left_down:
            m_ctx.send(
                m_handle,
                M_Stroke(MOUSE_MOVE_RELATIVE, LEFT_BUTTON_UP, 0, 0, 0),
            )
        if right_down:
            m_ctx.send(
                m_handle,
                M_Stroke(MOUSE_MOVE_RELATIVE, RIGHT_BUTTON_UP, 0, 0, 0),
            )
        if middle_down:
            m_ctx.send(
                m_handle,
                M_Stroke(MOUSE_MOVE_RELATIVE, MIDDLE_BUTTON_UP, 0, 0, 0),
            )


# Worker: Keyboard (Pipe + Binary Protocol)
def keyboard_worker(k_pipe_read: Connection):
    """Dedicated process for Windows Interception driver keyboard events (Lock-Free Pipe)."""

    from interception.interception import Interception
    from interception.strokes import KeyStroke
    from mapper_module.utils import PACK_KEY

    k_ctx = Interception()
    k_handle = k_ctx.keyboard
    # Keep track of keys we've pressed so we know what to release
    pressed_keys = set()
    running = True

    while running:
        try:
            # Wait up to 15 seconds for data
            if k_pipe_read.poll(15.0):
                payload = k_pipe_read.recv_bytes()
                code, state = PACK_KEY.unpack(payload)

                # Windows logic sends state=0 for down, state=1 for up.
                if state == 0:
                    pressed_keys.add(code)
                elif state == 1:
                    pressed_keys.discard(code)

                k_ctx.send(k_handle, KeyStroke(code, state))

            else:
                # Timeout logic for stuck buttons
                _release_all_keys(
                    k_ctx, k_handle, KeyStroke, pressed_keys, "Keyboard Timeout"
                )
                pressed_keys.clear()
                continue

        except EOFError:
            print("\n[UTILITY] - Keyboard Pipe closed by parent.")
            running = False

        except Exception as e:
            print(f"\n[UTILITY] - Keyboard Worker crashed: {e}.")
            running = False


# Worker: Mouse (Isolated with Coalescing, Pipe + Binary Protocol)
def mouse_worker(m_pipe_read: Connection):
    """Dedicated process for Windows Interception driver mouse events (Lock-Free Pipe)."""

    import ctypes

    ctypes.windll.ntdll.NtSetTimerResolution(
        NT_TIMER_RES, 1, ctypes.byref(ctypes.c_ulong())
    )

    from time import sleep as _sleep
    from random import uniform as _uniform
    from interception.interception import Interception
    from interception.strokes import MouseStroke
    from mapper_module.utils import (
        TASK_BUTTON,
        TASK_REL,
        TASK_ABS,
        PACK_BUTTON,
        PACK_REL,
        PACK_ABS,
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
            if pending_task:
                payload = pending_task
                task_id = pending_task[0]  # The first byte is always our Task ID
                pending_task = None
            else:
                # Wait up to 15 seconds for new data
                if m_pipe_read.poll(15.0):
                    # Instantly grab the raw byte payload without unpickling
                    payload = m_pipe_read.recv_bytes()
                    task_id = payload[0]  # The first byte is always our Task ID
                else:
                    # Timeout logic for stuck buttons
                    _release_all_buttons(
                        m_ctx,
                        m_handle,
                        MouseStroke,
                        left_down,
                        right_down,
                        middle_down,
                        "Mouse Timeout",
                    )
                    left_down = right_down = middle_down = False
                    continue

            # -----------------------------------------
            # HANDLE BUTTONS
            # -----------------------------------------
            if task_id == TASK_BUTTON:
                # Unpack expects a tuple, we grab the first element
                _, data = PACK_BUTTON.unpack(payload)

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

            # -----------------------------------------
            # HANDLE RELATIVE MOVEMENT (Coalescing)
            # -----------------------------------------
            elif task_id == TASK_REL:
                # Unpack the initial dx, dy
                _, dx, dy = PACK_REL.unpack(payload)
                acc_dx += dx
                acc_dy += dy

                coalesce_count = 0
                # Fast polling to drain the pipe
                while m_pipe_read.poll() and coalesce_count < MAX_COALESCE:
                    next_payload = m_pipe_read.recv_bytes()
                    next_task_id = next_payload[
                        0
                    ]  # The first byte is always our Task ID

                    if next_task_id == TASK_REL:
                        _, next_dx, next_dy = PACK_REL.unpack(next_payload)
                        acc_dx += next_dx
                        acc_dy += next_dy
                        coalesce_count += 1
                    else:
                        pending_task = next_payload
                        break

                if acc_dx != 0 or acc_dy != 0:
                    m_ctx.send(
                        m_handle,
                        MouseStroke(MOUSE_MOVE_RELATIVE, 0, 0, acc_dx, acc_dy),
                    )
                    acc_dx, acc_dy = 0, 0

                _sleep(_uniform(MIN_MOUSE_DWELL, MAX_MOUSE_DWELL))

            # -----------------------------------------
            # HANDLE ABSOLUTE MOVEMENT
            # -----------------------------------------
            elif task_id == TASK_ABS:
                _, x, y = PACK_ABS.unpack(payload)
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
            print(f"\n[UTILITY] - Mouse Pipe closed by parent.")
            running = False

        except Exception as e:
            print(f"\n[UTILITY] - Mouse Worker crashed: {e}.")
            running = False
