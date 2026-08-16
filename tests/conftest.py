import pytest
from mapper_module.platforms.base import AbstractBridge


class MockBridge(AbstractBridge):
    """A fake bridge that intercepts hardware calls for testing."""

    def __init__(self):
        self.injected_keys = []

    def key_down(self, code: int) -> None:
        self.injected_keys.append(("DOWN", code))

    def key_up(self, code: int) -> None:
        self.injected_keys.append(("UP", code))

    def mouse_move_rel(self, dx: int, dy: int) -> None:
        pass

    def mouse_move_abs(self, x: int, y: int) -> None:
        pass

    def left_click_down(self) -> None:
        pass

    def left_click_up(self) -> None:
        pass

    def right_click_down(self) -> None:
        pass

    def right_click_up(self) -> None:
        pass

    def middle_click_down(self) -> None:
        pass

    def middle_click_up(self) -> None:
        pass

    def health_check(self):
        """Monitors and restarts driver-specific worker processes."""
        pass

    def release_all(self) -> None:
        pass


@pytest.fixture
def mock_bridge():
    """Provides a fresh MockBridge for every test."""
    return MockBridge()
