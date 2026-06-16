from __future__ import annotations
from typing import TYPE_CHECKING

from mapper_module.utils import (
    LEFT_BUTTON_DOWN,
    LEFT_BUTTON_UP,
    RIGHT_BUTTON_DOWN,
    RIGHT_BUTTON_UP,
    MIDDLE_BUTTON_DOWN,
    MIDDLE_BUTTON_UP,
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


def _release_all_keys(ui_device, ecodes, keys_set, reason=""):
    """Helper to cleanly release all currently pressed keys."""
    if keys_set:
        print(f"\n[UTILITY] - {reason}. Releasing {len(keys_set)} keys.")
        for code in list(keys_set):
            ui_device.write(ecodes.EV_KEY, code, 0)  # 0 = UP
        ui_device.syn()
        keys_set.clear()


def _release_all_buttons(
    ui_device, ecodes, left_down, right_down, middle_down, reason=""
):
    print(f"\n[UTILITY] - {reason}.")
    buttons_set_sum = sum([left_down, right_down, middle_down])
    if buttons_set_sum > 0:
        print(f"\n[UTILITY] - Releasing {buttons_set_sum} buttons.")
        if left_down:
            ui_device.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0)
        if right_down:
            ui_device.write(ecodes.EV_KEY, ecodes.BTN_RIGHT, 0)
        if middle_down:
            ui_device.write(ecodes.EV_KEY, ecodes.BTN_MIDDLE, 0)
        ui_device.syn()


# Worker: Keyboard (Pipe + Binary Protocol)
def keyboard_worker(k_pipe_read: Connection):
    """Dedicated process for Linux evdev virtual keyboard (Lock-Free Pipe)."""

    from evdev import UInput, ecodes
    from mapper_module.utils import PACK_KEY

    cap = {ecodes.EV_KEY: list(range(1, 256))}
    ui_device = UInput(cap, name="Touch2Key-Keyboard")

    pressed_keys = set()
    running = True

    while running:
        try:
            # Wait up to 15 seconds for data
            if k_pipe_read.poll(15.0):
                payload = k_pipe_read.recv_bytes()
                code, state = PACK_KEY.unpack(payload)

                # Linux logic sends state=1 for down, state=0 for up.
                if state == 1:
                    pressed_keys.add(code)
                elif state == 0:
                    pressed_keys.discard(code)

                ui_device.write(ecodes.EV_KEY, code, state)
                ui_device.syn()

            else:
                # Timeout logic for stuck buttons
                _release_all_keys(ui_device, ecodes, pressed_keys, "Keyboard Timeout")
                pressed_keys.clear()
                continue
                
        except EOFError:
            print("\n[UTILITY] - Keyboard Pipe closed by parent.")
            running = False

        except Exception as e:
            print(f"\n[UTILITY] - Keyboard Worker crashed: {e}.")
            running = False
    ui_device.close()


# Worker: Mouse (Isolated with Coalescing, Pipe + Binary Protocol)
def mouse_worker(m_pipe_read: Connection):
    """Dedicated process for Linux evdev virtual mouse (Lock-Free Pipe)."""

    from time import sleep as _sleep
    from random import uniform as _uniform
    from evdev import UInput, ecodes, AbsInfo
    from mapper_module.utils import (
        TASK_BUTTON,
        TASK_REL,
        TASK_ABS,
        PACK_BUTTON,
        PACK_REL,
        PACK_ABS,
    )

    # Define Mouse Capabilities
    cap = {
        ecodes.EV_KEY: [ecodes.BTN_LEFT, ecodes.BTN_RIGHT, ecodes.BTN_MIDDLE],
        ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y, ecodes.REL_WHEEL],
        ecodes.EV_ABS: [
            (
                ecodes.ABS_X,
                AbsInfo(value=0, min=0, max=65535, fuzz=0, flat=0, resolution=0),
            ),
            (
                ecodes.ABS_Y,
                AbsInfo(value=0, min=0, max=65535, fuzz=0, flat=0, resolution=0),
            ),
        ],
    }
    ui_device = UInput(cap, name="Touch2Key-Mouse")

    # Mapping Windows button constants to Linux
    BTN_MAP = {
        LEFT_BUTTON_DOWN: (ecodes.BTN_LEFT, 1),
        LEFT_BUTTON_UP: (ecodes.BTN_LEFT, 0),
        RIGHT_BUTTON_DOWN: (ecodes.BTN_RIGHT, 1),
        RIGHT_BUTTON_UP: (ecodes.BTN_RIGHT, 0),
        MIDDLE_BUTTON_DOWN: (ecodes.BTN_MIDDLE, 1),
        MIDDLE_BUTTON_UP: (ecodes.BTN_MIDDLE, 0),
    }

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
                # Wait up to 15 seconds for data
                if m_pipe_read.poll(15.0):
                    # Instantly grab the raw byte payload without unpickling
                    payload = m_pipe_read.recv_bytes()
                    task_id = payload[0]  # The first byte is always our Task ID
                else:
                    # Timeout logic for stuck buttons
                    _release_all_buttons(ui_device, ecodes, left_down, right_down, middle_down, "Mouse Timeout")
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

                btn_code, btn_val = BTN_MAP[data]
                ui_device.write(ecodes.EV_KEY, btn_code, btn_val)
                ui_device.syn()

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
                    next_task_id = next_payload[0]  # The first byte is always our Task ID

                    if next_task_id == TASK_REL:
                        _, next_dx, next_dy = PACK_REL.unpack(next_payload)
                        acc_dx += next_dx
                        acc_dy += next_dy
                        coalesce_count += 1
                    else:
                        pending_task = next_payload
                        break

                if acc_dx != 0 or acc_dy != 0:
                    ui_device.write(ecodes.EV_REL, ecodes.REL_X, acc_dx)
                    ui_device.write(ecodes.EV_REL, ecodes.REL_Y, acc_dy)
                    ui_device.syn()
                    acc_dx, acc_dy = 0, 0

                _sleep(_uniform(MIN_MOUSE_DWELL, MAX_MOUSE_DWELL))

            # -----------------------------------------
            # HANDLE ABSOLUTE MOVEMENT
            # -----------------------------------------
            elif task_id == TASK_ABS:
                _, x, y = PACK_ABS.unpack(payload)
                ui_device.write(ecodes.EV_ABS, ecodes.ABS_X, x)
                ui_device.write(ecodes.EV_ABS, ecodes.ABS_Y, y)
                ui_device.syn()
                _sleep(CONSTANT_DWELL)

        except EOFError:
            print(f"\n[UTILITY] - Mouse Pipe closed by parent.")
            running = False

        except Exception as e:
            print(f"\n[UTILITY] - Mouse Worker crashed: {e}.")
            running = False

    ui_device.close()
