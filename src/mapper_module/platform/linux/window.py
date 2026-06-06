from typing import Any
from ..base import AbstractWindowManager
from Xlib import display, X, error

# Note: Requires `pip install python-xlib`

class WindowManager(AbstractWindowManager):
    def __init__(self):
        # Connect to the local X server display
        try:
            self.disp = display.Display()
            self.root = self.disp.screen().root
            
            # X11 uses "Atoms" (cached strings) to query window properties
            self.NET_ACTIVE_WINDOW = self.disp.intern_atom('_NET_ACTIVE_WINDOW')
            self.NET_WM_NAME = self.disp.intern_atom('_NET_WM_NAME')
        except Exception as e:
            print(f"[WINDOW MANAGER] - Failed to connect to X11 Display. Ensure you are on X11, not pure Wayland: {e}")
            self.disp = None

    def _get_window_obj(self, hwnd: int):
        """Helper to cast an integer ID back to an Xlib Window object."""
        return self.disp.create_resource_object('window', hwnd)

    def _get_all_windows(self, window=None) -> list:
        """Helper to recursively traverse the X11 window tree."""
        if window is None: 
            window = self.root
        windows = [window]
        try:
            for child in window.query_tree().children:
                windows.extend(self._get_all_windows(child))
        except error.BadWindow:
            pass
        return windows

    def get_foreground_window(self) -> int:
        if not self.disp: return 0
        try:
            win_id = self.root.get_full_property(self.NET_ACTIVE_WINDOW, X.AnyPropertyType)
            if win_id and win_id.value:
                return win_id.value
        except Exception:
            pass
        return 0

    def is_window_valid(self, hwnd: int) -> bool:
        if not self.disp or hwnd == 0: return False
        try:
            win = self._get_window_obj(hwnd)
            win.get_attributes()  # Will throw BadWindow if invalid
            return True
        except error.BadWindow:
            return False

    def is_window_visible(self, hwnd: int) -> bool:
        if not self.disp or hwnd == 0: return False
        try:
            win = self._get_window_obj(hwnd)
            attr = win.get_attributes()
            return attr.map_state == X.IsViewable
        except error.BadWindow:
            return False

    def get_window_class_name(self, hwnd: int) -> str:
        if not self.disp or hwnd == 0: return ""
        try:
            win = self._get_window_obj(hwnd)
            wm_class = win.get_wm_class()
            # X11 classes are tuples: ('instance_name', 'Class_Name')
            if wm_class and len(wm_class) > 1:
                return wm_class
        except Exception:
            pass
        return ""

    def find_window_by_title(self, title: str) -> Any | None:
        if not self.disp: return None
        # X11 requires searching the tree to find titles
        titles_dict = self.find_window_titles()
        for hwnd, win_title in titles_dict.items():
            if win_title == title:
                return hwnd
        return None

    def find_hwnds_by_class(self, class_name: str | None) -> list:
        if not self.disp or not class_name: return []
        results = []
        for win in self._get_all_windows():
            try:
                wm_class = win.get_wm_class()
                if wm_class and len(wm_class) > 1 and wm_class == class_name:
                    results.append(win.id)
            except error.BadWindow:
                continue
        return results

    def get_client_rect(self, hwnd: int) -> tuple[int, int]:
        if not self.disp or hwnd == 0: return 0, 0
        try:
            win = self._get_window_obj(hwnd)
            geom = win.get_geometry()
            # X11 get_geometry returns inner client dimensions, excluding WM borders
            return geom.width, geom.height
        except Exception:
            return 0, 0

    def get_window_position(self, hwnd: int) -> tuple[int, int]:
        if not self.disp or hwnd == 0: return 0, 0
        try:
            win = self._get_window_obj(hwnd)
            # Translate local coordinates (0, 0) to global root/screen coordinates
            coords = win.translate_coords(self.root, 0, 0)
            return coords.x, coords.y
        except Exception:
            return 0, 0

    def is_cursor_visible(self) -> bool:
        # X11 cursor visibility tracking requires the XFixes extension.
        # To avoid heavy/unstable dependencies, we fallback to True.
        # In Linux, cursor hiding is usually handled by the game capturing it.
        return True

    def get_screen_metrics(self) -> tuple[int, int]:
        if not self.disp: return 1920, 1080 # Safe fallback
        screen = self.disp.screen()
        return screen.width_in_pixels, screen.height_in_pixels

    def find_window_titles(self) -> dict:
        if not self.disp: return {}
        results = {}
        for win in self._get_all_windows():
            try:
                attr = win.get_attributes()
                if attr.map_state == X.IsViewable:
                    # Check legacy WM_NAME first
                    name = win.get_wm_name()
                    if not name:
                        # Fallback to modern EWMH _NET_WM_NAME
                        net_name = win.get_full_property(self.NET_WM_NAME, 0)
                        if net_name:
                            name = net_name.value.decode('utf-8', errors='ignore')
                    if name:
                        results[win.id] = name
            except Exception:
                continue
        return results
