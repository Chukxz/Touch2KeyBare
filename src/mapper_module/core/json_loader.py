from __future__ import annotations
from typing import TYPE_CHECKING

import json
import os
import time
import keyboard

from mapper_module.platform import get_platform
from mapper_module.utils import (
    MapperEvent, CIRCLE, RECT, RELOAD_DELAY,
    create_default_toml, update_toml
    )

if TYPE_CHECKING:
    from .config import AppConfig

class JSONLoader():
    def __init__(self, config:AppConfig, foreground_window):
        _, WindowMgrClass, _, _ = get_platform()
        self.window_manager = WindowMgrClass()

        self.config = config
        self.mapper_event_dispatcher = config.mapper_event_dispatcher
        self.foreground_window = foreground_window

        # State tracking
        self.last_loaded_json_path = None
        self.last_loaded_json_timestamp = 0
        self.json_data: list[tuple[str, dict]] = []
        self.last_reload_time = 0