from ..base import AbstractBridge
import multiprocessing
import threading
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
    PACK_ABS,
    PACK_BUTTON,
    PACK_REL,
    PACK_KEY,
    TASK_ABS,
    TASK_BUTTON,
    TASK_REL,
)


class UInputBridge(AbstractBridge):
    def __init__(self, window_manager, system_config):
        self.window_manager = window_manager
        self.system_config = system_config
        self.screen_w, self.screen_h = window_manager.get_screen_dimensions()
        self.bridge_lock = threading.RLock()

        self._mouse_left_down = False
        self._mouse_right_down = False
        self._mouse_middle_down = False
        self._pressed_keys = set()

        # Keyboard uses lock-free Pipe
        self.k_pipe_read, self.k_pipe_write = multiprocessing.Pipe(duplex=False)
        self.k_proc = multiprocessing.Process(
            target=keyboard_worker,
            name="Keyboard Worker",
            args=(self.k_pipe_read,),
            daemon=True,
        )
        self.k_proc.start()
        self.system_config.set_high_priority(self.k_proc.pid, "Keyboard")

        # Mouse uses lock-free Pipe (High-Frequency Streaming)
        self.m_pipe_read, self.m_pipe_write = multiprocessing.Pipe(duplex=False)
        self.m_proc = multiprocessing.Process(
            target=mouse_worker,
            name="Mouse Worker",
            args=(self.m_pipe_read,),
            daemon=True,
        )
        self.m_proc.start()
        self.system_config.set_high_priority(self.m_proc.pid, "Mouse")

        print(
            f"\n[BRIDGE] - UInput Dual Engine Started. "
            f"K-PID: {self.k_proc.pid} | "
            f"M-PID: {self.m_proc.pid}."
        )

    # -----------------------------------------
    # KEYBOARD API (Pipe)
    # -----------------------------------------
    # Linux logic sends state=1 for down, state=0 for up.
    def key_down(self, code):
        # Pack into 3 raw bytes: [Code: 2 bytes] [State: 1 byte]
        self._pressed_keys.add(code)
        try:
            self.k_pipe_write.send_bytes(PACK_KEY.pack(int(code), 1))
        except OSError:
            self.selective_release()

    def key_up(self, code):
        # Pack into 3 raw bytes: [Code: 2 bytes] [State: 1 byte]
        try:
            self.k_pipe_write.send_bytes(PACK_KEY.pack(int(code), 0))
        except OSError:
            self.selective_release()
        else:
            self._pressed_keys.discard(code)

    # -----------------------------------------
    # MOUSE API (Pipe)
    # -----------------------------------------
    def mouse_move_rel(self, dx, dy):
        # Pack into 5 raw bytes: [Task: 1 byte] [dx: 2 bytes] [dy: 2 bytes]
        try:
            self.m_pipe_write.send_bytes(PACK_REL.pack(TASK_REL, int(dx), int(dy)))
        except OSError:
            self.selective_release()

    def mouse_move_abs(self, x, y):
        # UInput uses literal screen pixels but we normalize to match ABS_X/ABS_Y declared range in the worker
        abs_x = int((x * 65535) / self.screen_w)
        abs_y = int((y * 65535) / self.screen_h)
        # Pack into 9 raw bytes: [Task: 1 byte] [x: 4 bytes] [y: 4 bytes]
        try:
            self.m_pipe_write.send_bytes(
                PACK_ABS.pack(TASK_ABS, int(abs_x), int(abs_y))
            )
        except OSError:
            self.selective_release()

    def left_click_down(self):
        # Pack into 5 raw bytes: [Task: 1 byte] [data: 4 bytes]
        try:
            self.m_pipe_write.send_bytes(
                PACK_BUTTON.pack(TASK_BUTTON, LEFT_BUTTON_DOWN)
            )
        except OSError:
            self.selective_release()
        else:
            self._mouse_left_down = True

    def left_click_up(self):
        # Pack into 5 raw bytes: [Task: 1 byte] [data: 4 bytes]
        try:
            self.m_pipe_write.send_bytes(PACK_BUTTON.pack(TASK_BUTTON, LEFT_BUTTON_UP))
        except OSError:
            self.selective_release()
        else:
            self._mouse_left_down = False

    def right_click_down(self):
        # Pack into 5 raw bytes: [Task: 1 byte] [data: 4 bytes]
        try:
            self.m_pipe_write.send_bytes(
                PACK_BUTTON.pack(TASK_BUTTON, RIGHT_BUTTON_DOWN)
            )
        except OSError:
            self.selective_release()
        else:
            self._mouse_right_down = True

    def right_click_up(self):
        # Pack into 5 raw bytes: [Task: 1 byte] [data: 4 bytes]
        try:
            self.m_pipe_write.send_bytes(PACK_BUTTON.pack(TASK_BUTTON, RIGHT_BUTTON_UP))
        except OSError:
            self.selective_release()
        else:
            self._mouse_right_down = False

    def middle_click_down(self):
        # Pack into 5 raw bytes: [Task: 1 byte] [data: 4 bytes]
        try:
            self.m_pipe_write.send_bytes(
                PACK_BUTTON.pack(TASK_BUTTON, MIDDLE_BUTTON_DOWN)
            )
        except OSError:
            self.selective_release()
        else:
            self._mouse_middle_down = True

    def middle_click_up(self):
        # Pack into 5 raw bytes: [Task: 1 byte] [data: 4 bytes]
        try:
            self.m_pipe_write.send_bytes(
                PACK_BUTTON.pack(TASK_BUTTON, MIDDLE_BUTTON_UP)
            )
        except OSError:
            self.selective_release()
        else:
            self._mouse_middle_down = False

    # -----------------------------------------
    # SYSTEM API
    # -----------------------------------------
    def health_check(self):
        with self.bridge_lock:
            # Check Keyboard Worker (Pipe)
            if not self.k_proc.is_alive():
                print(
                    f"\n[UTILITY] - Keyboard Worker Died: {_datetime.now().strftime('%H:%M:%S')}!"
                )

                # Scorched Earth: Destroy old pipes
                self.k_pipe_read.close()
                self.k_pipe_write.close()
                self.k_pipe_read, self.k_pipe_write = multiprocessing.Pipe(duplex=False)

                self.k_proc = multiprocessing.Process(
                    target=keyboard_worker,
                    args=(self.k_pipe_read,),
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

                # Scorched Earth: Destroy old pipes
                self.m_pipe_read.close()
                self.m_pipe_write.close()
                self.m_pipe_read, self.m_pipe_write = multiprocessing.Pipe(duplex=False)

                self.m_proc = multiprocessing.Process(
                    target=mouse_worker,
                    name="Mouse Worker",
                    args=(self.m_pipe_read,),
                    daemon=True,
                )
                self.m_proc.start()
                self.system_config.set_high_priority(self.m_proc.pid, "Revived Mouse")

    def selective_release(self):
        with self.bridge_lock:
            self.health_check()

            if self._pressed_keys:
                for code in list(self._pressed_keys):
                    try:
                        self.k_pipe_write.send_bytes(
                            PACK_KEY.pack(int(code), 0)
                        )  # Linux: 0=up
                    except OSError:
                        pass
                self._pressed_keys.clear()

            if self._mouse_left_down:
                try:
                    self.m_pipe_write.send_bytes(
                        PACK_BUTTON.pack(TASK_BUTTON, LEFT_BUTTON_UP)
                    )
                except OSError:
                    pass
            if self._mouse_right_down:
                try:
                    self.m_pipe_write.send_bytes(
                        PACK_BUTTON.pack(TASK_BUTTON, RIGHT_BUTTON_UP)
                    )
                except OSError:
                    pass
            if self._mouse_middle_down:
                try:
                    self.m_pipe_write.send_bytes(
                        PACK_BUTTON.pack(TASK_BUTTON, MIDDLE_BUTTON_UP)
                    )
                except OSError:
                    pass

            self._mouse_left_down = self._mouse_right_down = self._mouse_middle_down = (
                False
            )

    def release_all(self):
        print("\n[BRIDGE] - Emergency Release (UInput)...")
        with self.bridge_lock:
            self.health_check()

            # Release Keyboard via Pipe
            internal_mouse_codes = {M_LEFT, M_RIGHT, M_MIDDLE}
            unique_codes = set(SCANCODES.values()) - internal_mouse_codes
            for code in unique_codes:
                try:
                    self.k_pipe_write.send_bytes(
                        PACK_KEY.pack(int(code), 0)
                    )  # Linux: 0=up
                except OSError:
                    pass
            self._pressed_keys.clear()

            # Release Mouse via Pipe
            for btn_up in [LEFT_BUTTON_UP, RIGHT_BUTTON_UP, MIDDLE_BUTTON_UP]:
                try:
                    self.m_pipe_write.send_bytes(PACK_BUTTON.pack(TASK_BUTTON, btn_up))
                except OSError:
                    pass
            self._mouse_left_down = self._mouse_right_down = self._mouse_middle_down = (
                False
            )

        print("[BRIDGE] - Release signals dispatched.")
