from ..base import AbstractBridge
import multiprocessing
import threading
import queue
from datetime import datetime as _datetime
from .workers import keyboard_worker, mouse_worker

from mapper_module.utils import (
    LEFT_BUTTON_DOWN,
    LEFT_BUTTON_UP,
    RIGHT_BUTTON_DOWN,
    RIGHT_BUTTON_UP,
    MIDDLE_BUTTON_DOWN,
    MIDDLE_BUTTON_UP,
    SCANCODES,
    M_LEFT,
    M_RIGHT,
    M_MIDDLE,
)


class InterceptionBridge(AbstractBridge):
    def __init__(self, window_manager, system_config):
        self.window_manager = window_manager
        self.system_config = system_config
        self.screen_w, self.screen_h = window_manager.get_screen_dimensions()
        self.bridge_lock = threading.RLock()

        self.k_queue = multiprocessing.Queue()
        self.k_proc = multiprocessing.Process(
            target=keyboard_worker,
            name="Keyboard Worker",
            args=(self.k_queue,),
            daemon=True,
        )

        self.m_pipe_parent, self.m_pipe_child = multiprocessing.Pipe(duplex=False)

        self.m_proc = multiprocessing.Process(
            target=mouse_worker,
            name="Mouse Worker",
            args=(self.m_pipe_child,),
            daemon=True,
        )

        self.k_proc.start()
        self.m_proc.start()

        print(
            f"\n[BRIDGE] - Interception Dual Engine Started."
            f"K-PID: {self.k_proc.pid} | "
            f"M-PID: {self.m_proc.pid}."
        )

    # -----------------------------------------
    # KEYBOARD API (Queue)
    # -----------------------------------------
    def key_down(self, code):
        try:
            self.k_queue.put_nowait((code, 0))
        except queue.Full:
            pass

    def key_up(self, code):
        try:
            self.k_queue.put((code, 1), timeout=0.2)
        except queue.Full:
            print(f"[WARNING] - Key UP event ({code}) dropped! Triggering rescue...")
            self.health_check()

    # -----------------------------------------
    # MOUSE API (Pipe)
    # -----------------------------------------
    def mouse_move_rel(self, dx, dy):
        self.m_pipe_parent.send(("move_rel", (dx, dy)))

    def mouse_move_abs(self, x, y):
        # Windows Interception uses a normalized 0-65535 coordinate system
        abs_x = int((x * 65535) / self.screen_w)
        abs_y = int((y * 65535) / self.screen_h)
        self.m_pipe_parent.send(("move_abs", (abs_x, abs_y)))

    def left_click_down(self):
        self.m_pipe_parent.send(("button", LEFT_BUTTON_DOWN))

    def left_click_up(self):
        self.m_pipe_parent.send(("button", LEFT_BUTTON_UP))

    def right_click_down(self):
        self.m_pipe_parent.send(("button", RIGHT_BUTTON_DOWN))

    def right_click_up(self):
        self.m_pipe_parent.send(("button", RIGHT_BUTTON_UP))

    def middle_click_down(self):
        self.m_pipe_parent.send(("button", MIDDLE_BUTTON_DOWN))

    # -----------------------------------------
    # SYSTEM API
    # -----------------------------------------
    def health_check(self):
        with self.bridge_lock:
            # Check Keyboard Worker (Queue)
            if not self.k_proc.is_alive():
                print(
                    f"\n[UTILITY] - Keyboard Worker Died: {_datetime.now().strftime('%H:%M:%S')}!"
                )

                # SCORCHED EARTH: Close the old queue, make a new one.
                self.k_queue.close()
                self.k_queue = multiprocessing.Queue()

                # Start new worker with the FRESH queue
                self.k_proc = multiprocessing.Process(
                    target=keyboard_worker,
                    name="Keyboard Worker",
                    args=(self.k_queue,),
                    daemon=True,
                )
                self.k_proc.start()
                self.system_config.set_high_priority(
                    self.k_proc.pid, "Revived Keyboard"
                )

            # Check Mouse Worker (Pipe)
            if not self.m_proc.is_alive():
                print(
                    f"\n[UTILITY] - Mouse Worker Died: {_datetime.now().strftime('%H:%M:%S')}!"
                )

                # SCORCHED EARTH: Close old pipes, make new ones.
                self.m_pipe_parent.close()
                self.m_pipe_child.close()
                self.m_pipe_parent, self.m_pipe_child = multiprocessing.Pipe(
                    duplex=False
                )

                # Start new worker with the FRESH pipe child
                self.m_proc = multiprocessing.Process(
                    target=mouse_worker,
                    name="Mouse Worker",
                    args=(self.m_pipe_child,),
                    daemon=True,
                )
                self.m_proc.start()
                self.system_config.set_high_priority(self.m_proc.pid, "Revived Mouse")

    def release_all(self):
        print("\n[BRIDGE] - Emergency Release...")
        with self.bridge_lock:
            self.health_check()
            for btn_up in [LEFT_BUTTON_UP, RIGHT_BUTTON_UP, MIDDLE_BUTTON_UP]:
                self.m_pipe_parent.send(("button", btn_up))

            internal_mouse_codes = {M_LEFT, M_RIGHT, M_MIDDLE}
            unique_codes = set(SCANCODES.values()) - internal_mouse_codes
            for code in unique_codes:
                try:
                    self.k_queue.put_nowait((code, 1))
                except queue.Full:
                    pass
        print("[BRIDGE] - Release signals dispatched.")
