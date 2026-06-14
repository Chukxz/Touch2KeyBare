from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget,
    QListWidgetItem, QPushButton, QLabel
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from mapper_module.platform import get_platform
from mapper_module.utils import MIN_STR_LEN, WINDOWS_HEADERS, COL_WIDTHS


class ListApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Target Window")
        self.selected_window_id = None
        self.selected_window_title: str = ""

        self.v_layout = QVBoxLayout()

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

        self.windows_id_mapping: dict[int, int] = {}
        self.main_store: set[int] = set()
        self.tmp_store: set[int] = set()
        self.windows_data: dict[int, list] = {}

        _, WindowMgrClass, _, _ = get_platform()
        self.window_manager = WindowMgrClass()

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_list)
        self.timer.start(1000)

    def _get_windows_data(self):
        visible = self.window_manager.find_visible_windows()  # single pass
        self.windows_data.clear()
        self.tmp_store.clear()

        for window_id, meta in visible.items():
            left, top = self.window_manager.get_window_position(window_id)
            width, height = self.window_manager.get_window_dimensions(window_id)

            if width == 0 or height == 0:
                continue

            self.tmp_store.add(window_id)
            self.windows_data[window_id] = [
                window_id,
                meta["title"],
                meta["class_name"],
                left, top, width, height,
            ]

        added = self.tmp_store - self.main_store
        removed = self.main_store - self.tmp_store
        self.main_store.clear()
        self.main_store.update(self.tmp_store)
        return list(added), list(removed)

    def _update_list(self):
        added_ids, removed_ids = self._get_windows_data()

        for window_id in removed_ids:
            deletion_index = self.windows_id_mapping.pop(window_id, None)
            if deletion_index is None:
                continue
            item = self.list_widget.takeItem(deletion_index)
            del item
            for wid, idx in self.windows_id_mapping.items():
                if idx > deletion_index:
                    self.windows_id_mapping[wid] = idx - 1

        for window_id in added_ids:
            row = self.list_widget.count()
            data = self.windows_data[window_id]
            item = QListWidgetItem(self._format_row(data))
            item.setData(Qt.UserRole, window_id)
            item.setData(Qt.UserRole + 1, self.windows_data[window_id][1])  # title is index 1
            self.list_widget.addItem(item)
            self.windows_id_mapping[window_id] = row

    def _format_row(self, data: list) -> str:
        return "".join(
            self._pad(str(data[i]), COL_WIDTHS[i]) for i in range(len(COL_WIDTHS))
        )

    @staticmethod
    def _pad(s: str, width: int) -> str:
        width = max(MIN_STR_LEN, width)
        if len(s) > width:
            return s[:width - 3] + "..."
        return s.ljust(width)

    def _handle_enter(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        self.selected_window_id = item.data(Qt.UserRole)
        self.selected_window_title = item.data(Qt.UserRole + 1)
        self.timer.stop()
        self.close()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)


def select_window() -> tuple[int, str] | None:
    dialog = ListApp()
    dialog.show()
    QApplication.instance().exec_()
    if dialog.selected_window_id is None:
        return None
    return dialog.selected_window_id, dialog.selected_window_title