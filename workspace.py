import os.path

import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from support import (EntryLine, EntryLinePostfix, IntValid,
                     GraphicLine, GraphicPoint, AddGraphicLine, AddGraphicPoint, Utils)
from lucas_kanade import LucasKanade


class DialogProgress(QDialog):
    def __init__(self, parent: QObject = None):
        super().__init__(parent)

        layout = QVBoxLayout()
        layout.setContentsMargins(25, 10, 25, 10)
        bar = QProgressBar()
        bar.setFixedWidth(260)

        layout_buttons = QHBoxLayout()
        layout_buttons.addStretch(False)

        accept = QPushButton("OK", clicked=self.accept)
        accept.setObjectName("accept")
        reject = QPushButton("Cancel", clicked=self.reject)
        reject.setObjectName("reject")

        layout_buttons.addWidget(accept, alignment=Qt.AlignRight)
        layout_buttons.addWidget(reject, alignment=Qt.AlignRight)

        layout.addSpacing(10)
        layout.addWidget(bar)
        layout.addSpacing(10)
        layout.addLayout(layout_buttons)

        self.setObjectName("save_dialog")
        self.setLayout(layout)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowTitle("Wait")
        self.setFixedSize(self.sizeHint())


class SaveContoursFrames(QThread):
    progress = pyqtSignal(int)

    def __init__(self, data: dict, parent: QObject):
        super().__init__(parent)

        self.data = data
        self.stop = True
        self.finished.connect(lambda: setattr(self, "stop", True))

    def begin(self, types: list, path: str) -> None:
        self.types = types
        self.path = path
        self.stop = False
        self.start()

    def run(self) -> None:
        from PIL import Image, ImageDraw

        for n, frame in enumerate(self.data.get("frames")):

            if self.stop:
                break

            frame = Image.open(frame)
            draw = ImageDraw.Draw(frame)
            for type in self.types:
                fill = (255, 0, 0) if type == "endo" else (255, 255, 0)
                contour = self.data["ready_contours"][type][n]
                for p in range(len(contour) - 1):
                    start = (contour[p].x(), contour[p].y())
                    end = (contour[p + 1].x(), contour[p + 1].y())
                    draw.line((start, end), fill=fill, width=1)
            name = os.path.join(self.path, f"{n}.png")
            frame.save(name)
            self.progress.emit(n)

        del self.types
        del self.path


