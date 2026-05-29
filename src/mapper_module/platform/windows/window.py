import ctypes
from ctypes import wintypes
import win32gui

MAX_CLASS_NAME = 256

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long)
    ]

class WindowManager:
    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool, wintypes.HWND, wintypes.LPARAM
    )

    def get_foreground_window(self):
        return win32gui.GetForegroundWindow()

    def is_window_valid(self, hwnd):
        return bool(ctypes.windll.user32.IsWindow(hwnd))

    def is_window_visible(self, hwnd):
        return bool(ctypes.windll.user32.IsWindowVisible(hwnd))

    def get_window_class_name(self, hwnd):
        buffer = ctypes.create_unicode_buffer(MAX_CLASS_NAME)
        ctypes.windll.user32.GetClassNameW(hwnd, buffer, MAX_CLASS_NAME)
        return buffer.value

    def find_window_by_title(self, title):
        return ctypes.windll.user32.FindWindowW(None, title)

    def enum_class_windows_callback(self, hwnd, lParam):
        target_class = ctypes.cast(
            lParam, ctypes.POINTER(ctypes.py_object)
        ).contents.value['class_name']
        results = ctypes.cast(
            lParam, ctypes.POINTER(ctypes.py_object)
        ).contents.value['results']

        buffer = ctypes.create_unicode_buffer(MAX_CLASS_NAME)
        ctypes.windll.user32.GetClassNameW(hwnd, buffer, MAX_CLASS_NAME)
        if buffer.value == target_class:
            results.append(hwnd)
        return True

    def find_hwnds_by_class(self, class_name):
        results = []
        data = ctypes.py_object({
            'class_name': class_name,
            'results': results
        })
        ctypes.windll.user32.EnumWindows(
            self.EnumWindowsProc(self.enum_class_windows_callback),
            ctypes.byref(data)
        )
        return results

    def get_client_rect(self, hwnd):
        rect = RECT()
        ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        return width, height

    def get_window_position(self, hwnd):
        pt = POINT()
        pt.x = 0
        pt.y = 0
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt))
        return pt.x, pt.y

    def is_cursor_visible(self):
        try:
            flags, _, _ = win32gui.GetCursorInfo()  # type: ignore
            return bool(flags & 1)
        except Exception:
            return True

    def get_screen_metrics(self):
        w = ctypes.windll.user32.GetSystemMetrics(0)
        h = ctypes.windll.user32.GetSystemMetrics(1)
        return w, h

    def enum_title_windows_callback(self, hwnd, results: dict):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                results[hwnd] = title

    def find_window_titles(self):
        current_windows_titles = {}
        win32gui.EnumWindows(self.enum_title_windows_callback, current_windows_titles)
        return current_windows_titles