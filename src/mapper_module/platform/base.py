from abc import ABC, abstractmethod

class AbstractWindowManager(ABC):
    @abstractmethod
    def get_foreground_window(self): pass
    
    @abstractmethod
    def enum_windows(self): pass
    
    @abstractmethod
    def get_window_class(self, window): pass
    
    @abstractmethod
    def get_client_rect(self, window): pass
    
    @abstractmethod
    def get_window_position(self, window): pass
    
    @abstractmethod
    def is_cursor_visible(self): pass

class AbstractBridge(ABC):   
    @abstractmethod
    def key_down(self, code): pass
    
    @abstractmethod
    def key_up(self, code): pass
    
    @abstractmethod
    def mouse_move_rel(self, dx, dy): pass
    
    @abstractmethod
    def mouse_move_abs(self, x, y): pass
    
    @abstractmethod
    def left_click_down(self): pass
    
    @abstractmethod
    def left_click_up(self): pass
    
    @abstractmethod
    def right_click_down(self): pass
    
    @abstractmethod
    def right_click_up(self): pass
    
    @abstractmethod
    def middle_click_down(self): pass
    
    @abstractmethod
    def middle_click_up(self): pass

    @abstractmethod
    def health_check(self):
        """Monitors and restarts driver-specific worker processes."""
        pass
    
    @abstractmethod
    def release_all(self): pass
    
class AbstractSystemConfig(ABC):
    @abstractmethod
    def set_dpi_awareness(self): pass
    
    @abstractmethod
    def set_timer_resolution(self): pass
    
    @abstractmethod
    def set_high_priority(self, pid, label): pass

class AbstractMapping(ABC):
    @property
    @abstractmethod
    def modifier_map(self):
        """
        Dictionary mapping native OS scancodes to standardized key strings.
        Example: {56: 'lalt', 29: 'lctrl'}
        """
        pass
    
    @abstractmethod
    def get_key_from_scancode(self, scancode):
        """
        Translates a native OS scancode into a standardized key name.
        """
        pass
    
    @abstractmethod
    def get_scancode_from_key(self, key_name):
        """
        Translates a standardized key name into a native OS scancode.
        """
        pass