class Menu(QGroupBox):
    def _setUI(self, dir_name: str, parent: QWidget) -> None:
        self.setObjectName("menu")

        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignLeft)
        layout.setContentsMargins(10, 0, 0, 0)

        title_file = EntryLine()
        title_file.setObjectName("title_file")
        title_file.setPlaceholderText("File name")
        title_file.setText(dir_name)
        title_file.setFixedWidth(200)

        save_imgs = QPushButton()
        save_imgs.setObjectName("save_imgs")
        save_imgs.setIcon(QIcon("static/images/save_imgs_arrow.png"))
        save_imgs.setIconSize(QSize(35, 35))
        save_imgs.setCursor(Qt.PointingHandCursor)

        type_imgs = QMenu(parent)
        save_imgs.clicked.connect(
            lambda: (type_imgs.move(self.mapToGlobal(save_imgs.pos() + QPoint(0, 25))), type_imgs.show()))

        endo_exist = self.data.get("ready_contours").get("endo") is not None
        epi_exist = self.data.get("ready_contours").get("epi") is not None

        if endo_exist and epi_exist:
            endo_action = QAction("Endo", type_imgs)
            endo_action.triggered.connect(self.save_endo_imgs)
            epi_action = QAction("Epi", type_imgs)
            epi_action.triggered.connect(self.save_epi_imgs)
            all_action = QAction("All", type_imgs)
            all_action.triggered.connect(self.save_both_imgs)
            type_imgs.addActions((endo_action, epi_action, all_action))
        elif endo_exist:
            endo_action = QAction("Endo", type_imgs)
            endo_action.triggered.connect(self.save_endo_imgs)
            type_imgs.addAction(endo_action)
        elif epi_exist:
            epi_action = QAction("Epi", type_imgs)
            epi_action.triggered.connect(self.save_epi_imgs)
            type_imgs.addAction(epi_action)

        save_data = QPushButton()
        save_data.setObjectName("save_data")
        save_data.setIcon(QIcon("static/images/save_data.png"))
        save_data.setIconSize(QSize(20, 20))
        save_data.setCursor(Qt.PointingHandCursor)
        save_data.setToolTip("Save data")
        save_data.clicked.connect(self.save_data)

        type_points = QComboBox()
        type_points.setObjectName("type_points")
        type_points_list = QListView()
        type_points_list.setObjectName("type_points_list")
        type_points.setView(type_points_list)
        type_points.addItems(["Integer", "Float"])

        entry_float_values = EntryLine()
        entry_float_values.setObjectName("entry_float_values")
        entry_float_values.setText("3")
        entry_float_values.setValidator(QIntValidator())
        entry_float_values.setAlignment(Qt.AlignCenter)
        entry_float_values.setFixedWidth(40)
        entry_float_values.setMaxLength(2)
        entry_float_values.hide()

        type_points.currentTextChanged.connect(
            lambda type: entry_float_values.show() if type == "Float" else entry_float_values.hide())

        layout.addWidget(save_imgs)
        layout.addWidget(save_data)
        layout.addWidget(title_file, alignment=Qt.AlignLeft)
        layout.addWidget(type_points)
        layout.addWidget(entry_float_values, alignment=Qt.AlignLeft)

        self.setLayout(layout)

    def __init__(self, data: dict, parent: QWidget):
        super().__init__()

        self.data = data
        self.saveContoursFrames = SaveContoursFrames(self.data, self)
        self.progess = DialogProgress(self)
        save_bar: QProgressBar = self.progess.findChild(QProgressBar)
        self.progess.rejected.connect(lambda: setattr(self.saveContoursFrames, "stop", True))
        self.saveContoursFrames.finished.connect(
            lambda: self.progess.findChild(QPushButton, "accept").setEnabled(True))
        self.saveContoursFrames.progress.connect(
            lambda value: save_bar.setValue(value))
        self.dir = os.path.dirname(data.get("frames")[0])

        self._setUI(os.path.basename(self.dir), parent)

    def save_data(self) -> None:

        title_file = f"{self.findChild(EntryLine, 'title_file').text().strip()}"

        if not title_file:
            msg = QMessageBox()
            msg.setText("File name is empty")
            return msg.exec_()

        path = os.path.join(self.dir, title_file)

        endo_exist = self.data.get("ready_contours").get("endo") is not None
        epi_exist = self.data.get("ready_contours").get("epi") is not None
        endo_file_exist = os.path.exists(f"{path}_endo.txt")
        epi_file_exist = os.path.exists(f"{path}_epi.txt")

        quest = QMessageBox()
        quest.setWindowTitle("Overwrite")
        quest.addButton(QMessageBox.Ok)
        quest.addButton(QMessageBox.Cancel)

        msg = QMessageBox()
        msg.setWindowTitle("Saved")
        msg.setText("Data saved successfully")

        if endo_exist and epi_exist and (endo_file_exist or epi_file_exist):
            quest.setText("Files already exist. Overwrite?")
            if quest.exec_() == QMessageBox.Ok:
                self.file_data(path)
                msg.exec_()
        elif endo_exist and endo_file_exist:
            quest.setText("Endo file already exist. Overwrite?")
            if quest.exec_() == QMessageBox.Ok:
                self.file_data(path)
                msg.exec_()
        elif epi_exist and epi_file_exist:
            quest.setText("Epi file already exist. Overwrite?")
            if quest.exec_() == QMessageBox.Ok:
                self.file_data(path)
                msg.exec_()
        else:
            self.file_data(path)
            msg.exec_()

    def save_endo_imgs(self) -> None:
        self.save_imgs(["endo"])

    def save_epi_imgs(self) -> None:
        self.save_imgs(["epi"])

    def save_both_imgs(self) -> None:
        self.save_imgs(["endo", "epi"])

    def save_imgs(self, types: list) -> None:

        title_file = f"{self.findChild(EntryLine, 'title_file').text().strip()}"

        if not title_file:
            msg = QMessageBox()
            msg.setText("File name is empty")
            return msg.exec_()

        from shutil import rmtree

        title_file += f"_{types[0]}" if len(types) < 2 else f"_both"
        path = os.path.join(self.dir, title_file)

        if os.path.exists(path) and os.path.isdir(path):
            try:
                rmtree(path)
            except OSError:
                print("Dir wasn't deleted")

        while os.path.exists(path):
            pass

        os.mkdir(path)

        if "endo" in types and "epi" in types:
            self.progess.setWindowTitle("Endo/epi saving")
        elif "endo":
            self.progess.setWindowTitle("Endo saving")
        elif "epi":
            self.progess.setWindowTitle("Epi saving")

        save_bar: QProgressBar = self.progess.findChild(QProgressBar)
        save_bar.setRange(0, len(self.data["frames"]) - 1)
        save_bar.reset()
        accept = self.progess.findChild(QPushButton, "accept")
        accept.setEnabled(False)
        self.saveContoursFrames.begin(types, path)
        self.progess.clearFocus()
        self.progess.exec_()


    def file_data(self, path: str) -> None:

        type_points: QComboBox = self.findChild(QComboBox)
        entry_float_values: EntryLine = self.findChild(EntryLine, "entry_float_values")
        ft = entry_float_values.text() if type_points.currentText() == "Float" else 0

        for walltype, contours in self.data.get("ready_contours").items():
            with open(f"{path}_{walltype}.txt", "w") as file:
                try:
                    sys_id = self.data['sys_id']
                except AttributeError:
                    sys_id = -1
                try:
                    y0, x0 = self.data['scale_start'].y(), self.data['scale_start'].x()
                except AttributeError:
                    y0, x0 = -1, -1

                try:
                    y1, x1 = self.data['scale_end'].y(), self.data['scale_end'].x()
                except AttributeError:
                    y1, x1 = -1, -1

                file.write(f"{sys_id} {y0} {x0} {y1} {x1}\n")
                for contour in contours:
                    points = list(map(lambda p: "".join(f"{p.y():.{ft}f} {p.x():.{ft}f} "), contour))
                    points[-1] = f"{points[-1].rstrip()}\n"
                    file.writelines(points)


