import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QListWidget, QPushButton
from PyQt5.QtCore import QTimer
from mapper_module.platform import get_platform
from mapper_module.utils import MIN_STR_LEN, WINDOWS_HEADERS


class ListApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dynamic List Selector")
        self.v_layout = QVBoxLayout()

        self.list_widget = QListWidget()
        self.v_layout.addWidget(self.list_widget)

        self.enter_btn = QPushButton("Enter (Confirm Selection)")
        self.enter_btn.clicked.connect(self.handle_enter)
        self.v_layout.addWidget(self.enter_btn)

        self.setLayout(self.v_layout)

        self.windows_id_mapping = {}
        self.main_store = set()
        self.tmp_store = set()
        self.added_window_ids = []
        self.removed_window_ids = []
        self.windows_data = {}
        _, WindowMgrClass, _, _ = get_platform()
        self.window_manager = WindowMgrClass()

        # Setup Timer for polling (1000ms = 1s)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_list)
        self.timer.start(1000)

        header_data = self.format_windows_data_item(WINDOWS_HEADERS)
        self.list_widget.addItem(header_data)

    def update_list(self):

        self.get_windows_data()
        n = len(self.list_widget)
        adds = 0

        for window_id in self.removed_window_ids:
            deletion_index = self.windows_id_mapping.pop(window_id, None)
            if deletion_index == None:
                continue

            taken_item = self.list_widget.takeItem(deletion_index)
            del taken_item

            for window_id in self.windows_data:
                index = self.windows_id_mapping.get(window_id, None)

                if index is None:
                    continue

                if index > deletion_index:
                    self.windows_id_mapping[window_id] = index - 1

            n -= 1

        for window_id in self.added_window_ids:
            data = self.format_windows_data_item(self.windows_data[window_id])
            self.list_widget.addItem(data)

            self.windows_id_mapping[window_id] = n + adds
            adds += 1

    def handle_enter(self):
        selected = self.list_widget.currentItem()
        if selected:
            print(f"User confirmed: {selected.text()}")

    def get_windows_data(self):
        titles = self.window_manager.find_visible_window_titles()
        self.windows_data.clear()

        for window_id in titles:
            title = titles[window_id]
            class_name = self.window_manager.get_window_class_name(window_id)
            self.tmp_store.add(window_id)
            left, top = self.window_manager.get_window_position(window_id)
            width, height = self.window_manager.get_window_dimensions(window_id)

            self.windows_data[window_id] = [
                window_id,
                title,
                class_name,
                left,
                top,
                width,
                height,
            ]

        added = self.tmp_store - self.main_store
        removed = self.main_store - self.tmp_store
        self.added_window_ids = [window_id for window_id in added]
        self.removed_window_ids = [window_id for window_id in removed]

        self.main_store.clear()
        self.main_store.update(self.tmp_store)
        self.tmp_store.clear()

    def format_windows_data_item(self, data):
        print(data)
        data_0 = self.format_helper(data[0], 20)
        data_1 = self.format_helper(data[1], 60)
        data_2 = self.format_helper(data[2], 60)
        data_3 = self.format_helper(data[3], 10)
        data_4 = self.format_helper(data[4], 10)
        data_5 = self.format_helper(data[5], 10)
        data_6 = self.format_helper(data[6], 10)

        return f"{data_0}{data_1}{data_2}{data_3}{data_4}{data_5}{data_6}"

    def format_helper(self, subdata, _len):
        new_str_len = max(MIN_STR_LEN, _len)
        _str = str(subdata)
        str_len = len(_str)

        if str_len > new_str_len:
            _str = _str[0 : (new_str_len - 3)] + "..."
        elif str_len <= new_str_len:
            diff = new_str_len - str_len
            _str = _str + " " * diff

        return _str


def list():
    app = QApplication(sys.argv)
    window = ListApp()
    window.show()
    sys.exit(app.exec_())
