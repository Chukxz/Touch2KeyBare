from __future__ import annotations
from typing import TYPE_CHECKING
import threading

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
    KEY_PING,
    BUTTON_PING,
)

if TYPE_CHECKING:
    from multiprocessing.connection import Connection


def _release_all_keys(k_ctx, k_handle, K_Stroke, keys_set, reason=""):
    print(f"\n[WORKER] - {reason}.")
    if keys_set:
        print(f"\n[WORKER] - Releasing {len(keys_set)} keys.")
        for code in list(keys_set):
            k_ctx.send(k_handle, K_Stroke(code, 1))  # 1 = UP
        keys_set.clear()


def _release_all_buttons(
    m_ctx, m_handle, M_Stroke, left_down, right_down, middle_down, reason=""
):
    print(f"\n[WORKER] - {reason}.")
    buttons_set_sum = sum([left_down, right_down, middle_down])
    if buttons_set_sum > 0:
        print(f"\n[WORKER] - Releasing {buttons_set_sum} buttons.")
        if left_down:
            m_ctx.send(m_handle, M_Stroke(MOUSE_MOVE_RELATIVE, LEFT_BUTTON_UP, 0, 0, 0))
        if right_down:
            m_ctx.send(
                m_handle, M_Stroke(MOUSE_MOVE_RELATIVE, RIGHT_BUTTON_UP, 0, 0, 0)
            )
        if middle_down:
            m_ctx.send(
                m_handle, M_Stroke(MOUSE_MOVE_RELATIVE, MIDDLE_BUTTON_UP, 0, 0, 0)
            )


def keyboard_worker(k_pipe_read: Connection):
    """Dedicated process for Windows Interception driver keyboard events."""

    from interception.interception import Interception
    from interception.strokes import KeyStroke
    from mapper_module.utils import PACK_KEY

    k_ctx = Interception()
    k_handle = k_ctx.keyboard
    pressed_keys = set()
    running = True

    while running:
        try:
            if k_pipe_read.poll(15.0):
                payload = k_pipe_read.recv_bytes()
                code, state = PACK_KEY.unpack(payload)

                if state == KEY_PING:
                    continue  # keepalive only: resets poll() timer, no driver write

                # Windows logic sends state=0 for down, state=1 for up.
                if state == 0:
                    pressed_keys.add(code)
                elif state == 1:
                    pressed_keys.discard(code)

                k_ctx.send(k_handle, KeyStroke(code, state))

            else:
                _release_all_keys(
                    k_ctx, k_handle, KeyStroke, pressed_keys, "Keyboard Timeout"
                )
                pressed_keys.clear()
                continue

        except EOFError:
            print("\n[WORKER] - Keyboard Pipe closed by parent.")
            running = False

        except Exception as e:
            print(f"\n[WORKER] - Keyboard Worker crashed: {e}.")
            running = False


def mouse_worker(m_pipe_read: Connection, mb_pipe_read: Connection):
    """Movement (REL/ABS) runs on this function's main loop. Buttons run on
    a separate thread with their own pipe, so a button's dwell sleep can
    never block camera-movement delivery. Both share one Interception mouse
    handle behind `send_lock`, which wraps only the send() call, not sleeps."""

    import ctypes

    ctypes.windll.ntdll.NtSetTimerResolution(
        NT_TIMER_RES, 1, ctypes.byref(ctypes.c_ulong())
    )

    from time import sleep as _sleep
    from random import uniform as _uniform
    from interception.interception import Interception
    from interception.strokes import MouseStroke
    from mapper_module.utils import (
        TASK_REL,
        TASK_ABS,
        PACK_BUTTON,
        PACK_REL,
        PACK_ABS,
        MAX_COALESCE,
        DOWN_TUPLE,
        CONSTANT_DWELL,
        MIN_BUTTON_DWELL,
        MAX_BUTTON_DWELL,
        MIN_MOUSE_DWELL,
        MAX_MOUSE_DWELL,
    )

    m_ctx = Interception()
    m_handle = m_ctx.mouse
    send_lock = threading.Lock()
    state = {"running": True}

    def button_loop():
        left_down = right_down = middle_down = False
        while state["running"]:
            try:
                if mb_pipe_read.poll(15.0):
                    payload = mb_pipe_read.recv_bytes()
                    _, data = PACK_BUTTON.unpack(payload)

                    if data == BUTTON_PING:
                        continue

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

                    with send_lock:
                        m_ctx.send(
                            m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, data, 0, 0, 0)
                        )

                    if data in DOWN_TUPLE:
                        _sleep(_uniform(MIN_BUTTON_DWELL, MAX_BUTTON_DWELL))
                    else:
                        _sleep(CONSTANT_DWELL)

                else:
                    with send_lock:
                        _release_all_buttons(
                            m_ctx,
                            m_handle,
                            MouseStroke,
                            left_down,
                            right_down,
                            middle_down,
                            "Mouse Button Timeout",
                        )
                    left_down = right_down = middle_down = False

            except EOFError:
                print("\n[WORKER] - Mouse Button Pipe closed by parent.")
                state["running"] = False

            except Exception as e:
                print(f"\n[WORKER] - Mouse Button Worker crashed: {e}.")
                state["running"] = False

    button_thread = threading.Thread(
        target=button_loop, name="Mouse-Button-Loop", daemon=True
    )
    button_thread.start()

    acc_dx, acc_dy = 0, 0
    pending_task = None

    while state["running"]:
        try:
            if pending_task:
                payload = pending_task
                task_id = pending_task[0]
                pending_task = None
            else:
                if m_pipe_read.poll(15.0):
                    payload = m_pipe_read.recv_bytes()
                    task_id = payload[0]
                else:
                    continue  # buttons live on their own pipe/thread now

            if task_id == TASK_REL:
                _, dx, dy = PACK_REL.unpack(payload)
                acc_dx += dx
                acc_dy += dy

                coalesce_count = 0
                while m_pipe_read.poll() and coalesce_count < MAX_COALESCE:
                    next_payload = m_pipe_read.recv_bytes()
                    next_task_id = next_payload[0]

                    if next_task_id == TASK_REL:
                        _, next_dx, next_dy = PACK_REL.unpack(next_payload)
                        acc_dx += next_dx
                        acc_dy += next_dy
                        coalesce_count += 1
                    else:
                        pending_task = next_payload
                        break

                if acc_dx != 0 or acc_dy != 0:
                    with send_lock:
                        m_ctx.send(
                            m_handle,
                            MouseStroke(MOUSE_MOVE_RELATIVE, 0, 0, acc_dx, acc_dy),
                        )
                    acc_dx, acc_dy = 0, 0

                _sleep(_uniform(MIN_MOUSE_DWELL, MAX_MOUSE_DWELL))

            elif task_id == TASK_ABS:
                _, x, y = PACK_ABS.unpack(payload)
                with send_lock:
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
            print("\n[WORKER] - Mouse Movement Pipe closed by parent.")
            state["running"] = False

        except Exception as e:
            print(f"\n[WORKER] - Mouse Movement Worker crashed: {e}.")
            state["running"] = False