class WallTypes(QGroupBox):
    ENDO = 1
    EPI = 2
    BOTH = 3
    turned = pyqtSignal(int)
    double_contour = pyqtSignal(int)

    def _setUI(self, type: int) -> None:

        self.setObjectName("walltypes")
        layout = QHBoxLayout()

        binding = QIcon("static/images/binding.png")
        binding_enable = QIcon("static/images/binding_enable2.png")

        if WallTypes.BOTH == type:
            group = QButtonGroup(self)
            connect = QPushButton()
            connect.setObjectName("connect_button")
            connect.setCheckable(True)
            connect.setIcon(QIcon("static/images/binding.png"))
            connect.setChecked(False)
            connect.setCursor(Qt.PointingHandCursor)
            connect.setIconSize(QSize(48, 48))
            connect.toggled.connect(
                lambda enable: (connect.setIcon(binding_enable),
                                self.double_contour.emit(True)) if enable else (connect.setIcon(binding),
                                                                                self.double_contour.emit(False)))

        if WallTypes.ENDO == type or WallTypes.BOTH == type:
            endo = QPushButton("ENDO")
            endo.setObjectName("endo")
            endo.setCursor(Qt.PointingHandCursor)
            endo.setCheckable(True)
            endo.setChecked(True)
            endo.clicked.connect(lambda: self.turned.emit(WallTypes.ENDO))
            layout.addWidget(endo)
            if WallTypes.ENDO == type:
                endo.setEnabled(False)
            else:
                group.addButton(endo)
                layout.addWidget(connect)

        if WallTypes.EPI == type or WallTypes.BOTH == type:
            epi = QPushButton("EPI")
            epi.setObjectName("epi")
            epi.setCursor(Qt.PointingHandCursor)
            epi.setCheckable(True)
            epi.clicked.connect(lambda: self.turned.emit(WallTypes.EPI))
            layout.addWidget(epi)
            if WallTypes.EPI == type:
                epi.setChecked(True)
                epi.setEnabled(False)
            else:
                group.addButton(epi)

        self.setLayout(layout)

    def __init__(self, type: int):
        super().__init__()

        self._setUI(type)
        self.type = type


