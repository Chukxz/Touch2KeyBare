from __future__ import annotations
from typing import TYPE_CHECKING

import threading
from pathlib import Path
import tomlkit
from tomlkit.exceptions import ParseError
import keyboard
from .utils import  MapperEvent, TOML_PATH, create_default_toml

if TYPE_CHECKING:
    from .utils import MapperEventDispatcher

class AppConfig:
    def __init__(self, mapper_event_dispatcher:MapperEventDispatcher):
        self.mapper_event_dispatcher = mapper_event_dispatcher
        
        # Initialize the lock to protect config_data
        self.config_lock = threading.Lock()
        
        self.config_data = {}
        
        # Load immediately
        self.load_config()
        print(f"\n[CONFIG] - Configuration loaded from {TOML_PATH}.")
        print(f"\n[CONFIG] - Current Handedness: {self.display_handedness(self.get('system').get('left_handed', False))}")

        # REGISTER HOTKEY
        print("\n[CONFIG] - Press F7 to switch handedness or F9 to only reload config.")
        keyboard.add_hotkey('f7', self.switch_handedness)
        keyboard.add_hotkey('f9', self.reload_config)
        
    def load_config(self):
        """Loads TOML data safely. Creates default if missing."""
        try:
            # Check if file exists, if not create it using your helper
            toml_path = Path(TOML_PATH)
            if not Path.exists(toml_path):
                print(f"\n[CONFIG] - Config file {TOML_PATH} not found! Creating default...")
                create_default_toml()

            # Read the file from disk
            with toml_path.open("rb") as f:
                new_data = tomlkit.load(f)

            with self.config_lock:
                self.config_data = new_data
                            
        except ParseError as e:
            print(f"\n[CONFIG] - Failed to parse TOML. Keeping previous config. Error: {e}")
        except Exception as e:
            print(f"[CONFIG] - Error loading config: {e}")


    def reload_config(self):
        """Reloads from disk and notifies listeners."""
        print(f"\n[CONFIG] - Reloading TOML configuration from {TOML_PATH}...")
        self.load_config()
        
        # Dispatch event so other modules know config changed
        self.mapper_event_dispatcher.dispatch(MapperEvent(action="ON_CONFIG_RELOAD"))
        
    def display_handedness(self, handedness):
        return "Left-Handed" if handedness else "Right-Handed"
        
    def switch_handedness(self):
        """Toggles left-handed mode in config and saves."""
        with self.config_lock:
            system_config = self.get('system')
            current_value = system_config.get('left_handed', False)
            new_value = not current_value
            system_config['left_handed'] = new_value
            self.config_data['system'] = system_config
        
        # Save back to disk
        try:
            with open(TOML_PATH, "w", encoding="utf-8") as f:
                tomlkit.dump(self.config_data, f)
            print(f"\n[CONFIG] - Handedness switched to {self.display_handedness(new_value)}. Config saved.")
        except Exception as e:
            print(f"\n[CONFIG] - Failed to save config: {e}")
        
        # Notify listeners of config change
        self.mapper_event_dispatcher.dispatch(MapperEvent(action="ON_CONFIG_RELOAD"))

    def get(self, key, default=None):
        return self.config_data.get(key, default if default is not None else {})
