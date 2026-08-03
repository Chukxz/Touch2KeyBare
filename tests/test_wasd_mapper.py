import pytest
from unittest.mock import MagicMock
from mapper_module.core.wasd_mapper import WASDMapper, _State


# Mock TouchEvent matching your exact signature
class TouchEvent:
    def __init__(
        self,
        slot: int,
        id: int,
        x: float,
        y: float,
        sx: float,
        sy: float,
        timestamp: float,
        is_mouse: bool,
        is_wasd: bool,
    ):
        self.slot = slot
        self.id = id
        self.x = x
        self.y = y
        self.sx = sx
        self.sy = sy
        self.timestamp = timestamp
        self.is_mouse = is_mouse
        self.is_wasd = is_wasd


# Helper function to generate clean touch events for our tests
def _make_touch(x: float, y: float) -> TouchEvent:
    return TouchEvent(
        slot=0,
        id=1,
        x=x,
        y=y,
        sx=0.0,
        sy=0.0,
        timestamp=0.0,
        is_mouse=False,
        is_wasd=True,
    )


@pytest.fixture
def mock_bridge():
    """A fake OS bridge to capture hardware injection calls."""
    return MagicMock()


@pytest.fixture
def mock_mapper_orchestrator(mock_bridge):
    """A fake Mapper orchestrator structured exactly how WASDMapper expects."""
    mapper = MagicMock()
    mapper.bridge = mock_bridge

    mock_json_loader = MagicMock()
    # Inner Radius: 20, d_radius: 100 (Outer Radius = 120)
    mock_json_loader.get_mouse_wheel_info.return_value = (20.0, 100.0)
    mapper.json_loader = mock_json_loader

    mock_config = MagicMock()
    mock_config.config_data = {
        "joystick": {"deadzone": 0.1, "hysteresis": 5.0},
        "mouse": {"sensitivity": 1.0},
    }
    mapper.config = mock_config

    mapper.mapper_event_dispatcher = MagicMock()
    mapper.emulator = {"sprint_key": "LSHIFT"}
    mapper.wasd_block = 0
    return mapper


def test_wasd_initialization(mock_mapper_orchestrator):
    """Ensure the WASDMapper initializes math and config without crashing."""
    wasd = WASDMapper(mock_mapper_orchestrator)
    assert wasd.current_mask == _State.NONE
    assert wasd.inner_radius_sq == 400.0  # 20.0 squared


def test_joystick_forward_movement(mock_mapper_orchestrator, mock_bridge):
    """Verify that pushing the joystick UP calculates Sector 6 and presses W."""
    wasd = WASDMapper(mock_mapper_orchestrator)

    # Touch center
    wasd._touch_down(_make_touch(500, 500), is_visible=False)

    # Drag UP by 15 pixels (Y=485) - Past 10px deadzone, under 20px sprint
    wasd._touch_pressed(_make_touch(500, 485), is_visible=False)

    # Verify ONLY W was pressed
    mock_bridge.key_down.assert_called_once_with(wasd.KEY_W)
    assert wasd.current_mask == _State.W


def test_joystick_diagonal_transition(mock_mapper_orchestrator, mock_bridge):
    """Verify moving from UP to UP-LEFT correctly triggers a differential update."""
    wasd = WASDMapper(mock_mapper_orchestrator)
    wasd._touch_down(_make_touch(500, 500), is_visible=False)

    wasd._touch_pressed(_make_touch(500, 485), is_visible=False)
    mock_bridge.reset_mock()

    # Now drag thumb UP-LEFT (X and Y both decrease)
    wasd._touch_pressed(_make_touch(485, 485), is_visible=False)

    # It should ONLY press 'A' (W is already pressed)
    mock_bridge.key_down.assert_called_once_with(wasd.KEY_A)
    mock_bridge.key_up.assert_not_called()
    assert wasd.current_mask == (_State.W | _State.A)


def test_joystick_sprint_trigger(mock_mapper_orchestrator, mock_bridge):
    """Verify that pushing past the outer radius threshold triggers sprint."""
    wasd = WASDMapper(mock_mapper_orchestrator)
    wasd._touch_down(_make_touch(500, 500), is_visible=False)

    # Drag thumb UP by 150 pixels (past the 120px Outer Radius)
    wasd._touch_pressed(_make_touch(500, 350), is_visible=False)

    # Verify both W and Sprint were pressed
    mock_bridge.key_down.assert_any_call(wasd.KEY_W)
    mock_bridge.key_down.assert_any_call(wasd.sprint_key_code)
    assert wasd.sprinting is True


def test_joystick_thumb_release(mock_mapper_orchestrator, mock_bridge):
    """Verify lifting the thumb releases all active keys and clears state."""
    wasd = WASDMapper(mock_mapper_orchestrator)

    wasd._touch_down(_make_touch(500, 500), is_visible=False)
    wasd._touch_pressed(_make_touch(500, 485), is_visible=False)

    mock_bridge.reset_mock()

    # Lift thumb
    wasd.touch_up()

    # Verify ONLY W was released
    mock_bridge.key_up.assert_called_once_with(wasd.KEY_W)
    assert wasd.current_mask == _State.NONE
    assert wasd.center_x == 0.0
