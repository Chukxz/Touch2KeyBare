from __future__ import annotations
from typing import TYPE_CHECKING

import time
import threading

from mapper_module.platform import get_platform

from .utils import (
    DEF_DPI, LONG_DELAY, WINDOW_UPDATE_INTERVAL, SCANCODES,
    MapperEvent, rotate_resolution
    )

if TYPE_CHECKING:
    from .json_loader import JSONLoader
    from .touch_reader import TouchReader
    # Just use the windows equivalent as all supported platforms use the same methods albeit different implementations
    from mapper_module.platform.windows import InterceptionBridge


class Mapper():
    # EnumWindows callback type definition

    def __init__(self, json_loader:JSONLoader, touch_reader:TouchReader, interception_bridge:InterceptionBridge, pps:float, emulator:dict[str, str]):
        _, WindowMgrClass, _, _ = get_platform()

        # Setup Dependencies
        self.json_loader = json_loader
        self.config = self.json_loader.config
        self.mapper_event_dispatcher = self.json_loader.mapper_event_dispatcher
        self.touch_reader = touch_reader
        self.interception_bridge = interception_bridge
        self.emulator = emulator
        self.window_title = emulator['window_title']
        self.toggle_key_scancode = SCANCODES[emulator["toggle_key"]]
        self.pps = pps
        self.event_count = 0
        self.last_pulse_time = time.perf_counter()
        
        # Window Tracking Setup
        self.window_manager = WindowMgrClass()
        self.screen_w, self.screen_h = self.window_manager.get_screen_metrics()
        self.lock = threading.Lock()
        self.last_cursor_state = True # Cursor showing (Default)
        self.game_window_class_name = None
        self.game_window_info = None
        self.window_update_interval = WINDOW_UPDATE_INTERVAL
        
        # Config & State
        self.wasd_block = 0
        self.update_config() 
        
        self.mapper_event_dispatcher.register_callback("ON_CONFIG_RELOAD", self.update_config)
        
        # Start the window tracking thread
        self.running = True
        self.window_lost = False
        self.window_thread = threading.Thread(target=self.update_game_window_info, daemon=True)
        self.window_thread.start()
    
    def update_config(self):
        with self.lock:
            self.device_width = self.json_loader.width
            self.device_height = self.json_loader.height
            self.dpi = self.json_loader.dpi
            print(f"\n[MAPPER] - Mapping from Device synced to Resolution: {self.device_width}x{self.device_height}, DPI: {self.dpi}.")
            print(f"\n[MAPPER] - Current Screen Resolution: {self.screen_w}x{self.screen_h}")
            
    # Window Management
    def get_game_window_class_name(self, window_title):
        """Gets the game window classname."""
        if window_title is None:
            raise ValueError("Window_title must be provided.")
    
        class_name = None            
        hwnd = self.window_manager.find_window_by_title(window_title)
        if hwnd != 0:
            class_name = self.window_manager.get_window_class_name(hwnd)
            print(f"\n[MAPPER] - Found window '{window_title}' (Class: {class_name}).")
        else:
            _str = f"\n[MAPPER] - Window class name could not be gotten for window: '{window_title}'."
            raise RuntimeError(_str)            
        return class_name

    def get_window_info(self, hwnd):
        # Get the Client Area (The pure game content size)
        width, height = self.window_manager.get_client_rect(hwnd)
        
        # Find where top-left (0,0) of the Client Area is on the Screen
        x, y = self.window_manager.get_window_position(hwnd)

        self.pulse_status()
        
        # Check Cursor Visibility
        is_visible = self.window_manager.is_cursor_visible()
        
        if not is_visible == self.last_cursor_state:
            self.last_cursor_state = is_visible
            # Signal the rest of the app to switch modes
            self.mapper_event_dispatcher.dispatch(MapperEvent(action="ON_MENU_MODE_TOGGLE", is_visible=is_visible))
            
        return {
            'hwnd': hwnd,
            'left': x,
            'top': y,    
            'width': width,  
            'height': height 
        }

    def update_game_window_info(self):
        """Background thread - optimized to minimize lock hold time."""        
        while self.running:
            try:                
                # Check if current handle is still valid
                current_hwnd = None
                with self.lock:
                    if self.game_window_info:
                        current_hwnd = self.game_window_info.get('hwnd')
                        
                if current_hwnd and self.window_manager.is_window_valid(current_hwnd):
                    # WINDOW IS ACTIVE: Get fresh coordinates
                    new_info = self.get_window_info(current_hwnd)
                                        
                    if self.window_lost:
                        print(f"\n[MAPPER] - Acquired game window!")
                                            
                    # ATOMIC SWAP: Only hold lock to update the dict reference
                    with self.lock:
                        self.game_window_info = new_info
                        self.window_lost = False
                        
                else:
                    # WINDOW IS LOST: Handle scanning                        
                    if not self.window_lost:
                        print("\n[MAPPER] - Game window lost! Scanning for new window...")
                        with self.lock:
                            self.window_lost = True
                            self.game_window_info = None
                                                
                    try:
                        # Get window title class name if it doesn't exist
                        
                        if not self.game_window_class_name:
                            self.game_window_class_name = self.get_game_window_class_name(self.window_title)

                        # Scan for the window
                        discovered_info = self.get_game_window_info()
                        
                        # If we found it, swap it in
                        with self.lock:
                            self.game_window_info = discovered_info
                            self.window_lost = False
                        print("\n[MAPPER] - New window handle bound.")
                            
                    except RuntimeError:
                        with self.lock:
                            self.game_window_info = None
                            # Game isn't open yet, just keep waiting
                        pass
                    
            except Exception as e:
                print(f"\n[MAPPER] - Window tracking error: {e}.")
            
            # Dynamic Sleep: Constant from utils
            sleep_time = LONG_DELAY if self.window_lost else self.window_update_interval
            time.sleep(sleep_time)

    def get_game_window_info(self):
        hwnds = self.window_manager.find_hwnds_by_class(self.game_window_class_name)
        target_info = None
        max_diag = 0

        for hwnd in hwnds:
            if not self.window_manager.is_window_visible(hwnd):
                continue

            info = self.get_window_info(hwnd)
            w, h = info['width'], info['height']
            diag = (w*w + h*h) ** 0.5

            if diag > max_diag:
                max_diag = diag
                target_info = info
        
        if target_info is None:
            _str = f"\n[MAPPER] - No visible window found for class: '{self.game_window_class_name}'."
            raise RuntimeError(_str)
        
        return target_info
    
    def device_to_game_abs(self, x, y):
        """Thread-safe absolute mapping."""
        with self.lock:
            rot = self.touch_reader.rotation
        
        rot_dev_w, rot_dev_h = rotate_resolution(self.device_width, self.device_height, rot)
        return (x / rot_dev_w) * self.screen_w, (y / rot_dev_h) * self.screen_h

    
    def dp_to_px(self, dp):
        return dp * (self.dpi / DEF_DPI)

    def px_to_dp(self, px):
        return px * (DEF_DPI / self.dpi)

    def pulse_status(self):
        now = time.perf_counter()
        elapsed = now - self.last_pulse_time
    
        if elapsed >= 5.0:
            current_count = self.event_count
            self.event_count = 0
            self.last_pulse_time = now
            pps = current_count / elapsed
        
            # Check if we are lagging
            status = "HEALTHY" if pps >= self.pps else "LOW RATE"
            if pps == 0: status = "IDLE/DISCONNECTED"
            block_indicator = f"[BLOCK ON ({self.wasd_block})]" if self.wasd_block > 0 else "[OPEN]"

            print(f"\n[MAPPER] - Rate: {pps:>5.1f} Hz | Status: {status:<15} | WASD: {block_indicator:<12}")
