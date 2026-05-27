from typing import ClassVar
from ..base import AbstractMapping

class Mapping(AbstractMapping):
    """Linux-specific scancode mapping implementation."""
    
    # Fulfills the @property contract from AbstractMapping
    modifier_map: ClassVar[dict[int, str]] = {
        64: "lalt",
        108: "ralt",
        37: "lctrl",
        105: "rctrl",
        50: "lshift",
        62: "rshift"
    }

    # Generate reverse map once at class load for O(1) lookups
    _reverse_map: ClassVar[dict[str, int]] = {v: k for k, v in modifier_map.items()}

    def get_key_from_scancode(self, scancode: int) -> str:
        """Translates a Linux native scancode to a standard key string."""
        return self.modifier_map.get(scancode, "")

    def get_scancode_from_key(self, key_name: str) -> int:
        """Translates a standard key string to a Linux native scancode."""
        return self._reverse_map.get(key_name, 0)
    
    