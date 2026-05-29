from ..base import AbstractBridge
import multiprocessing
import threading
from datetime import datetime as _datetime
from .workers import keyboard_worker, mouse_worker
from .system import SystemConfig

from mapper_module.utils import (
    LEFT_BUTTON_DOWN, LEFT_BUTTON_UP,
    RIGHT_BUTTON_DOWN, RIGHT_BUTTON_UP, 
    MIDDLE_BUTTON_DOWN, MIDDLE_BUTTON_UP,
    SCANCODES, M_LEFT, M_RIGHT, M_MIDDLE,
)

class InterceptionBridge(AbstractBridge):
    def __init__(self, window_manager):
        self.window_manager = window_manager
        self.screen_w, self.screen_h = window_manager.get_screen_metrics()
        self.bridge_lock = threading.RLock()

        self.k_queue = multiprocessing.Queue()
        self.k_proc = multiprocessing.Process(
            target=keyboard_worker,
            name="Keyboard Worker",
            args=(self.k_queue,),
            daemon=True
        )

        self.m_queue = multiprocessing.Queue(maxsize=64)
        self.m_proc = multiprocessing.Process(
            target=mouse_worker,
            name="Mouse Worker",
            args=(self.m_queue,),
            daemon=True
        )

        self.k_proc.start()
        self.m_proc.start()

        print(f"\n[BRIDGE] - Dual Engine Started. "
              f"K-PID: {self.k_proc.pid} | "
              f"M-PID: {self.m_proc.pid}.")

    # Keyboard API
    def key_down(self, code): self.k_queue.put((code, 0))
    def key_up(self, code): self.k_queue.put((code, 1))

    # Mouse API
    def mouse_move_rel(self, dx, dy):
        try:
            self.m_queue.put_nowait(("move_rel", (dx, dy)))
        except Exception: pass

    def mouse_move_abs(self, x, y):
        abs_x = int((x * 65535) / self.screen_w)
        abs_y = int((y * 65535) / self.screen_h)
        try:
            self.m_queue.put_nowait(("move_abs", (abs_x, abs_y)))
        except Exception: pass

    def left_click_down(self):
        try:
            self.m_queue.put(("button", LEFT_BUTTON_DOWN), timeout=0.05)
        except Exception: pass

    def left_click_up(self):
        try:
            self.m_queue.put(("button", LEFT_BUTTON_UP), timeout=0.05)
        except Exception: pass

    def right_click_down(self):
        try:
            self.m_queue.put(("button", RIGHT_BUTTON_DOWN), timeout=0.05)
        except Exception: pass

    def right_click_up(self):
        try:
            self.m_queue.put(("button", RIGHT_BUTTON_UP), timeout=0.05)
        except Exception: pass

    def middle_click_down(self):
        try:
            self.m_queue.put(("button", MIDDLE_BUTTON_DOWN), timeout=0.05)
        except Exception: pass

    def middle_click_up(self):
        try:
            self.m_queue.put(("button", MIDDLE_BUTTON_UP), timeout=0.05)
        except Exception: pass

    def health_check(self):
        with self.bridge_lock:
            # Check Keyboard Worker
            if not self.k_proc.is_alive():
                print(f"\n[UTILITY] - Keyboard Worker Died: {_datetime.now().strftime('%H:%M:%S')}!")
                self.k_proc = multiprocessing.Process(target=keyboard_worker, name="Keyboard Worker", args=(self.k_queue,), daemon=True)
                self.k_proc.start()
                # Re-apply High Priority to the new PID
                SystemConfig().set_high_priority(self.k_proc.pid, "Revived Keyboard")
                # Safety: Clear the queue to prevent a backlog of old 'stuck' keys firing at once
                while not self.k_queue.empty():
                    try: self.k_queue.get_nowait()
                    except Exception: break

            # Check Mouse Worker
            if not self.m_proc.is_alive():
                print(f"\n[UTILITY] - Mouse Worker Died: {_datetime.now().strftime('%H:%M:%S')}!")
                self.m_proc = multiprocessing.Process(target=mouse_worker, name="Mouse Worker", args=(self.m_queue,), daemon=True)
                self.m_proc.start()
                # Re-apply High Priority to the new PID
                SystemConfig().set_high_priority(self.m_proc.pid, "Revived Mouse")
                # Safety: Clear the queue to prevent a backlog of old 'stuck' mouse movements firing at once
                while not self.m_queue.empty():
                    try: self.m_queue.get_nowait()
                    except Exception: break

    def release_all(self):
        print("\n[BRIDGE] - Emergency Release...")
        with self.bridge_lock:
            self.health_check()
            for btn_up in [LEFT_BUTTON_UP, RIGHT_BUTTON_UP, MIDDLE_BUTTON_UP]:
                self.m_queue.put(("button", btn_up))
            internal_mouse_codes = {M_LEFT, M_RIGHT, M_MIDDLE}
            unique_codes = set(SCANCODES.values()) - internal_mouse_codes
            for code in unique_codes:
                self.k_queue.put((code, 1))
        print("[BRIDGE] - Release signals dispatched.")