from __future__ import annotations
from typing import TYPE_CHECKING

import time
from .utils import (
    DOWN, UP, PRESSED, TAP_SLOP_DP, TAP_MAX_TIME
)

if TYPE_CHECKING:
    from .mapper import Mapper
    from .utils import TouchEvent

class MouseMapper():
    def __init__(self, mapper:Mapper):
        self.mapper = mapper
        self.mapper_event_dispatcher = self.mapper.mapper_event_dispatcher
        self.interception_bridge = mapper.interception_bridge
        self.config = mapper.config

        self.prev_x = None
        self.prev_y = None
        self.acc_x = 0.0
        self.acc_y = 0.0
        self.left_down = False
        self.scaling_factor = 1.0
        self.timestamp = 0.0

        self.update_config()

        # Register Callbacks
        self.mapper_event_dispatcher.register_callback("ON_CONFIG_RELOAD", self.update_config)


    def update_config(self):
        """Pre-calculates sensitivity to keep the touch_pressed loop lean."""
        print(f"\n[MOUSEMAPPER] - Syncing sensitivity...")
        try:
            with self.config.config_lock:
                mouse_cfg = self.config.config_data.get('mouse', {})
                base_sens = mouse_cfg.get('sensitivity', 1.0)
            
            with self.mapper.lock:                
                pc_w = self.mapper.screen_w
                dev_w = self.mapper.device_width

            if dev_w > 0:
                resolution_ratio = pc_w / dev_w
            else:
                print("\n[MOUSEMAPPER] - Device width is not a positive integer. Defaulting ratio to 1.0.")
                resolution_ratio = 1.0

            self.scaling_factor = base_sens * resolution_ratio
            
            print(f"\n[MOUSEMAPPER] - Sync: PC width ({pc_w}px) / Phone width ({dev_w}px) = Ratio ({resolution_ratio:.2f}).")
            print(f"\n[MOUSEMAPPER] - Final Scaling Factor: {self.scaling_factor:.4f} (User Sensitivity: {base_sens}x).")

        except Exception as e:
            print(f"\n[MOUSEMAPPER] - Mouse config update failed: {e}.")
            self.scaling_factor = 1.0

    def touch_down(self, touch_event:TouchEvent, is_visible:bool):
        """
        Anchor the start position and reset precision accumulators
        """
        self.prev_x = touch_event.x
        self.prev_y = touch_event.y
        self.acc_x = 0.0
        self.acc_y = 0.0

        if is_visible:           
            _x, _y = self.mapper.device_to_game_abs(self.prev_x, self.prev_y)
            self.interception_bridge.mouse_move_abs(_x, _y)
            self.interception_bridge.left_click_down()
            self.left_down = True
        
        else:
            self.timestamp = touch_event.timestamp


    def touch_pressed(self, touch_event:TouchEvent, is_visible:bool):
        """
        The 'Hot Path'. This code runs hundreds of times per second.
        Optimized to minimize branching and float operations.
        """
        # prev_x or prev_y can be none if the ADB connection was lost and the touch points were reset. In that case, we need to re-anchor before calculating deltas.
        # Treat it as a fresh touch down, which will also reset the accumulators and prevent a large jump in the first movement packet after reconnection.
        if self.prev_x is None or self.prev_y is None:
            self.touch_down(touch_event, is_visible)
            return

        # Calculate Raw Delta
        raw_dx = touch_event.x - self.prev_x
        raw_dy = touch_event.y - self.prev_y

        # Update anchors immediately
        self.prev_x = touch_event.x
        self.prev_y = touch_event.y

        # Apply Multiplier and add previous remainders (Sub-pixel precision)
        # Using float math here is necessary for 1:1 feel
        calc_dx = (raw_dx * self.scaling_factor) + self.acc_x
        calc_dy = (raw_dy * self.scaling_factor) + self.acc_y

        # Truncate to Integer (Actual pixels to move)
        final_dx = int(calc_dx)
        final_dy = int(calc_dy)

        # Fast-Exit for Noise
        # If the delta is less than 1 physical pixel, just keep the remainder and exit.
        if final_dx == 0 and final_dy == 0:
            self.acc_x = calc_dx
            self.acc_y = calc_dy
            return

        # Save remainders for next packet
        self.acc_x = calc_dx - final_dx
        self.acc_y = calc_dy - final_dy

        # Physical movement execution
        self.interception_bridge.mouse_move_rel(final_dx, final_dy)

    def touch_up(self, touchevent:TouchEvent | None, is_visible:bool):
        self.prev_x = None
        self.prev_y = None
        self.acc_x = 0.0
        self.acc_y = 0.0
        
        if self.left_down:
            self.interception_bridge.left_click_up()
            self.left_down = False
        
        if touchevent is not None and not is_visible:
            now = touchevent.timestamp
            temporal_diff = now - self.timestamp
            spatial_diff_squared = (touchevent.sx - touchevent.x)**2 + (touchevent.sy - touchevent.y)**2
            
            tap_slop_px_squared = self.mapper.dp_to_px(TAP_SLOP_DP)**2
            
            if temporal_diff <= TAP_MAX_TIME and spatial_diff_squared <= tap_slop_px_squared:
                self.interception_bridge.key_down(self.mapper.toggle_key_scancode)
                time.sleep(0.2)
                
                _x, _y = self.mapper.device_to_game_abs(touchevent.x, touchevent.y)
                self.interception_bridge.mouse_move_abs(_x, _y)
                self.interception_bridge.left_click_down()                
                time.sleep(0.2)
                self.interception_bridge.left_click_up()
                time.sleep(0.2)
                
                self.interception_bridge.key_up(self.mapper.toggle_key_scancode)
            
        self.timestamp = 0.0


    def process_touch(self, action, touch_event:TouchEvent, is_visible:bool):
        if action == PRESSED:
            self.touch_pressed(touch_event, is_visible)

        elif action == DOWN:
            self.touch_down(touch_event, is_visible)

        elif action == UP:
            self.touch_up(touch_event, is_visible)
