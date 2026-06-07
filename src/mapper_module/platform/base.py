from typing import Any
from abc import ABC, abstractmethod

class AbstractWindowManager(ABC):
    @abstractmethod
    def get_foreground_window(self) -> int: pass
    
    @abstractmethod
    def is_window_valid(self, hwnd) -> bool: pass
        
    @abstractmethod
    def is_window_visible(self, hwnd) -> bool: pass
        
    @abstractmethod
    def get_window_class_name(self, hwnd) -> str: pass
    
    @abstractmethod
    def find_window_by_title(self, title: str) -> Any | None: pass
    
    @abstractmethod
    def find_hwnds_by_class(self, class_name: str | None) -> list: pass
    
    @abstractmethod
    def get_client_rect(self, hwnd) -> tuple[int, int]: pass

    @abstractmethod
    def get_window_position(self, hwnd) -> tuple[int, int]: pass

    @abstractmethod
    def is_cursor_visible(self, last_state: bool, last_check_time: int) -> tuple[bool, int]: pass

    @abstractmethod
    def get_screen_metrics(self) -> tuple[int, int]: pass
    
    @abstractmethod
    def find_window_titles(self) -> dict: pass

class AbstractBridge(ABC):   
    @abstractmethod
    def key_down(self, code: int) -> None: pass
    
    @abstractmethod
    def key_up(self, code: int) -> None: pass
    
    @abstractmethod
    def mouse_move_rel(self, dx: int, dy: int) -> None: pass
    
    @abstractmethod
    def mouse_move_abs(self, x: int, y: int) -> None: pass
    
    @abstractmethod
    def left_click_down(self) -> None: pass
    
    @abstractmethod
    def left_click_up(self) -> None: pass
    
    @abstractmethod
    def right_click_down(self) -> None: pass
    
    @abstractmethod
    def right_click_up(self) -> None: pass
    
    @abstractmethod
    def middle_click_down(self) -> None: pass
    
    @abstractmethod
    def middle_click_up(self) -> None: pass

    @abstractmethod
    def health_check(self):
        """Monitors and restarts driver-specific worker processes."""
        pass
    
    @abstractmethod
    def release_all(self) -> None: pass
    
class AbstractSystemConfig(ABC):
    @abstractmethod
    def set_dpi_awareness(self) -> None: pass
    
    @abstractmethod
    def set_timer_resolution(self) -> None: pass
    
    @abstractmethod
    def set_high_priority(self, pid: int | None, label: str) -> None: pass

class AbstractMapping(ABC):    
    @abstractmethod
    def get_key_from_scancode(self, scancode: int) -> str:
        """
        Translates a native OS scancode into a standardized key name.
        """
        pass
    
    @abstractmethod
    def get_scancode_from_key(self, key_name: str) -> int:
        """
        Translates a standardized key name into a native OS scancode.
        """
        pass
