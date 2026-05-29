from __future__ import annotations
from typing import TYPE_CHECKING

from mapper_module.utils import (
    MOUSE_MOVE_RELATIVE, MOUSE_MOVE_ABSOLUTE, MOUSE_VIRTUAL_DESKTOP,
    LEFT_BUTTON_DOWN, LEFT_BUTTON_UP,
    RIGHT_BUTTON_DOWN, RIGHT_BUTTON_UP, MIDDLE_BUTTON_DOWN, 
    MIDDLE_BUTTON_UP, NT_TIMER_RES
)

if TYPE_CHECKING:
    from multiprocessing import Queue
    
# Worker: Keyboard (Isolated)
def keyboard_worker(k_queue:Queue):
    """ Dedicated process for Keyboard events only (Windows Interception driver). """
    
    from interception import Interception, KeyStroke
    
    k_ctx = Interception()
    k_handle = k_ctx.keyboard
    # Keep track of keys we've pressed so we know what to release
    pressed_keys = set()
    running = True
    
    while running:
        try:
            code, state = k_queue.get(timeout=0.5)

            if state == 0:
                pressed_keys.add(code)
            else:
                pressed_keys.discard(code)
            
            k_ctx.send(k_handle, KeyStroke(code, state))            
  
        except Exception as e:           
            if pressed_keys:
                print(f"\n[UTILITY] - Keyboard worker timeout. Releasing {len(pressed_keys)} keys.")
                for code in list(pressed_keys):
                    k_ctx.send(k_handle, KeyStroke(code, 1))
                pressed_keys.clear()
            
            # Queue is empty, continue the loop
            if k_queue.empty():
                continue
            
            # An error occured, end the loop
            else:
                print(f"\n[UTILITY] - Releasing {len(pressed_keys)} keys.\nKeyboard Worker crashed: {e}")
                running = False

# Worker: Mouse (Isolated with Coalescing)
def mouse_worker(m_queue:Queue):
    """ Dedicated process for Mouse events only (Windows Interception driver). """
    
    import ctypes
    from time import sleep as _sleep
    from random import uniform as _uniform
    from interception import Interception, MouseStroke

    ctypes.windll.ntdll.NtSetTimerResolution(NT_TIMER_RES, 1, ctypes.byref(ctypes.c_ulong()))
    m_ctx = Interception()
    m_handle = m_ctx.mouse
    
    acc_dx, acc_dy = 0, 0
    pending_task = None
    
    left_down = False
    right_down = False
    middle_down = False
    running = True

    MAX_COALESCE = 20
    DOWN_TUPLE = (LEFT_BUTTON_DOWN, RIGHT_BUTTON_DOWN, MIDDLE_BUTTON_DOWN)
    
    # In seconds
    CONSTANT_DWELL = 0.001
    MIN_BUTTON_DWELL = 0.025 
    MAX_BUTTON_DWELL = 0.04
    MIN_MOUSE_DWELL = 0.0008
    MAX_MOUSE_DWELL = 0.0012
    
    while running:
        try:
            if pending_task:
                task, data = pending_task
            else:
                task, data = m_queue.get(timeout=0.5)
            
            if task == "button":
                m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, data, 0, 0, 0))
                
                if data == LEFT_BUTTON_DOWN: left_down = True
                elif data == LEFT_BUTTON_UP: left_down = False
                elif data == RIGHT_BUTTON_DOWN: right_down = True
                elif data == RIGHT_BUTTON_UP: right_down = False
                elif data == MIDDLE_BUTTON_DOWN: middle_down = True
                elif data == MIDDLE_BUTTON_UP: middle_down = False
                
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
                            acc_dx += next_data[0]
                            acc_dy += next_data[1]
                            coalesce_count += 1
                        else:
                            pending_task = (next_task, next_data)
                            break 
                    except Exception: 
                        break

                if acc_dx != 0 or acc_dy != 0:
                    m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, MOUSE_MOVE_RELATIVE, 0, acc_dx, acc_dy))
                    acc_dx, acc_dy = 0, 0
                
                _sleep(_uniform(MIN_MOUSE_DWELL, MAX_MOUSE_DWELL))

            elif task == "move_abs":
                x, y = data
                m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_ABSOLUTE | MOUSE_VIRTUAL_DESKTOP, MOUSE_MOVE_ABSOLUTE, 0, x, y))
                _sleep(CONSTANT_DWELL)

        except Exception as e: 
            print("\n[UTILITY] - Mouse worker timeout. Releasing buttons.")
            if left_down:
                m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, LEFT_BUTTON_UP, 0, 0, 0))
            if right_down:
                m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, RIGHT_BUTTON_UP, 0, 0, 0))
            if middle_down:
                m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, MIDDLE_BUTTON_UP, 0, 0, 0))

            # Queue is empty, continue the loop
            if m_queue.empty():
                continue
            
            # An error occured, end the loop
            else:
                print(f"\n[UTILITY] - Releasing buttons.\nMouse Worker crashed: {e}")
                running = False
                