class Picture(QGraphicsView):

    def __init__(self, background: str = None):
        super().__init__()

        self.setScene(QGraphicsScene())
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameStyle(False)

        pixmap = QPixmap(background)
        graphic_pixmap = QGraphicsPixmapItem(pixmap)

        self.scale_value = Utils.get_scale_value(pixmap.size() + QSize(0, 350))
        self.scale(self.scale_value, self.scale_value)
        self.scale_counter = 0

        self.scene().addItem(graphic_pixmap)

    def sizeHint(self) -> QSize:
        from math import ceil
        size = self.scene().items(order=Qt.AscendingOrder)[0].pixmap().size()
        width = ceil(size.width() * self.scale_value)
        height = ceil(size.height() * self.scale_value)
        return QSize(width, height)

    def set_radius_slider(self, slider: QSlider) -> None:
        self._radius = slider
        self._radius.valueChanged.connect(self.change_radius)

    def set_picture(self, background: str, points: list, add_points: list = None, visible: bool = False) -> None:

        self.scene().clear()
        self.scene().addPixmap(QPixmap(background))

        r = self._radius.value() / 10
        w = r / 4

        add_graphic_lines = [GraphicLine(points[n], points[n + 1], w) for n in range(len(points) - 1)]
        add_graphic_points = [GraphicPoint(point, r) for point in points]
        add_graphic_points[0].set_lines(out_=add_graphic_lines[0])
        add_graphic_points[-1].set_lines(in_=add_graphic_lines[-1])
        for n, _ in enumerate(add_middle_points:=add_graphic_points[1:-1]):
            add_middle_points[n].set_lines(in_=add_graphic_lines[n], out_=add_graphic_lines[n + 1])
        for line in add_graphic_lines:
            self.scene().addItem(line)
        for point in add_graphic_points:
            self.scene().addItem(point)

        if add_points is None:
            return

        add_graphic_lines = [AddGraphicLine(add_points[n], add_points[n + 1], w) for n in range(len(add_points) - 1)]
        add_graphic_points = [AddGraphicPoint(point, r) for point in add_points]

        if not visible:
            for n, _ in enumerate(add_graphic_lines):
                add_graphic_lines[n].hide()
                add_graphic_points[n].hide()
            add_graphic_points[-1].hide()

        add_graphic_points[0].set_lines(out_=add_graphic_lines[0])
        add_graphic_points[-1].set_lines(in_=add_graphic_lines[-1])
        for n, _ in enumerate(add_middle_points := add_graphic_points[1:-1]):
            add_middle_points[n].set_lines(in_=add_graphic_lines[n], out_=add_graphic_lines[n + 1])
        for line in add_graphic_lines:
            self.scene().addItem(line)
        for point in add_graphic_points:
            self.scene().addItem(point)

    def show_add_contour(self) -> None:
        items = self.scene().items()
        for item in items:
            if isinstance(item, (AddGraphicPoint, AddGraphicLine)):
                item.hide() if item.isVisible() else item.show()

    def change_radius(self, r: float) -> None:
        items = self.scene().items()
        r /= 10
        for item in items:
            if isinstance(item, (AddGraphicPoint, GraphicPoint)):
                item.set_radius(r)
            if isinstance(item, (AddGraphicLine, GraphicLine)):
                item.set_width(r / 4)

    def scroll(self, pos: QPoint) -> None:
        offset = self.prev_pos - pos
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() + offset.y())
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + offset.x())
        self.prev_pos = pos

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()

        if event.modifiers() & Qt.AltModifier:
            return

        if event.modifiers() & Qt.ShiftModifier:
            return

        if event.modifiers() & Qt.ControlModifier:
            value = 3 if delta > 0 else -3
            self._radius.setValue(self._radius.value() + value)
            self.change_radius(self._radius.value())
            return

        if delta < 0 and self.scale_counter == 0:
            return

        if delta > 0 and self.scale_counter == 20:
            return

        if delta > 0:
            self.scale_counter += 1
            self.scale(1.25, 1.25)
        else:
            self.scale_counter -= 1
            self.scale(1 / 1.25, 1 / 1.25)

    def mousePressEvent(self, event: QMouseEvent) -> None:

        if event.buttons() & Qt.RightButton:
            self.prev_pos = event.pos()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:

        if event.buttons() & Qt.RightButton:
            self.scroll(event.pos())

        super().mouseMoveEvent(event)


