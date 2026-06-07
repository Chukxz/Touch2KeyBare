from __future__ import annotations
from typing import TYPE_CHECKING
import queue
from time import sleep as _sleep
from random import uniform as _uniform

from mapper_module.utils import (
    LEFT_BUTTON_DOWN, LEFT_BUTTON_UP,
    RIGHT_BUTTON_DOWN, RIGHT_BUTTON_UP, MIDDLE_BUTTON_DOWN, 
    MIDDLE_BUTTON_UP
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
    """ Dedicated process for Linux evdev virtual keyboard. """
    from evdev import UInput, ecodes

    # Create a virtual keyboard capable of sending all standard keys
    cap = {ecodes.EV_KEY: list(range(1, 256))}
    ui = UInput(cap, name="Touch2Key-Keyboard")

    pressed_keys = set()
    running = True

    while running:
        try:
            code, state = k_queue.get(timeout=15.0)

            # LINUX DIFFERENCE: Linux evdev uses 1 for DOWN and 0 for UP.
            # Your Windows logic sends state=0 for down, state=1 for up. 
            linux_value = 1 if state == 0 else 0

            if linux_value == 1:
                pressed_keys.add(code)
            else:
                pressed_keys.discard(code)

            ui.write(ecodes.EV_KEY, code, linux_value)
            ui.syn() # Crucial in Linux: syncs the event to the OS          

        except queue.Empty:           
            if pressed_keys:
                print(f"\n[UTILITY] - Keyboard timeout. Releasing {len(pressed_keys)} keys.")
                for code in list(pressed_keys):
                    ui.write(ecodes.EV_KEY, code, 0) # 0 = UP
                    ui.syn()
                pressed_keys.clear()
            continue

        except Exception as e:
            print(f"\n[UTILITY] - Keyboard Worker crashed: {e}")
            if pressed_keys:
                for code in list(pressed_keys):
                    ui.write(ecodes.EV_KEY, code, 0)
                    ui.syn()
            running = False
    ui.close()

# Worker: Mouse (Isolated with Coalescing)
def mouse_worker(m_queue: Queue):
    """ Dedicated process for Linux evdev virtual mouse. """
    from evdev import UInput, ecodes, AbsInfo

    # Define Mouse Capabilities
    cap = {
        ecodes.EV_KEY: [ecodes.BTN_LEFT, ecodes.BTN_RIGHT, ecodes.BTN_MIDDLE],
        ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y, ecodes.REL_WHEEL],
        ecodes.EV_ABS: [
            # Max 65535 maps proportionally to screen size in X11/Wayland
            (ecodes.ABS_X, AbsInfo(value=0, min=0, max=65535, fuzz=0, flat=0, resolution=0)),
            (ecodes.ABS_Y, AbsInfo(value=0, min=0, max=65535, fuzz=0, flat=0, resolution=0))
        ]
    }
    ui = UInput(cap, name="Touch2Key-Mouse")

    # Mapping Windows button constants to Linux (Button Code, Value)
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
                task, data = pending_task
                pending_task = None
            else:
                task, data = m_queue.get(timeout=15.0)

            if task == "button":
                if data == LEFT_BUTTON_DOWN: left_down = True
                elif data == LEFT_BUTTON_UP: left_down = False
                elif data == RIGHT_BUTTON_DOWN: right_down = True
                elif data == RIGHT_BUTTON_UP: right_down = False
                elif data == MIDDLE_BUTTON_DOWN: middle_down = True
                elif data == MIDDLE_BUTTON_UP: middle_down = False

                btn_code, btn_val = BTN_MAP[data]
                ui.write(ecodes.EV_KEY, btn_code, btn_val)
                ui.syn()

                if data in DOWN_TUPLE:
                    _sleep(_uniform(MIN_BUTTON_DWELL, MAX_BUTTON_DWELL))
                else:
                    _sleep(CONSTANT_DWELL)

            elif task == "move_rel":
                acc_dx += data[0]
                acc_dy += data[1]

                coalesce_count = 0
                while not m_queue.empty() and coalesce_count < MAX_COALESCE:
                    try:
                        next_task, next_data = m_queue.get_nowait()
                        if next_task == "move_rel":
                            acc_dx += next_data
                            acc_dy += next_data
                            coalesce_count += 1
                        else:
                            pending_task = (next_task, next_data)
                            break 
                    except queue.Empty: 
                        break

                if acc_dx != 0 or acc_dy != 0:
                    ui.write(ecodes.EV_REL, ecodes.REL_X, acc_dx)
                    ui.write(ecodes.EV_REL, ecodes.REL_Y, acc_dy)
                    ui.syn()
                    acc_dx, acc_dy = 0, 0

                _sleep(_uniform(MIN_MOUSE_DWELL, MAX_MOUSE_DWELL))

            elif task == "move_abs":
                x, y = data
                ui.write(ecodes.EV_ABS, ecodes.ABS_X, x)
                ui.write(ecodes.EV_ABS, ecodes.ABS_Y, y)
                ui.syn()
                _sleep(CONSTANT_DWELL)

        except queue.Empty:
            pressed_buttons = sum([left_down, right_down, middle_down])
            if pressed_buttons > 0:
                print(f"\n[UTILITY] - Mouse worker timed out. Releasing {pressed_buttons} buttons.")
                if left_down: ui.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0)
                if right_down: ui.write(ecodes.EV_KEY, ecodes.BTN_RIGHT, 0)
                if middle_down: ui.write(ecodes.EV_KEY, ecodes.BTN_MIDDLE, 0)
                ui.syn()
                left_down = right_down = middle_down = False
            continue

        except Exception as e:
            pressed_buttons = sum([left_down, right_down, middle_down])
            print(f"\n[UTILITY] - Mouse Worker crashed: {e}. Releasing {pressed_buttons} buttons.")
            if left_down: ui.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0)
            if right_down: ui.write(ecodes.EV_KEY, ecodes.BTN_RIGHT, 0)
            if middle_down: ui.write(ecodes.EV_KEY, ecodes.BTN_MIDDLE, 0)
            ui.syn()
            running = False

    ui.close()
