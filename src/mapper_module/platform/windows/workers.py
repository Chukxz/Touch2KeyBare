from __future__ import annotations
from typing import TYPE_CHECKING

import time
import random
import ctypes
from mapper_module.utils import (
    MOUSE_MOVE_RELATIVE, MOUSE_MOVE_ABSOLUTE, MOUSE_VIRTUAL_DESKTOP,
    LEFT_BUTTON_DOWN, LEFT_BUTTON_UP,
    RIGHT_BUTTON_DOWN, RIGHT_BUTTON_UP, MIDDLE_BUTTON_DOWN, 
    MIDDLE_BUTTON_UP, NT_TIMER_RES
)

if TYPE_CHECKING:
    from multiprocessing import Process
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
            code, state = k_queue.get(timeout=15.0)

            if state == 0:
                pressed_keys.add(code)
            else:
                pressed_keys.discard(code)
            
            k_ctx.send(k_handle, KeyStroke(code, state))
  
        except Exception:
            if pressed_keys:
                print(f"\n[UTILITY] - Keyboard worker timeout. Releasing {len(pressed_keys)} keys.")
                for code in list(pressed_keys):
                    k_ctx.send(k_handle, KeyStroke(code, 1))
                pressed_keys.clear()
            running = False

# Worker: Mouse (Isolated with Coalescing)
def mouse_worker(m_queue:Queue):
    """ Dedicated process for Mouse events only (Windows Interception driver). """
    ctypes.windll.ntdll.NtSetTimerResolution(NT_TIMER_RES, 1, ctypes.byref(ctypes.c_ulong()))
        
    from interception import Interception, MouseStroke

    m_ctx = Interception()
    m_handle = m_ctx.mouse
    
    acc_dx, acc_dy = 0, 0
    pending_task = None
    
    left_down = False
    right_down = False
    middle_down = False
    running = True

    MAX_COALESCE = 20  
    MIN_DWELL = 0.025 
    DELTA_DWELL = 0.015
    DOWN_TUPLE = (LEFT_BUTTON_DOWN, RIGHT_BUTTON_DOWN, MIDDLE_BUTTON_DOWN)

    while running:
        try:
            if pending_task:
                task, data = pending_task
                pending_task = None
            else:
                task, data = m_queue.get(timeout=15.0)

            if task == "button":
                m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, data, 0, 0, 0))
                
                if data == LEFT_BUTTON_DOWN: left_down = True
                elif data == LEFT_BUTTON_UP: left_down = False
                elif data == RIGHT_BUTTON_DOWN: right_down = True
                elif data == RIGHT_BUTTON_UP: right_down = False
                elif data == MIDDLE_BUTTON_DOWN: middle_down = True
                elif data == MIDDLE_BUTTON_UP: middle_down = False
                
                if data in DOWN_TUPLE:
                     time.sleep(MIN_DWELL + random.random() * DELTA_DWELL)
                else:
                    time.sleep(0.005) 

            elif task == "move_rel":
                acc_dx += data
                acc_dy += data

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
                    except Exception: 
                        break

                if acc_dx != 0 or acc_dy != 0:
                    m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, MOUSE_MOVE_RELATIVE, 0, acc_dx, acc_dy))
                    acc_dx, acc_dy = 0, 0
                
                time.sleep(0.0005)

            elif task == "move_abs":
                x, y = data
                m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_ABSOLUTE | MOUSE_VIRTUAL_DESKTOP, MOUSE_MOVE_ABSOLUTE, 0, x, y))
                time.sleep(0.001)

        except Exception: 
            print("\n[UTILITY] - Mouse worker timeout. Releasing buttons.")
            if left_down:
                m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, LEFT_BUTTON_UP, 0, 0, 0))
            if right_down:
                m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, RIGHT_BUTTON_UP, 0, 0, 0))
            if middle_down:
                m_ctx.send(m_handle, MouseStroke(MOUSE_MOVE_RELATIVE, MIDDLE_BUTTON_UP, 0, 0, 0))
            running = False
