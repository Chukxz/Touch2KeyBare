from mapper_module.utils import (
    PRESETS,
    get_keys_from_toml,
    update_toml_keys,
    get_scancode_and_bridge_key_from_key,
)
from mapper_module.platform import get_specific_qt_key
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class KeyCaptureDialog(QDialog):
    def __init__(
        self, prompt: str, skippable: bool = False, default_key: str | None = None
    ):
        super().__init__()
        self.setWindowTitle("Key Capture")
        self.setFixedSize(400, 200)
        self.captured_key: str | None = None
        self.skippable = skippable
        self.default_key = default_key
        self._listening = True

        layout = QVBoxLayout()

        self.prompt_label = QLabel(prompt)
        self.prompt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prompt_label.setFont(QFont("Courier", 8))
        layout.addWidget(self.prompt_label)

        if default_key:
            self.key_label = QLabel(
                f"Waiting for keypress (Default : {default_key})..."
            )
        else:
            self.key_label = QLabel("Waiting for keypress (Default: '')...")
        self.key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key_label.setFont(QFont("Courier", 8))
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
            self.skip_btn = QPushButton("Skip")
            self.skip_btn.clicked.connect(self._skip)
            btn_layout.addWidget(self.skip_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._reset)
        btn_layout.addWidget(self.reset_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def keyPressEvent(self, event):
        if not self._listening:
            return

        precise_key = get_specific_qt_key(event)
        _, key_name = get_scancode_and_bridge_key_from_key(precise_key)

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
        self.done(QDialog.DialogCode.Accepted)

    def _skip(self):
        self.captured_key = self.default_key
        self.done(QDialog.DialogCode.Accepted)

    def _reset(self):
        self.captured_key = None
        self.done(QDialog.DialogCode.Accepted)


def capture_keys(
    preset_name: str | None = None,
) -> tuple[str | None, str | None] | None:
    preset = PRESETS.get(preset_name, {}) if preset_name else {}
    last_toggle, last_sprint = get_keys_from_toml()

    default_toggle = last_toggle or preset.get("toggle_key")
    default_sprint = last_sprint or preset.get("sprint_key")

    toggle_dialog = KeyCaptureDialog(
        "Press the key to use as the TOGGLE key\nfor Camera/Menu mode toggle\n(or click Skip to use the default)",
        skippable=True,
        default_key=default_toggle,
    )
    if toggle_dialog.exec_() == QDialog.Rejected:
        return None
    toggle_key = toggle_dialog.captured_key

    sprint_dialog = KeyCaptureDialog(
        "Press the key to use as the SPRINT key\n(or click Skip to use the default)",
        skippable=True,
        default_key=default_sprint,
    )
    if sprint_dialog.exec_() == QDialog.Rejected:
        return None
    sprint_key = sprint_dialog.captured_key

    update_toml_keys(toggle_key, sprint_key)
    return toggle_key, sprint_key
