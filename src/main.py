from __future__ import annotations

import keyboard
import os
import win32gui
import threading
import time
import ctypes
from mapper_module.utils import (
    DEFAULT_ADB_RATE_CAP, SHORT_DELAY,
    PPS, EMULATORS, ADB_EXE,
    DEF_EMULATOR_ID, TouchEvent,
    set_high_priority, stop_process,
    maintain_bridge_health
)

from mapper_module import (
    MapperEventDispatcher,
    AppConfig,
    JSONLoader,
    TouchReader,
    InterceptionBridge,
    Mapper,
    MouseMapper,
    KeyMapper,
    WASDMapper,
)


def check_single_instance(instance_name="Touch2Key_Engine"):
    """Create a unique named mutex to prevent duplicate instances."""
    mutex_name = f"Global\\{instance_name}"
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183:
        return False, None
    return True, handle


def construct_titles_dict(emulators: dict) -> dict:
    titles_dict = {}
    n = 0
    for emulator, value in emulators.items():
        titles_dict[value['window_title']] = {"name": emulator, "id": n}
        n += 1
    return titles_dict


def enum_callback(hwnd, results: dict):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if title:
            results[hwnd] = title


def select_emulator() -> dict | None:
    print("\n[MAIN] - Touch2Key Emulator Selector")
    emulators_list = list(EMULATORS.keys())
    emulators_len = len(emulators_list)

    if emulators_len == 0:
        return None

    print("\n[MAIN] - Supported Emulators:")
    for id, name in enumerate(emulators_list):
        print(f"    ID: [{id}] Name: {name}")

    current_windows = {}
    win32gui.EnumWindows(enum_callback, current_windows)
    titles_dict = construct_titles_dict(EMULATORS)
    titles = list(titles_dict.keys())

    emulator_id = DEF_EMULATOR_ID

    if current_windows:
        i = 0
        for hwnd in current_windows:
            window_title = current_windows[hwnd]
            if window_title in titles:
                if i == 0:
                    print(f"\nEmulators detected:")
                    emulator_id = None

                if emulator_id is None:
                    emulator_id = titles_dict[window_title]["id"]

                emulator = titles_dict[window_title]["name"]

                if emulator_id == titles_dict[window_title]["id"]:
                    print(f"    {emulator} - Selected automatically as default")
                else:
                    print(f"    {emulator}")

                i += 1

    try:
        choice = input(f"\nSelect Emulator ID [Default - {emulators_list[emulator_id]}]: ").strip()
        tmp = emulator_id
        emulator_id = int(choice)
        if not (0 <= emulator_id < emulators_len):
            print(f"ID {emulator_id} out of range. Using default...")
            emulator_id = tmp
    except ValueError:
        print("Invalid input. Using default...")

    emulator_name = emulators_list[emulator_id]
    print(f"\n[MAIN] - '{emulator_name}' selected.")
    return EMULATORS[emulator_name]


