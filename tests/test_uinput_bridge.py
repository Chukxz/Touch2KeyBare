# import pytest
# from unittest.mock import MagicMock, patch
# from mapper_module.platform.linux.bridge import UInputBridge
# from mapper_module.utils import (
#     PACK_KEY,
#     PACK_ABS,
#     TASK_ABS,
#     LEFT_BUTTON_DOWN,
#     PACK_BUTTON,
#     TASK_BUTTON,
# )


# @pytest.fixture
# def mock_dependencies():
#     """Provides mocked WindowManager and SystemConfig."""
#     mock_wm = MagicMock()
#     # Mocking a standard 1080p display for coordinate normalization testing
#     mock_wm.get_screen_dimensions.return_value = (1920, 1080)

#     mock_sc = MagicMock()
#     return mock_wm, mock_sc


# # We patch multiprocessing.Process so the test doesn't spawn real daemon workers
# @patch("mapper_module.platform.linux.bridge.multiprocessing.Process")
# def test_bridge_initialization(mock_process, mock_dependencies):
#     """Ensure the bridge grabs dimensions and attempts to start both workers."""
#     wm, sc = mock_dependencies
#     bridge = UInputBridge(wm, sc)

#     assert bridge.screen_w == 1920
#     assert bridge.screen_h == 1080
#     assert mock_process.call_count == 2  # Should spawn Keyboard and Mouse workers
#     assert sc.set_high_priority.call_count == 2


# @patch("mapper_module.platform.linux.bridge.multiprocessing.Process")
# def test_key_down_packing(mock_process, mock_dependencies):
#     """Verify that a key press correctly packs the 3-byte payload and sends it."""
#     wm, sc = mock_dependencies
#     bridge = UInputBridge(wm, sc)

#     # Mock the write end of the keyboard pipe
#     bridge.k_pipe_write = MagicMock()

#     # Simulate pressing scancode 0x1E (typically 'A')
#     test_scancode = 0x1E
#     bridge.key_down(test_scancode)

#     # UInputBridge logic dictates state '1' for key down
#     expected_bytes = PACK_KEY.pack(test_scancode, 1)

#     bridge.k_pipe_write.send_bytes.assert_called_once_with(expected_bytes)
#     assert test_scancode in bridge._pressed_keys


# @patch("mapper_module.platform.linux.bridge.multiprocessing.Process")
# def test_mouse_move_abs_normalization(mock_process, mock_dependencies):
#     """Verify that absolute mouse movements are correctly normalized to 65535."""
#     wm, sc = mock_dependencies
#     bridge = UInputBridge(wm, sc)

#     # Mock the write end of the mouse pipe
#     bridge.m_pipe_write = MagicMock()

#     # Simulate a touch exactly in the middle of a 1920x1080 screen
#     bridge.mouse_move_abs(960, 540)

#     # 960/1920 = 0.5 -> 0.5 * 65535 = 32767
#     expected_x = 32767
#     expected_y = 32767
#     expected_bytes = PACK_ABS.pack(TASK_ABS, expected_x, expected_y)

#     bridge.m_pipe_write.send_bytes.assert_called_once_with(expected_bytes)