class ActionBar(QGroupBox):
    turned = pyqtSignal(tuple)

    def _setUI(self, amount_pages: int) -> None:
        self.setObjectName("action_bar")

        layout = QHBoxLayout()

        radius = QPushButton()
        radius.setObjectName("radius")
        radius.setCheckable(True)
        radius.setIcon(QIcon("static/images/radius.png"))
        radius.setIconSize(QSize(24, 24))
        radius.setCursor(Qt.PointingHandCursor)

        left = QPushButton()
        left.setObjectName("left")
        left.setIcon(QIcon("static/images/left.png"))
        left.setIconSize(QSize(22, 22))
        left.setCursor(Qt.PointingHandCursor)
        left.clicked.connect(self.previous)

        pages = EntryLinePostfix(f" / {amount_pages}", "1")
        pages.setObjectName("pages")
        pages.setAlignment(Qt.AlignCenter)
        pages.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        pages.setMaxLength(len(str(amount_pages)))
        pages.setValidator(IntValid())
        pages.textChanged.connect(self.set_page)

        right = QPushButton()
        right.setObjectName("right")
        right.setIcon(QIcon("static/images/right.png"))
        right.setIconSize(QSize(22, 22))
        right.setCursor(Qt.PointingHandCursor)
        right.clicked.connect(self.next)

        reload = QPushButton()
        reload.setObjectName("reload")
        reload.setIcon(QIcon("static/images/reload.png"))
        reload.setIconSize(QSize(18, 18))
        reload.setCursor(Qt.PointingHandCursor)

        layout.addWidget(radius)
        layout.addSpacing(20)
        layout.addWidget(left)
        layout.addWidget(pages)
        layout.addWidget(right)
        layout.addSpacing(20)
        layout.addWidget(reload)

        self.setLayout(layout)

    def __init__(self, amount_pages: int):
        super().__init__()

        self._setUI(amount_pages)

        self.amount_pages = amount_pages
        self.current_type = None
        self.current_page = {WallTypes.ENDO: 1, WallTypes.EPI: 1}

        self._radius_slider = None
        self._space = None

    def set_radius_slider(self, radius_slider: QSlider, space: int) -> None:
        self._radius_slider = radius_slider
        self._space = space
        self._radius_slider.hide()
        radius = self.findChild(QPushButton, "radius")
        radius.toggled.connect(
            lambda enable: self._radius_slider.show() if enable else self._radius_slider.hide())

    def radius_slider_move(self, pos: QPoint) -> None:
        if self._radius_slider is None:
            return

        radius = self.findChild(QPushButton, "radius")
        x = radius.x() + pos.x()
        y = pos.y() - self._radius_slider.height() - self._space
        self._radius_slider.move(x, y)

    def change_type_pages(self, type: int) -> None:
        pages: EntryLinePostfix = self.findChild(EntryLinePostfix, "pages")
        self.current_type = type
        pages.setText(str(self.current_page[type]))
        self.turned.emit((type, self.current_page[type]))

    def set_page(self, text: str) -> None:
        if 0 < int(text) <= self.amount_pages:
            self.current_page[self.current_type] = int(text)
            self.turned.emit((self.current_type, self.current_page[self.current_type]))

    def next(self) -> None:
        pages: EntryLinePostfix = self.findChild(EntryLinePostfix, "pages")
        right: QPushButton = self.findChild(QPushButton, "right")
        if self.current_page[self.current_type] < self.amount_pages:
            self.current_page[self.current_type] += 1
        elif self.current_page[self.current_type] == self.amount_pages:
            self.current_page[self.current_type] = 1
        pages.setText(str(self.current_page[self.current_type]))
        self.turned.emit((self.current_type, self.current_page[self.current_type]))

    def previous(self) -> None:
        pages: EntryLinePostfix = self.findChild(EntryLinePostfix, "pages")
        left: QPushButton = self.findChild(QPushButton, "left")
        if self.current_page[self.current_type] > 1:
            self.current_page[self.current_type] -= 1
        elif self.current_page[self.current_type] == 1:
            self.current_page[self.current_type] = self.amount_pages
        pages.setText(str(self.current_page[self.current_type]))
        self.turned.emit((self.current_type, self.current_page[self.current_type]))

    def moveEvent(self, event: QMoveEvent) -> None:
        self.radius_slider_move(event.pos())
        super().moveEvent(event)


