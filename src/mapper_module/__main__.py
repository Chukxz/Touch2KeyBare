from __future__ import annotations

import multiprocessing
import keyboard
import os
import threading
import time
import sys

from mapper_module.platform import check_single_instance, get_platform
from mapper_module.utils import (
    DEFAULT_ADB_RATE_CAP,
    SHORT_DELAY,
    PPS,
    EMULATORS,
    ADB_EXE,
    DEF_EMULATOR_ID,
    SYSTEM,
    TouchEvent,
    stop_process,
)

from mapper_module import (
    MapperEventDispatcher,
    AppConfig,
    JSONLoader,
    TouchReader,
    Mapper,
    MouseMapper,
    KeyMapper,
    WASDMapper,
)

from mapper_module.scripts.pre_flight import run as pre_flight_run

NAME = "Touch2Key__Engine"


def get_display_protocol():
    """
    Returns the display protocol or None if the session is not 
    X11, Wayland, or XWayland.
    """
    # Normalize to lowercase and handle missing environment variables
    session = os.environ.get('XDG_SESSION_TYPE', '').lower()
    
    # 1. Handle Wayland and XWayland
    if session == 'wayland':
        # If we are in Wayland but DISPLAY is set, it is XWayland
        if 'DISPLAY' in os.environ:
            return 'xwayland'
        return 'wayland'
    
    # 2. Handle X11
    # Check session type, but also allow DISPLAY variable 
    # as a secondary check for legacy X11 sessions
    if session == 'x11' or 'DISPLAY' in os.environ:
        return 'x11'
    
    # 3. Default for TTY, SSH, or other headless environments
    return None


def _construct_titles_dict(emulators: dict) -> dict:
    titles_dict = {}
    n = 0
    for emulator, value in emulators.items():
        titles_dict[value["window_title"]] = {"name": emulator, "id": n}
        n += 1
    return titles_dict


def _select_emulator(window_manager) -> dict | None:
    print("\n[MAIN] - Touch2Key Emulator Selector")
    emulators_list = list(EMULATORS.keys())
    emulators_len = len(emulators_list)

    if emulators_len == 0:
        return None

    print("\n[MAIN] - Supported Emulators:")
    for id, name in enumerate(emulators_list):
        print(f"    ID: [{id}] Name: {name}")

    current_windows_titles = window_manager.find_window_titles()
    titles_dict = _construct_titles_dict(EMULATORS)
    titles = list(titles_dict.keys())

    emulator_id = DEF_EMULATOR_ID

    if current_windows_titles:
        i = 0
        for _, window_title in current_windows_titles.items():
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
        choice = input(
            f"\nSelect Emulator ID [Default - {emulators_list[emulator_id]}]: "
        ).strip()
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


