from PyQt5.QtWidgets import (
    QListWidgetItem, QWidget, QDialog, QVBoxLayout, QLabel, QRadioButton,
    QHBoxLayout, QListWidget, QCheckBox, QDialogButtonBox, QButtonGroup,
    QMenu
)
from PyQt5.QtCore import Qt, pyqtSignal

from pathlib import Path
from typing import Union


class FileList(QListWidgetItem):
    def __init__(self, path: str):
        super().__init__()

        self._path = path
        self.setText(Path(path).stem)

    def path(self) -> str:
        return self._path


class ListContours(QWidget):
    def __init__(self, type: str):
        super().__init__()

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(5)

        title = QLabel(type.upper())
        title.setObjectName("title_list")

        list = QListWidget()
        list.setFocusPolicy(Qt.NoFocus)
        list.setFixedSize(325, 200)

        checkbox = QCheckBox(f"Draw a new {type.lower()} contour")
        checkbox.setCursor(Qt.PointingHandCursor)
        checkbox.toggled.connect(lambda enable: (title.setEnabled(not enable), list.setEnabled(not enable)))

        layout.addWidget(title, alignment=Qt.AlignCenter)
        layout.addWidget(list, alignment=Qt.AlignCenter)
        layout.addWidget(checkbox, alignment=Qt.AlignLeft)

        menu = QMenu(self)
        menu.addAction("Clear", lambda: list.setCurrentRow(-1))

        list.setContextMenuPolicy(Qt.CustomContextMenu)
        list.customContextMenuRequested.connect(lambda pos: menu.exec_(list.mapToGlobal(pos)))

        self.setLayout(layout)

    def add_files(self, files: list) -> None:
        list: QListWidget = self.findChild(QListWidget)
        for file in files:
            list.addItem(FileList(file))

    def get_current_file(self) -> Union[str, int, None]:
        checkbox: QCheckBox = self.findChild(QCheckBox)

        if checkbox.isChecked():
            return Options.NEW

        list: QListWidget = self.findChild(QListWidget)

        if list.currentItem() is not None:
            return list.currentItem().path()

        return None

    def set_current_file(self, index: int) -> None:
        list: QListWidget = self.findChild(QListWidget)
        list.setCurrentRow(index)


class Options(QDialog):

    EMPTY = 0
    NEW = 1
    IMAGES = 2
    ENDO = 3
    EPI = 4
    BOTH = 5

    def _setUI(self, data: dict) -> None:
        self.setObjectName("options")

        with open("static/styles/options.css", "r") as style:
            self.setStyleSheet(style.read())

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(50, 30, 50, 30)

        title = QLabel("Select an action")
        title.setObjectName("title")

        button_group = QButtonGroup(self)

        option_create = QRadioButton("Create a new contours")
        option_create.setObjectName("option_create")
        option_create.setCursor(Qt.PointingHandCursor)
        button_group.addButton(option_create)

        layout.addWidget(title)
        layout.addSpacing(20)
        layout.addWidget(option_create)

        if data.get("ready_images"):
            option_load_images = QRadioButton("Use drawn images")
            option_load_images.setObjectName("option_load_images")
            option_load_images.setCursor(Qt.PointingHandCursor)
            button_group.addButton(option_load_images)
            option_load_images.toggle()

            layout.addWidget(option_load_images)

        if data.get("ready_contours"):
            option_load_contours = QRadioButton("Use ready contours")
            option_load_contours.setObjectName("option_load_contours")
            option_load_contours.setCursor(Qt.PointingHandCursor)
            option_load_contours.toggle()
            option_load_contours.toggled.connect(lambda enable: (list_endo.setEnabled(enable),
                                                                 list_epi.setEnabled(enable)))
            button_group.addButton(option_load_contours)

            list_layout = QHBoxLayout()
            list_layout.setSpacing(20)

            list_endo = ListContours("endo")
            list_endo.setObjectName("list_endo")
            list_endo.add_files(data["ready_contours"]["endo"])
            list_endo.set_current_file(0)

            list_epi = ListContours("epi")
            list_epi.setObjectName("list_epi")
            list_epi.add_files(data["ready_contours"]["epi"])
            list_epi.set_current_file(0)

            list_layout.addWidget(list_endo)
            list_layout.addWidget(list_epi)

            layout.addWidget(option_load_contours)
            layout.addSpacing(20)
            layout.addLayout(list_layout)

        buttons_action = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons_action.button(QDialogButtonBox.Ok).setCursor(Qt.PointingHandCursor)
        buttons_action.button(QDialogButtonBox.Cancel).setCursor(Qt.PointingHandCursor)

        buttons_action.accepted.connect(self.accept)
        buttons_action.rejected.connect(self.reject)

        layout.addSpacing(30)
        layout.addWidget(buttons_action)

        self.setLayout(layout)

    def __init__(self, data: dict):
        super().__init__()

        self._setUI(data)

        self.setWindowTitle("Options")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setFixedSize(self.sizeHint().width(), self.sizeHint().height())

    def accept_action(self):
        group_button = self.findChild(QButtonGroup)
        active_button = group_button.checkedButton().objectName()

        if active_button == "option_create":
            self.accepted.emit("new", {})
        elif active_button == "option_load_images":
            self.accepted.emit("images", {})
        elif active_button == "option_load_contours":
            list_endo: ListContours = self.findChild(ListContours, "list_endo")
            list_epi: ListContours = self.findChild(ListContours, "list_epi")
            self.accepted.emit("contours", {"endo": list_endo.get_current_file(),
                                            "epi": list_epi.get_current_file()})

        self.accept()

    def exec_(self) -> Union[tuple, int]:
        answer = super().exec_()

        if not answer:
            return Options.EMPTY

        group_button = self.findChild(QButtonGroup)
        active_button = group_button.checkedButton().objectName()

        if active_button == "option_create":
            return Options.NEW
        elif active_button == "option_load_images":
            return Options.IMAGES
        elif active_button == "option_load_contours":
            current_endo_file = self.findChild(ListContours, "list_endo").get_current_file()
            current_epi_file = self.findChild(ListContours, "list_epi").get_current_file()
            if current_endo_file == Options.NEW and current_epi_file == Options.NEW:
                return Options.NEW
            elif current_endo_file == Options.NEW:
                return (Options.EPI, current_epi_file)
            elif current_epi_file == Options.NEW:
                return (Options.ENDO, current_endo_file)
            else:
                return (Options.BOTH, {"endo": current_endo_file, "epi": current_epi_file})