class Gallery(QWidget):
    reload = pyqtSignal(dict)

    def _setUI(self, data: dict) -> None:
        self.setObjectName("gallery")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(10)

        menu = Menu(data, self)

        endo = data.get("ready_contours").get("endo")
        epi = data.get("ready_contours").get("epi")

        action_bar = ActionBar(len(data.get("frames")))
        reload = action_bar.findChild(QPushButton, "reload")
        reload.clicked.connect(self.get_current_contour)

        if endo is not None and epi is not None:
            walltypes = WallTypes(WallTypes.BOTH)
            action_bar.change_type_pages(WallTypes.ENDO)
        elif endo is not None:
            walltypes = WallTypes(WallTypes.ENDO)
            action_bar.change_type_pages(WallTypes.ENDO)
        elif epi is not None:
            walltypes = WallTypes(WallTypes.EPI)
            action_bar.change_type_pages(WallTypes.EPI)

        picture = Picture(data.get("frames")[0])

        walltypes.turned.connect(action_bar.change_type_pages)
        connect_button = walltypes.findChild(QPushButton, "connect_button")
        if connect_button is not None:
            connect_button.toggled.connect(picture.show_add_contour)

        layout.addWidget(menu)
        layout.addWidget(walltypes, alignment=Qt.AlignCenter)
        layout.addWidget(picture)
        layout.addWidget(action_bar, alignment=Qt.AlignCenter)

        self.setLayout(layout)

        radius_slider = QSlider(Qt.Vertical, self)
        radius_slider.setMinimum(5)
        radius_slider.setValue(30)
        radius_slider.setFixedSize(36, 150)
        action_bar.set_radius_slider(radius_slider, 10)
        picture.set_radius_slider(radius_slider)

    def __init__(self, data: dict):
        super().__init__()

        self._setUI(data)
        self.data = data

    def get_current_contour(self) -> None:
        action_bar: ActionBar = self.findChild(ActionBar)
        type, page = action_bar.current_type, action_bar.current_page[action_bar.current_type]
        data = {"frames": self.data.get("frames")[page - 1:], "ready_contours": {}}
        if type == WallTypes.ENDO:
            data["ready_contours"]["endo"] = self.data.get("ready_contours").get("endo")[page - 1]
        elif type == WallTypes.EPI:
            data["ready_contours"]["epi"] = self.data.get("ready_contours").get("epi")[page - 1]
        self.reload.emit(data)

    def page_turning(self, page: tuple) -> None:
        walltype, number = page
        number -= 1

        walltypes: WallTypes = self.findChild(WallTypes)
        picture: Picture = self.findChild(Picture)
        frame = self.data.get("frames")[number]
        contours = self.data.get("ready_contours")

        if walltypes.type == WallTypes.BOTH:
            is_double = walltypes.findChild(QPushButton, "connect_button").isChecked()
            endo = contours.get("endo")[number]
            epi = contours.get("epi")[number]
            if walltype == WallTypes.ENDO:
                picture.set_picture(frame, endo, epi, is_double)
            elif walltype == WallTypes.EPI:
                picture.set_picture(frame, epi, endo, is_double)
        else:
            if walltype == WallTypes.ENDO:
                endo = contours.get("endo")[number]
                picture.set_picture(frame, endo)
            elif walltype == WallTypes.EPI:
                epi = contours.get("epi")[number]
                picture.set_picture(frame, epi)

    def showEvent(self, event: QShowEvent):
        action_bar: ActionBar = self.findChild(ActionBar)
        type = action_bar.current_type
        page = action_bar.current_page[type]
        self.page_turning((type, page))
        if not action_bar.receivers(action_bar.turned):
            action_bar.turned.connect(self.page_turning)
        super().showEvent(event)