class _Engine:
    def __init__(self):
        BridgeClass, WindowMgrClass, SysConfigClass, _ = get_platform()

        self.window_manager = WindowMgrClass()
        self.system_config = SysConfigClass()
        self.bridge_class = BridgeClass(self.window_manager, self.system_config)

        self.system_config.set_dpi_awareness()
        self.system_config.set_timer_resolution()
        self.foreground_window = self.window_manager.get_foreground_window()

        self.touch_reader: TouchReader | None = None
        self.mapper: Mapper | None = None
        self.mouse_mapper: MouseMapper | None = None
        self.key_mapper: KeyMapper | None = None
        self.wasd_mapper: WASDMapper | None = None
        self.is_visible: bool = True
        self.lock: threading.Lock = threading.Lock()
        self.is_shutting_down: bool = False

    def _set_is_visible(self, _is_visible: bool):
        with self.lock:
            self.is_visible = _is_visible
            assert self.mouse_mapper is not None
            assert self.key_mapper is not None
            assert self.wasd_mapper is not None

            self.bridge_class.health_check()
            self.mouse_mapper.touch_up(None, self.is_visible)
            self.key_mapper.release_all()
            self.wasd_mapper.touch_up()

    def _check_workers(self):
        self.bridge_class.health_check()
        time.sleep(SHORT_DELAY)

    def _process_touch_event(self, action, touch_event: TouchEvent):
        assert self.mouse_mapper is not None
        assert self.key_mapper is not None
        assert self.wasd_mapper is not None
        assert self.mapper is not None

        local_visible = self.is_visible
        self.mapper.event_count += 1

        if touch_event.is_mouse:
            self.mouse_mapper.process_touch(action, touch_event, local_visible)
            return  # CRITICAL: Prevents finger from hitting buttons/WASD

        self.key_mapper.process_touch(action, touch_event, local_visible)

        if touch_event.is_wasd:
            self.wasd_mapper.process_touch(action, touch_event, self.is_visible)

    def _start(self):
        keyboard.add_hotkey("esc", self._shutdown)

        # Elevate Main Process (ADB Parsing & Logic) using abstracted config
        self.system_config.set_high_priority(os.getpid(), "Main Loop")

        print("\n[MAIN] - Initializing Dual-_Engine Mapper... Press 'ESC' to Stop.")
        print(f"\n[MAIN] - ADB Executable File Path: {ADB_EXE}.")

        emulator = _select_emulator(self.window_manager)
        if emulator is None:
            print("\n[MAIN] - No emulators supported. Exiting...")
            return

        try:
            rate_input = input(
                f"\nEnter ADB rate cap [Default {DEFAULT_ADB_RATE_CAP}, Min 60, Blank for Default]: "
            ).strip()
            rate_cap = (
                max(60.0, float(rate_input)) if rate_input else DEFAULT_ADB_RATE_CAP
            )

            pps_input = input(
                f"Enter target Alert Threshold for health alerts [Default {PPS}, Range 30-120]: "
            ).strip()
            pps = max(30.0, min(120.0, float(pps_input))) if pps_input else PPS

        except ValueError:
            print("Invalid input. Using defaults...")
            rate_cap, pps = DEFAULT_ADB_RATE_CAP, PPS

        print(f"\n[MAIN] - ADB Cap: {rate_cap}Hz | Alert Threshold: {pps}PPS.")

        mapper_event_dispatcher = MapperEventDispatcher()
        config = AppConfig(mapper_event_dispatcher)

        if hasattr(self.bridge_class, "m_proc"):
            self.system_config.set_high_priority(self.bridge_class.m_proc.pid, "Mouse")

        if hasattr(self.bridge_class, "k_proc"):
            self.system_config.set_high_priority(
                self.bridge_class.k_proc.pid, "Keyboard"
            )

        time.sleep(SHORT_DELAY)

        json_loader = JSONLoader(config, self.foreground_window)
        self.touch_reader = TouchReader(config, mapper_event_dispatcher, rate_cap)
        self.mapper = Mapper(
            json_loader, self.touch_reader, self.bridge_class, pps, emulator
        )

        self.mouse_mapper = MouseMapper(self.mapper)
        self.key_mapper = KeyMapper(self.mapper)
        self.wasd_mapper = WASDMapper(self.mapper)

        self.touch_reader.bind_touch_event(self._process_touch_event)
        mapper_event_dispatcher.register_callback(
            "ON_MENU_MODE_TOGGLE", self._set_is_visible
        )

        # Restart failed child processes
        threading.Thread(target=self._check_workers, daemon=True).start()

        # Block until ESC is pressed
        keyboard.wait()

    def _shutdown(self):
        # Use abstracted window manager to check active window
        if self.window_manager.get_foreground_window() != self.foreground_window:
            return

        if self.is_shutting_down:
            return
        self.is_shutting_down = True

        print("\n[MAIN] - 'ESC' detected. Cleaning up...")

        try:
            print("[MAIN] - Exiting all spawned threads...")
            if self.touch_reader is not None:
                self.touch_reader.stop()
            if self.mapper is not None:
                self.mapper.running = False
            if self.bridge_class is not None:
                self.bridge_class.release_all()

                # Cleanup child processes safely if they exist in the OS-specific implementation
                print("[MAIN] - Stopping Mouse and Keyboard child processes...")
                if hasattr(self.bridge_class, "k_proc"):
                    stop_process(self.bridge_class.k_proc)
                if hasattr(self.bridge_class, "m_proc"):
                    stop_process(self.bridge_class.m_proc)
        except Exception:
            pass

        print("[MAIN] - Shutdown complete. Goodbye.")
        os._exit(0)


def run():
    if not pre_flight_run():
        sys.exit(1)
    
    if SYSTEM == "Linux":
        protocol = get_display_protocol()
        if protocol and protocol == "x11":
            pass
        else:
            print("[MAIN] - Ensure you are on X11.")
            sys.exit(1)

    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    success, _ = check_single_instance(NAME)
    if not success:
        print(
            "[MAIN] - Another instance of Touch2Key is already running. Exiting this instance."
        )
        os._exit(0)

    _engine = _Engine()

    try:
        _engine._start()
    except KeyboardInterrupt:
        _engine._shutdown()


if __name__ == "__main__": 
    run()
