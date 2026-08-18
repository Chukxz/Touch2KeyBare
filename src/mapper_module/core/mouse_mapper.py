from __future__ import annotations
from typing import TYPE_CHECKING

from time import sleep as _sleep
from random import uniform as _uniform
import threading

from mapper_module.utils import UP, DOWN, PRESSED, TAP_SLOP_DP, TAP_MAX_TIME_NS

if TYPE_CHECKING:
    from .mapper import Mapper
    from mapper_module.utils import TouchEvent


class MouseMapper:
    def __init__(self, mapper: Mapper):
        self.mapper = mapper
        self.mapper_event_dispatcher = self.mapper.mapper_event_dispatcher
        self.bridge = mapper.bridge
        self.config = mapper.config

        self.prev_x = None
        self.prev_y = None
        self.acc_x = 0.0
        self.acc_y = 0.0
        self.left_down = False
        self.scaling_factor = 1.0
        self.timestamp = 0.0
        self.click_lock = threading.Lock()

        self.tap_in_progress = False
        self._update_config()

        # Register callbacks
        self.mapper_event_dispatcher.register_callback(
            "ON_CONFIG_RELOAD", self._update_config
        )
        self.mapper_event_dispatcher.register_callback(
            "ON_AGGREGATION", self._aggregate
        )
        self.mapper_event_dispatcher.register_callback(
            "ON_WORKER_RESPAWN", self._on_worker_respawn
        )

    def _update_config(self):
        """Pre-calculates sensitivity to keep the _touch_pressed loop lean."""
        print(f"\n[MOUSEMAPPER] - Syncing sensitivity...")
        try:
            with self.config.config_lock:
                mouse_cfg = self.config.config_data.get("mouse", {})
                base_sens = mouse_cfg.get("sensitivity", 1.0)
                base_sens = max(0.1, min(base_sens, 10.0))  # Sensitivity guardrail

            with self.mapper.lock:
                pc_w = self.mapper.screen_w
                dev_w = self.mapper.device_width

            if dev_w > 0:
                resolution_ratio = pc_w / dev_w
            else:
                print(
                    "\n[MOUSEMAPPER] - Device width is not a positive integer. Defaulting ratio to 1.0."
                )
                resolution_ratio = 1.0

            self.scaling_factor = base_sens * resolution_ratio

            print(
                f"\n[MOUSEMAPPER] - Sync: PC width ({pc_w}px) / Phone width ({dev_w}px) = Ratio ({resolution_ratio:.2f}).\
                    \n[MOUSEMAPPER] - Final Scaling Factor: {self.scaling_factor:.4f} (User Sensitivity: {base_sens}x)."
            )

        except Exception as e:
            print(f"\n[MOUSEMAPPER] - Mouse config update failed: {e}.")
            self.scaling_factor = 1.0

    def _touch_down(self, touch_event: TouchEvent, is_visible: bool):
        """
        Anchor the start position and reset precision accumulators
        """
        self.prev_x = touch_event.x
        self.prev_y = touch_event.y
        self.acc_x = 0.0
        self.acc_y = 0.0

        if is_visible:
            _x, _y = self.mapper.device_to_game_abs(self.prev_x, self.prev_y)
            self.bridge.mouse_move_abs(_x, _y)
            with self.click_lock:
                self.bridge.left_click_down()
                self.left_down = True

        else:
            self.timestamp = touch_event.timestamp

    def _touch_pressed(self, touch_event: TouchEvent, is_visible: bool):
        """
        The 'Hot Path'. This code runs hundreds of times per second.
        Optimized to minimize branching and float operations.
        """
        # prev_x or prev_y can be none if the ADB connection was lost and the touch points were reset. In that case, we need to re-anchor before calculating deltas.
        # Treat it as a fresh touch down, which will also reset the accumulators and prevent a large jump in the first movement packet after reconnection.
        if self.prev_x is None or self.prev_y is None:
            self._touch_down(touch_event, is_visible)
            return

        # Calculate Raw Delta
        raw_dx = touch_event.x - self.prev_x
        raw_dy = touch_event.y - self.prev_y

        # Update anchors immediately
        self.prev_x = touch_event.x
        self.prev_y = touch_event.y

        self.acc_x, self.acc_y = self._process_deltas(
            raw_dx, raw_dy, self.acc_x, self.acc_y
        )

    def touch_up(
        self,
        touchevent: TouchEvent | None,
        is_visible: bool,
        activate_mouse_sequence: bool,
    ):
        self.prev_x = None
        self.prev_y = None
        self.acc_x = 0.0
        self.acc_y = 0.0

        with self.click_lock:
            if self.left_down:
                self.bridge.left_click_up()
                self.left_down = False

        if activate_mouse_sequence and touchevent is not None and not is_visible:
            if not self.tap_in_progress:
                self.tap_in_progress = True
                now = touchevent.timestamp
                temporal_diff = now - self.timestamp
                spatial_diff_squared = (touchevent.sx - touchevent.x) ** 2 + (
                    touchevent.sy - touchevent.y
                ) ** 2
                tap_slop_px_squared = self.mapper.dp_to_px(TAP_SLOP_DP) ** 2

                if (
                    temporal_diff <= TAP_MAX_TIME_NS
                    and spatial_diff_squared <= tap_slop_px_squared
                ):
                    threading.Thread(
                        target=self._toggle_key_mouse_sequence,
                        args=(touchevent,),
                        daemon=True,
                    ).start()
                else:
                    self.tap_in_progress = False

        self.timestamp = 0.0

    def _toggle_key_mouse_sequence(self, touchevent: TouchEvent):
        self._tap_toggle_key()
        _sleep(_uniform(0.04, 0.12))
        self._left_click_mouse(touchevent)
        _sleep(_uniform(0.06, 0.18))
        self._tap_toggle_key()
        self.tap_in_progress = False

    def _tap_toggle_key(self):
        if self.mapper.toggle_key_scancode:
            self.bridge.key_down(self.mapper.toggle_key_scancode)
            _sleep(_uniform(0.02, 0.09))
            self.bridge.key_up(self.mapper.toggle_key_scancode)

    def _left_click_mouse(self, touchevent: TouchEvent):
        _x, _y = self.mapper.device_to_game_abs(touchevent.x, touchevent.y)
        self.bridge.mouse_move_abs(_x, _y)
        _sleep(_uniform(0.016, 0.04))
        self.bridge.left_click_down()
        _sleep(_uniform(0.02, 0.07))
        self.bridge.left_click_up()

    def _aggregate(self, raw_dx: float, raw_dy: float, acc_x: float, acc_y: float):
        self.mapper.acc_x, self.mapper.acc_y = self._process_deltas(
            raw_dx, raw_dy, acc_x, acc_y
        )

    def _process_deltas(self, raw_dx: float, raw_dy: float, acc_x: float, acc_y: float):
        # Apply Multiplier and add previous remainders (Sub-pixel precision)
        # Using float math here is necessary for 1:1 feel
        calc_dx = (raw_dx * self.scaling_factor) + acc_x
        calc_dy = (raw_dy * self.scaling_factor) + acc_y

        # Truncate to integer (actual pixels to move)
        final_dx = int(calc_dx)
        final_dy = int(calc_dy)   

        # Fast-Exit for Noise
        # If the delta is less than 1 physical pixel, just keep the remainder and exit.
        if final_dx == 0 and final_dy == 0:
            acc_x = calc_dx
            acc_y = calc_dy
            return acc_x, acc_y

        # Save remainders for next packet
        acc_x = calc_dx - final_dx
        acc_y = calc_dy - final_dy
        
        # Clamp values
        final_dx = max(-32000, min(32000, final_dx))
        final_dy = max(-32000, min(32000, final_dy))

        # Physical movement execution
        self.bridge.mouse_move_rel(final_dx, final_dy)
        return acc_x, acc_y

    def process_touch(
        self,
        action,
        touch_event: TouchEvent,
        is_visible: bool,
        activate_mouse_sequence: bool,
    ):
        if action == PRESSED:
            self._touch_pressed(touch_event, is_visible)

        elif action == DOWN:
            self._touch_down(touch_event, is_visible)

        elif action == UP:
            self.touch_up(touch_event, is_visible, activate_mouse_sequence)

    def _on_worker_respawn(self, worker_type: str):
        if worker_type != "mouse":
            return
        with self.click_lock:
            if self.left_down:
                self.bridge.left_click_down()