class Wait(QWidget):
    def _setUI(self) -> None:

        self.setObjectName("wait")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        movie = QMovie("static/images/wait.gif")
        movie.setSpeed(150)
        movie.start()

        gif = QLabel()
        gif.setObjectName("gif")
        gif.setMovie(movie)
        gif.setAlignment(Qt.AlignCenter)

        caption = QLabel("Image processing... Please wait")
        caption.setObjectName("caption")
        caption.setAlignment(Qt.AlignCenter)

        layout.addWidget(gif)
        layout.addWidget(caption)

        self.setLayout(layout)

    def __init__(self):
        super().__init__()

        self._setUI()


class Workspace(QStackedWidget):
    def _setUI(self, data: dict) -> None:
        self.setObjectName("workspace")

        with open("static/styles/gallery.css", "r") as style:
            self.setStyleSheet(style.read())

        wait = Wait()
        gallery = Gallery(data)
        gallery.reload.connect(self.segmentation)

        self.addWidget(wait)
        self.addWidget(gallery)

        Utils.move_center_hint(self)

    def __init__(self, data: dict = None):
        super().__init__()

        dir = os.path.basename(os.path.dirname(data.get("frames")[0]))
        self.setWindowTitle(dir)

        self._setUI(data)

        self.lucas_kanade = LucasKanade(data.get("amount_points"), self)
        self.lucas_kanade.released.connect(self.init_gallery)

        self.segmentation(data)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.showMaximized()

    def init_gallery(self, contours: dict) -> None:
        gallery: Gallery = self.widget(1)

        if contours.get("scale_start") and contours.get("scale_end"):
            gallery.data["scale_start"] = contours.get("scale_start")
            gallery.data["scale_end"] = contours.get("scale_end")
        try:
            del contours["scale_start"]
            del contours["scale_end"]
        except KeyError:
            pass
        try:
            del gallery.data["amount_points"]
        except KeyError:
            pass
        try:
            del gallery.data["ready_images"]
        except KeyError:
            pass
        try:
            del gallery.data["step_processing"]
        except KeyError:
            pass

        gallery.data["ready_contours"] = contours
        self.lucas_kanade.released.disconnect()
        self.lucas_kanade.released.connect(self.update_gallery)
        self.setCurrentIndex(1)

    def update_gallery(self, contours: dict) -> None:
        gallery: Gallery = self.widget(1)
        action_bar = gallery.findChild(ActionBar)
        page = action_bar.current_page[action_bar.current_type]
        for wall, values in contours.items():
            gallery.data["ready_contours"][wall][page - 1:] = values
        self.setCurrentIndex(1)

    def segmentation(self, data: dict) -> None:
        self.setCurrentIndex(0)
        frames = data.get("frames")
        ready_contours = data.get("ready_contours")
        self.lucas_kanade.begin(ready_contours, frames)