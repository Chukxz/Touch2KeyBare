import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLabel
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from mapper_module.platform import get_platform
from mapper_module.utils import MIN_STR_LEN, WINDOWS_HEADERS, COL_WIDTHS


class ListApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Target Window")
        self.selected_window_id = None  # None = no confirmed selection

        self.v_layout = QVBoxLayout()

        # Monospace label as header (immune to list reordering)
        self.header_label = QLabel(self._format_row(WINDOWS_HEADERS))
        self.header_label.setFont(QFont("Courier", 9))
        self.v_layout.addWidget(self.header_label)

        self.list_widget = QListWidget()
        self.list_widget.setFont(QFont("Courier", 9))
        self.v_layout.addWidget(self.list_widget)

        self.enter_btn = QPushButton("Confirm Selection")
        self.enter_btn.clicked.connect(self._handle_enter)
        self.v_layout.addWidget(self.enter_btn)

        self.setLayout(self.v_layout)
        self.resize(900, 500)

        # State
        self.windows_id_mapping: dict[int, int] = {}  # window_id -> list row index
        self.main_store: set[int] = set()
        self.tmp_store: set[int] = set()
        self.windows_data: dict[int, list] = {}

        _, WindowMgrClass, _, _ = get_platform()
        self.window_manager = WindowMgrClass()

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_list)
        self.timer.start(1000)


    # Data layer
    def _get_windows_data(self):
        titles = self.window_manager.find_visible_window_titles()
        self.windows_data.clear()
        self.tmp_store.clear()

        for window_id, title in titles.items():
            left, top = self.window_manager.get_window_position(window_id)
            width, height = self.window_manager.get_window_dimensions(window_id)

            # Skip zero-dimension windows — they'd cause ZeroDivisionError in mapper
            if width == 0 or height == 0:
                continue

            class_name = self.window_manager.get_window_class_name(window_id)
            self.tmp_store.add(window_id)
            self.windows_data[window_id] = [
                window_id, title, class_name, left, top, width, height
            ]

        added = self.tmp_store - self.main_store
        removed = self.main_store - self.tmp_store

        self.main_store.clear()
        self.main_store.update(self.tmp_store)

        return (
            [wid for wid in added],
            [wid for wid in removed],
        )


    # UI update
    def _update_list(self):
        added_ids, removed_ids = self._get_windows_data()

        for window_id in removed_ids:
            deletion_index = self.windows_id_mapping.pop(window_id, None)
            if deletion_index is None:
                continue

            item = self.list_widget.takeItem(deletion_index)
            del item

            # Shift all indices that were after the deleted row
            for wid, idx in self.windows_id_mapping.items():
                if idx > deletion_index:
                    self.windows_id_mapping[wid] = idx - 1

        for window_id in added_ids:
            row = self.list_widget.count()
            data = self.windows_data[window_id]
            item = QListWidgetItem(self._format_row(data))
            # Store the window_id in the item so selection doesn't need the mapping
            item.setData(Qt.UserRole, window_id)
            self.list_widget.addItem(item)
            self.windows_id_mapping[window_id] = row

    
    # Formatting
    def _format_row(self, data: list) -> str:
        return "".join(
            self._pad(str(data[i]), _COL_WIDTHS[i]) for i in range(len(COL_WIDTHS))
        )

    @staticmethod
    def _pad(s: str, width: int) -> str:
        width = max(MIN_STR_LEN, width)
        if len(s) > width:
            return s[: width - 3] + "..."
        return s.ljust(width)


    # Confirm / close
    def _handle_enter(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        self.selected_window_id = item.data(Qt.UserRole)
        self.timer.stop()
        self.close()

    def closeEvent(self, event):
        # Covers both the X button and programmatic close()
        self.timer.stop()
        super().closeEvent(event)


def select_window() -> int | None:
    """
    Opens the window selector. Returns the selected window_id on confirm,
    or None if the user closed the dialog without confirming.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    dialog = ListApp()
    dialog.show()
    app.exec_()
    return dialog.selected_window_id