from typing import ClassVar
from ..base import AbstractMapping

class Mapping(AbstractMapping):
    """Windows-specific scancode mapping implementation."""
    
    # Use ClassVar to tell Pylance this is a class attribute, not a property method
    modifier_map: ClassVar[dict[int, str]] = {
        56: "lalt",
        312: "ralt",
        29: "lctrl",
        285: "rctrl",
        42: "lshift",
        54: "rshift"
    }
    
    # Generate reverse map once at class load for O(1) lookups
    _reverse_map: ClassVar[dict[str, int]] = {v: k for k, v in modifier_map.items()}

    def get_key_from_scancode(self, scancode: int) -> str:
        """Translates a Windows native scancode to a standard key string."""
        return self.modifier_map.get(scancode, "")

    def get_scancode_from_key(self, key_name: str) -> int:
        """Translates a standard key string to a Windows native scancode."""
        return self._reverse_map.get(key_name, 0)