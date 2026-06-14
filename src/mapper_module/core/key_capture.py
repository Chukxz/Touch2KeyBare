import sys
from mapper_module.platform import get_platform
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class KeyCaptureDialog(QDialog):
    def __init__(self, prompt: str, skippable: bool = False):
        super().__init__()
        self.setWindowTitle("Key Capture")
        self.setFixedSize(400, 200)
        self.captured_key: str | None = None
        self.skippable = skippable
        self._listening = True

        layout = QVBoxLayout()

        self.prompt_label = QLabel(prompt)
        self.prompt_label.setAlignment(Qt.AlignCenter)
        self.prompt_label.setFont(QFont("Courier", 10))
        layout.addWidget(self.prompt_label)

        self.key_label = QLabel("Waiting for keypress...")
        self.key_label.setAlignment(Qt.AlignCenter)
        self.key_label.setFont(QFont("Courier", 14))
        layout.addWidget(self.key_label)

        btn_layout = QHBoxLayout()

        self.retry_btn = QPushButton("Retry")
        self.retry_btn.setEnabled(False)
        self.retry_btn.clicked.connect(self._retry)
        btn_layout.addWidget(self.retry_btn)

        self.confirm_btn = QPushButton("Confirm")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self._confirm)
        btn_layout.addWidget(self.confirm_btn)

        if skippable:
            self.skip_btn = QPushButton("Skip (None)")
            self.skip_btn.clicked.connect(self._skip)
            btn_layout.addWidget(self.skip_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._cancel)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def keyPressEvent(self, event):
        if not self._listening:
            return

        # Qt key name — convert to scancode key name format
        scan_code = event.nativeScanCode()
        key_name = self.mapping.get_key_from_scancode(scan_code)

        # Fall back to Qt key map for non-modifier keys
        if not key_name:
            key_name = self._qt_key_to_name(event.key())

        if key_name is None:
            return

    self.captured_key = key_name
    self.key_label.setText(f"Captured: {key_name}")
    self._listening = False
    self.retry_btn.setEnabled(True)
    self.confirm_btn.setEnabled(True)

    def _retry(self):
        self.captured_key = None
        self.key_label.setText("Waiting for keypress...")
        self._listening = True
        self.retry_btn.setEnabled(False)
        self.confirm_btn.setEnabled(False)

    def _confirm(self):
        self.done(QDialog.Accepted)

    def _skip(self):
        self.captured_key = None
        self.done(QDialog.Accepted)  # Accepted but captured_key stays None

    def _cancel(self):
        self.captured_key = None
        self.done(QDialog.Rejected)

    @staticmethod
    def _qt_key_to_name(key: int, modifiers) -> str | None:
        """Map Qt key codes to your SCANCODES key name format."""
        _MAP = {
            Qt.Key_Escape: "ESC",
            Qt.Key_Tab: "TAB",
            Qt.Key_Return: "ENTER",
            # Shift/Ctrl/Alt intentionally omitted — handled by scancode path above
            Qt.Key_Space: "SPACE",
            Qt.Key_CapsLock: "CAPSLOCK",
            Qt.Key_F1: "F1", Qt.Key_F2: "F2", Qt.Key_F3: "F3",
            Qt.Key_F4: "F4", Qt.Key_F5: "F5", Qt.Key_F6: "F6",
            Qt.Key_F7: "F7", Qt.Key_F8: "F8", Qt.Key_F9: "F9",
            Qt.Key_F10: "F10", Qt.Key_F11: "F11", Qt.Key_F12: "F12",
            Qt.Key_BracketLeft: "LEFT_BRACKET",
            Qt.Key_BracketRight: "RIGHT_BRACKET",
            Qt.Key_Backspace: "BACKSPACE",
            Qt.Key_Insert: "E0_INSERT",
            Qt.Key_Delete: "E0_DELETE",
            Qt.Key_Home: "E0_HOME",
            Qt.Key_End: "E0_END",
            Qt.Key_PageUp: "E0_PAGEUP",
            Qt.Key_PageDown: "E0_PAGEDOWN",
            Qt.Key_Left: "E0_LEFT",
            Qt.Key_Right: "E0_RIGHT",
            Qt.Key_Up: "E0_UP",
            Qt.Key_Down: "E0_DOWN",
        }

        if key in _MAP:
            return _MAP[key]

        # Single printable ASCII (a-z, 0-9, etc.)
        if 32 <= key <= 126:
            return chr(key).lower()

        return None  # Ignore unknown keys (mouse buttons, media keys, etc.)


def capture_keys(preset_name: str | None = None) -> tuple[str | None, str | None] | None:
    from mapper_module.utils import PRESETS, get_keys_from_toml, update_toml_keys

    preset = PRESETS.get(preset_name, {}) if preset_name else {}
    last_toggle, last_sprint = get_keys_from_toml()

    default_toggle = last_toggle or preset.get("toggle_key")
    default_sprint = last_sprint or preset.get("sprint_key")

    toggle_dialog = KeyCaptureDialog(
        "Press the key to toggle between MOUSE MODE and CURSOR MODE.",
        skippable=False,
        default_key=default_toggle,
    )
    if toggle_dialog.exec_() == QDialog.Rejected:
        return None
    toggle_key = toggle_dialog.captured_key
    if toggle_key is None:
        return None

    sprint_dialog = KeyCaptureDialog(
        "Press the key to use as the SPRINT key\n(or click Skip if not needed)",
        skippable=True,
        default_key=default_sprint,
    )
    if sprint_dialog.exec_() == QDialog.Rejected:
        return None
    sprint_key = sprint_dialog.captured_key

    update_toml_keys(toggle_key, sprint_key)
    return toggle_key, sprint_key