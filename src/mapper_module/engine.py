from __future__ import annotations
from typing import TYPE_CHECKING

import multiprocessing
import keyboard
import os
import threading
import time
import sys
import argparse
from PySide6.QtWidgets import QApplication
from mapper_module.platforms import check_single_instance, get_platform

from mapper_module.utils import (
    PRESETS,
    ADB,
    SHORT_DELAY,
    TouchEvent,
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
from mapper_module.core.list_windows import select_window
from mapper_module.core.key_capture import capture_keys, capture_performance_settings

from mapper_module.utils import PROJECT_ROOT

NAME = "Touch2Key_Engine"

if TYPE_CHECKING:
    from cProfile import Profile

profiler: Profile | None = None


class Engine:
    def __init__(self):
        _Platform = get_platform()

        print("\n[MAIN] - Initializing Touch2Key... Press 'ESC' to Stop.")
        print(f"\n[MAIN] - ADB Executable File Path: {ADB}.")
        keyboard.add_hotkey("esc", self._shutdown)

        self.system_config = _Platform.SystemConfig()
        self.system_config.set_high_priority(os.getpid(), "Main Loop")
        self.system_config.set_dpi_awareness()
        self.system_config.set_timer_resolution()

        self.window_manager = _Platform.WindowManager()
        self.foreground_window = self.window_manager.get_foreground_window()

        self.bridge_class = _Platform.Bridge(self.window_manager, self.system_config)

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
            self.mouse_mapper.touch_up(None, self.is_visible, False)
            self.key_mapper.release_all()
            self.wasd_mapper.touch_up()

    def _process_touch_event(self, action, touch_event: TouchEvent):
        assert self.mouse_mapper is not None
        assert self.key_mapper is not None
        assert self.wasd_mapper is not None
        assert self.mapper is not None

        local_visible = self.is_visible
        self.mapper.event_count += 1

        activate_mouse_sequence = self.key_mapper.process_touch(
            action, touch_event, local_visible
        )

        if touch_event.is_mouse:
            self.mouse_mapper.process_touch(
                action, touch_event, local_visible, activate_mouse_sequence
            )

        if touch_event.is_wasd:
            self.wasd_mapper.process_touch(action, touch_event, self.is_visible)

    def _start(self):
        w_result = select_window()
        if w_result is None:
            print("\n[MAIN] - No window selected.")
            input("Press Enter to exit...")
            return
        selected_window_id, window_title = w_result

        preset_name = next(
            (
                name
                for name, data in PRESETS.items()
                if data.get("window_title") == window_title
            ),
            None,
        )

        c_result = capture_keys(preset_name)
        if c_result is None:
            print("\n[MAIN] - Key configuration cancelled.")
            input("Press Enter to exit...")
            return
        toggle_key, sprint_key = c_result

        if not toggle_key:
            print(
                "\n[MAIN] - No toggle key set. Touch zones if disabled by the cursor state can only be re-enabled via the keyboard/mouse."
            )

        emulator = {
            "toggle_key": toggle_key,
            "sprint_key": sprint_key,
        }

        perf_result = capture_performance_settings()
        if perf_result is None:
            print("\n[MAIN] - Performance configuration cancelled.")
            input("Press Enter to exit...")
            return
        rate_cap, pps = perf_result

        if rate_cap is None or pps is None:
            print("\n[MAIN] - Invalid performance settings.")
            input("Press Enter to exit...")
            return

        print(f"\n[MAIN] - ADB Cap: {rate_cap}Hz | Alert Threshold: {pps}PPS.")

        mapper_event_dispatcher = MapperEventDispatcher()
        config = AppConfig(mapper_event_dispatcher)

        time.sleep(SHORT_DELAY)

        json_loader = JSONLoader(config, self.foreground_window)
        self.touch_reader = TouchReader(config, mapper_event_dispatcher, rate_cap)
        self.mapper = Mapper(
            json_loader,
            self.touch_reader,
            self.bridge_class,
            pps,
            emulator,
            selected_window_id,
        )

        self.mouse_mapper = MouseMapper(self.mapper)
        self.key_mapper = KeyMapper(self.mapper)
        self.wasd_mapper = WASDMapper(self.mapper)

        self.touch_reader.bind_touch_event(self._process_touch_event)
        mapper_event_dispatcher.register_callback(
            "ON_MENU_MODE_TOGGLE", self._set_is_visible
        )
        self.bridge_class.start_worker_processes()

        keyboard.wait()

    def _shutdown(self):
        if self.window_manager.get_foreground_window() != self.foreground_window:
            return
        if self.is_shutting_down:
            return
        self.is_shutting_down = True

        print("\n[MAIN] - 'ESC' detected. Cleaning up...")
        try:
            if self.touch_reader is not None:
                self.touch_reader.stop()
            if self.mapper is not None:
                self.mapper.running = False
            if self.bridge_class is not None:
                self.bridge_class.shutdown()  # stop the heartbeat thread first
                self.bridge_class.release_all()

                procs = [
                    p
                    for p in (
                        getattr(self.bridge_class, "k_proc", None),
                        getattr(self.bridge_class, "m_proc", None),
                    )
                    if p is not None
                ]

                # Signal both to terminate before waiting on either.
                for p in procs:
                    if p.is_alive():
                        p.terminate()

                for p in procs:
                    p.join(timeout=1.0)
                    if p.is_alive():
                        p.kill()
                        p.join(timeout=1.0)

        except Exception:
            pass

        profiler_cleanup(profiler)
        print("\n[MAIN] - Shutdown complete. Goodbye.")
        input("Press Enter to exit...")
        os._exit(0)


def profiler_cleanup(profiler: Profile | None):
    if profiler:
        profiler.disable()
        profiler.dump_stats(PROJECT_ROOT / "touch2key.prof")
        print("\n[MAIN] - Profiling data saved to 'touch2key.prof'.")


def run():
    global profiler
    parser = argparse.ArgumentParser(description="Touch2Key Main")
    parser.add_argument(
        "--profile", action="store_true", help="Generate profiling data."
    )
    args = parser.parse_args()

    if args.profile:
        import cProfile

        profiler = cProfile.Profile()
        profiler.enable()

    if not pre_flight_run():
        profiler_cleanup(profiler)
        input("Press Enter to exit...")
        sys.exit(1)

    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    try:
        success, _instance_handle = check_single_instance(NAME)
    except RuntimeError as e:
        print(f"[MAIN] - {e}")
        profiler_cleanup(profiler)
        input("Press Enter to exit...")
        os._exit(0)

    if not success:
        print(
            "[MAIN] - Another instance of Touch2Key is already running. Exiting this instance."
        )
        profiler_cleanup(profiler)
        input("Press Enter to exit...")
        os._exit(0)

    _app = QApplication(sys.argv)
    _app.setQuitOnLastWindowClosed(True)
    _engine = Engine()
    try:
        _engine._start()
    except KeyboardInterrupt:
        _app.closeAllWindows()
        _engine._shutdown()


if __name__ == "__main__":
    run()