class Engine:
    def __init__(self):
        self.foreground_window: int = win32gui.GetForegroundWindow()
        self.interception_bridge: InterceptionBridge | None = None
        self.touch_reader: TouchReader | None = None
        self.mapper_logic: Mapper | None = None
        self.mouse_mapper: MouseMapper | None = None
        self.key_mapper: KeyMapper | None = None
        self.wasd_mapper: WASDMapper | None = None
        self.is_visible: bool = True
        self.lock: threading.Lock = threading.Lock()
        self.is_shutting_down: bool = False

    def set_is_visible(self, _is_visible: bool):
        with self.lock:
            self.is_visible = _is_visible
            assert self.interception_bridge is not None
            assert self.mouse_mapper is not None
            assert self.key_mapper is not None
            assert self.wasd_mapper is not None
            with self.interception_bridge.bridge_lock:
                maintain_bridge_health(self.interception_bridge)
            self.mouse_mapper.touch_up()
            self.key_mapper.release_all()
            self.wasd_mapper.touch_up()

    def process_touch_event(self, action, touch_event: TouchEvent):
        assert self.mouse_mapper is not None
        assert self.key_mapper is not None
        assert self.wasd_mapper is not None
        assert self.mapper_logic is not None

        local_visible = self.is_visible
        self.mapper_logic.event_count += 1

        if touch_event.is_mouse:
            self.mouse_mapper.process_touch(action, touch_event, local_visible)
            return  # CRITICAL: Prevents finger from hitting buttons/WASD

        self.key_mapper.process_touch(action, touch_event, local_visible)

        if touch_event.is_wasd:
            self.wasd_mapper.process_touch(action, touch_event, self.is_visible)

    def start(self):
        keyboard.add_hotkey('esc', self.shutdown)

        # Elevate Main Process (ADB Parsing & Logic)
        set_high_priority(os.getpid(), "Main Loop")

        print("\n[MAIN] - Initializing Dual-Engine Mapper... Press 'ESC' to Stop.")
        print(f"\n[MAIN] - ADB Executable File Path: {ADB_EXE}.")

        emulator = select_emulator()
        if emulator is None:
            print("\n[MAIN] - No emulators supported. Exiting...")
            return

        try:
            rate_input = input(f"\nEnter ADB rate cap [Default {DEFAULT_ADB_RATE_CAP}, Min 60, Blank for Default]: ").strip()
            rate_cap = max(60.0, float(rate_input)) if rate_input else DEFAULT_ADB_RATE_CAP

            pps_input = input(f"Enter target Alert Threshold for health alerts [Default {PPS}, Range 30-120]: ").strip()
            pps = max(30.0, min(120.0, float(pps_input))) if pps_input else PPS

        except ValueError:
            print("Invalid input. Using defaults...")
            rate_cap, pps = DEFAULT_ADB_RATE_CAP, PPS

        print(f"\n[MAIN] - ADB Cap: {rate_cap}Hz | Alert Threshold: {pps}PPS.")

        mapper_event_dispatcher = MapperEventDispatcher()
        config = AppConfig(mapper_event_dispatcher)

        # Initialize Bridge (spawns TWO processes: k_proc and m_proc)
        self.interception_bridge = InterceptionBridge()

        if hasattr(self.interception_bridge, 'm_proc'):
            set_high_priority(self.interception_bridge.m_proc.pid, "Mouse")

        if hasattr(self.interception_bridge, 'k_proc'):
            set_high_priority(self.interception_bridge.k_proc.pid, "Keyboard")

        time.sleep(SHORT_DELAY)

        json_loader = JSONLoader(config, self.foreground_window)
        self.touch_reader = TouchReader(config, mapper_event_dispatcher, self.interception_bridge, rate_cap)
        self.mapper_logic = Mapper(json_loader, self.touch_reader, self.interception_bridge, pps, emulator)

        self.mouse_mapper = MouseMapper(self.mapper_logic)
        self.key_mapper = KeyMapper(self.mapper_logic)
        self.wasd_mapper = WASDMapper(self.mapper_logic)

        self.touch_reader.bind_touch_event(self.process_touch_event)
        mapper_event_dispatcher.register_callback("ON_MENU_MODE_TOGGLE", self.set_is_visible)

        # Block until ESC is pressed
        keyboard.wait()

    def shutdown(self):
        if not win32gui.GetForegroundWindow() == self.foreground_window:
            return

        if self.is_shutting_down:
            return
        self.is_shutting_down = True

        print("\n[MAIN] - 'ESC' detected. Cleaning up...")

        try:
            print("[MAIN] - Exiting all spawned threads...")
            if self.touch_reader is not None:
                self.touch_reader.stop()
            if self.mapper_logic is not None:
                self.mapper_logic.running = False
            if self.interception_bridge is not None:
                self.interception_bridge.release_all()
                print("[MAIN] - Stopping Mouse and Keyboard child processes...")
                stop_process(self.interception_bridge.k_proc)
                stop_process(self.interception_bridge.m_proc)
        except Exception:
            pass

        print("[MAIN] - Shutdown complete. Goodbye.")
        os._exit(0)


if __name__ == "__main__":
    success, mutex_handle = check_single_instance()
    if not success:
        print("[MAIN] - Another instance of Touch2Key is already running. Exiting this instance.")
        os._exit(0)

    engine = Engine()
    try:
        engine.start()
    except KeyboardInterrupt:
        engine.shutdown()
