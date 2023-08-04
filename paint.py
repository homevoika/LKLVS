from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from typing import Literal, Union
from qimage2ndarray import array2qimage, rgb_view
import numpy as np

from support import EntryLine, Utils, ToggleButton


class Instruments(QGroupBox):
    ENDO = 0
    EPI = 1

    def _setUI(self) -> None:
        self.setObjectName("instruments")

        with open("static/styles/paint.css", "r") as style:
            self.setStyleSheet(style.read())

        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

        type_brush = ToggleButton()
        type_brush.setObjectName("type_brush")
        type_brush.setText("ENDO")
        type_brush.toggled.connect(
            lambda enable: type_brush.setText("EPI") if enable else type_brush.setText("ENDO"))

        button_group = QButtonGroup(self)

        brush = ToggleButton()
        brush.setIcon(QIcon("static/images/brush.png"))
        brush.setIconSize(QSize(42, 42))
        brush.setObjectName("brush")
        brush.toggle()
        button_group.addButton(brush)

        width = EntryLine()
        width.setObjectName("width")
        width.setAlignment(Qt.AlignCenter)
        width.setValidator(QIntValidator(0, 99))
        width.setMaxLength(2)
        width.setText("1")

        eraser = ToggleButton()
        eraser.setIcon(QIcon("static/images/eraser.png"))
        eraser.setIconSize(QSize(19, 19))
        eraser.setObjectName("eraser")
        button_group.addButton(eraser)

        dot_brush = ToggleButton()
        dot_brush.setIcon(QIcon("static/images/dot_brush.png"))
        dot_brush.setIconSize(QSize(18, 18))
        dot_brush.setObjectName("dot_brush")
        button_group.addButton(dot_brush)

        accept = QPushButton()
        accept.setIcon(QIcon("static/images/accept.png"))
        accept.setIconSize(QSize(22, 22))
        accept.setObjectName("accept")
        accept.setCursor(Qt.PointingHandCursor)

        layout.addWidget(type_brush)
        layout.addWidget(brush)
        layout.addWidget(width)
        layout.addWidget(eraser)
        layout.addWidget(dot_brush)
        layout.addSpacing(15)
        layout.addWidget(accept)

        self.setLayout(layout)

    def __init__(self):
        super().__init__()

        self._setUI()


class DiscolorPixmapItem(QGraphicsPixmapItem):

    def __init__(self, background: str):
        pixels = rgb_view(QImage(background))
        r, g, b = pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2]

        red_mask = (r == 255) & (g == 0) & (b == 0)
        yellow_mask = (r == 255) & (g == 255) & (b == 0)
        purple_mask = (r == 255) & (g == 0) & (b == 255)

        pixels[red_mask] = np.array([180, 0, 0])
        pixels[yellow_mask] = np.array([180, 180, 0])
        pixels[purple_mask] = np.array([180, 0, 180])

        pixmap = QPixmap.fromImage(array2qimage(pixels))

        super().__init__(pixmap)

        self._layer = QImage(self.pixmap().size(), QImage.Format_ARGB32)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget) -> None:
        super().paint(painter, option, widget)
        painter.drawImage(self._layer.rect(), self._layer)

    def layer(self) -> QImage:
        return self._layer

    def redraw(self) -> None:
        super().setPixmap(self.pixmap())

    def merge(self) -> QImage:
        background = self.pixmap().toImage()
        painter = QPainter(background)
        painter.drawImage(background.rect(), self._layer)
        painter.end()
        return background


class Canvas(QGraphicsView):
    ERASE = 0
    LINE = 1
    POINT = 2
    RED = QColor(255, 0, 0)
    YELLOW = QColor(255, 255, 0)
    PURPLE = QColor(255, 0, 255)

    def __init__(self, background: str):
        super().__init__()

        self.setScene(QGraphicsScene())
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameStyle(False)

        graphic_pixmap = DiscolorPixmapItem(background)
        pixmap = graphic_pixmap.pixmap()

        self.scale_value = Utils.get_scale_value(pixmap.size() + QSize(0, 74))
        self.scale(self.scale_value, self.scale_value)
        self.scale_counter = 0

        self.scene().addItem(graphic_pixmap)

        self.image = rgb_view(pixmap.toImage())
        self.mode = Canvas.LINE
        self.brush = QPen()

    def sizeHint(self) -> QSize:
        size = self.image.shape
        return QSize(size[1] * self.scale_value, size[0] * self.scale_value)

    def setBrush(self, mode: int = None, width: int = None, color: Union[QColor, int] = None) -> None:
        if width is not None:
            self.brush.setWidth(width)
        if color is not None:
            self.brush.setColor(color)
        if mode is not None:
            self.mode = mode
            if mode == Canvas.LINE:
                self.brush.setCapStyle(Qt.RoundCap)
                self.brush.setJoinStyle(Qt.RoundJoin)
            else:
                self.brush.setCapStyle(Qt.SquareCap)
                self.brush.setJoinStyle(Qt.BevelJoin)
        self.set_cursor()

    def draw_point(self, pos: QPointF) -> None:
        item = self.scene().items()[0]
        layer = item.layer()
        painter = QPainter(layer)
        painter.setPen(self.brush)
        transform_pos = self.mapToScene(pos)
        if self.mode == Canvas.ERASE:
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.drawPoint(QPoint(transform_pos.x(), transform_pos.y()))
        painter.end()
        item.redraw()
        self.prev_pos = pos

    def draw_line(self, pos: QPointF) -> None:
        item = self.scene().items()[0]
        layer = item.layer()
        painter = QPainter(layer)
        painter.setPen(self.brush)
        transform_pos = self.mapToScene(pos)
        transform_prev_pos = self.mapToScene(self.prev_pos)
        if self.mode == Canvas.ERASE:
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.drawPoint(QPoint(transform_pos.x(), transform_pos.y()))
        else:
            painter.drawLine(QPoint(transform_prev_pos.x(), transform_prev_pos.y()),
                             QPoint(transform_pos.x(), transform_pos.y()))
        painter.end()
        item.redraw()
        self.prev_pos = pos

    def scroll(self, pos: QPoint) -> None:
        offset = self.prev_pos - pos
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() + offset.y())
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + offset.x())
        self.prev_pos = pos

    def draw_scale(self, pos: QPointF) -> None:
        item = self.scene().items()[0]
        pixmap = item.pixmap()
        painter = QPainter(pixmap)
        painter.setPen(self.brush)
        painter.drawPoint(pos)
        painter.end()
        item.setPixmap(pixmap)

    def draw_contour(self, points: list) -> None:
        item = self.scene().items()[0]
        pixmap = item.pixmap()

        painter = QPainter(pixmap)
        painter.setPen(self.brush)

        values = iter(points)
        begin, end = next(values), next(values)
        painter.drawLine(begin, end)

        while True:
            try:
                begin = end
                end = next(values)
                painter.drawLine(begin, end)
            except StopIteration:
                break

        painter.end()

        item.setPixmap(pixmap)

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()

        if event.modifiers() & Qt.AltModifier:
            return

        if event.modifiers() & Qt.ShiftModifier:
            return

        if event.modifiers() & Qt.AltModifier:
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

        self.set_cursor()

    def mousePressEvent(self, event: QMouseEvent) -> None:

        if event.buttons() & Qt.LeftButton:
            self.draw_point(event.pos())

        if event.buttons() & Qt.RightButton:
            self.prev_pos = event.pos()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.LeftButton and self.mode != Canvas.POINT:
            self.draw_line(event.pos())

        if event.buttons() & Qt.RightButton:
            self.scroll(event.pos())

        # if self.background_bright(event.pos()):
        #     self.cursor_brush.setColor(Qt.black)
        # else:
        #     self.cursor_brush.setColor(Qt.white)
        #
        # self.set_cursor()

        super().mouseMoveEvent(event)

    def background_bright(self, pos: QPointF) -> bool:
        transform_pos = self.mapToScene(pos)
        pos = QPoint(transform_pos.x(), transform_pos.y())

        cursor_width = int(self.cursor().pixmap().width() / self.transform().m11())
        radius = cursor_width // 2

        if not 0 <= pos.x() <= self.image.shape[1]:
            return True

        if not 0 <= pos.y() <= self.image.shape[0]:
            return True

        left_pixel, right_pixel = pos.x() - radius, pos.x() + radius + 1
        top_pixel, bottom_pixel = pos.y() - radius, pos.y() + radius + 1

        if left_pixel < 0:
            left_pixel = 0
        if right_pixel > self.image.shape[1]:
            right_pixel = self.image.shape[1]
        if top_pixel < 0:
            top_pixel = 0
        if bottom_pixel > self.image.shape[0]:
            bottom_pixel = self.image.shape[0]

        frame = self.image[top_pixel:bottom_pixel, left_pixel:right_pixel, :]
        light_pixels = np.count_nonzero(frame.sum(axis=2) / 3 > 222)
        all_pixels = frame.shape[0] * frame.shape[1]

        try:
            return light_pixels / all_pixels > 0.5
        except ZeroDivisionError:
            return True

    def set_cursor(self) -> None:

        if self.mode != Canvas.POINT:
            size = QSize(1, 1) * self.brush.width() * self.transform().m11()
        else:
            size = QSize(1, 1)

        tr_black = 170
        tr_white = 255

        if size.width() < 5:
            cursor = QPixmap(QSize(19, 19))
            cursor.fill(Qt.transparent)

            painter = QPainter(cursor)
            painter.setPen(QPen(QColor(0, 0, 0, tr_black), 1))

            radius = size.width() // 2
            dist = 5
            rect = cursor.rect()
            center = rect.center()

            painter.drawLine(rect.x(), center.y() - 1, center.x() - dist, center.y() - 1)
            painter.drawLine(rect.x(), center.y() + 1, center.x() - dist, center.y() + 1)
            painter.drawLine(center.x() + dist, center.y() + 1, rect.width() - 1, center.y() + 1)
            painter.drawLine(center.x() + dist, center.y() - 1, rect.width() - 1, center.y() - 1)
            painter.drawLine(center.x() - 1, rect.y(), center.x() - 1, center.y() - dist)
            painter.drawLine(center.x() + 1, rect.y(), center.x() + 1, center.y() - dist)
            painter.drawLine(center.x() + 1, center.y() + dist, center.x() + 1, rect.height() - 1)
            painter.drawLine(center.x() - 1, center.y() + dist, center.x() - 1, rect.height() - 1)

            painter.setPen(QPen(QColor(255, 255, 255, tr_white), 1))
            painter.drawLine(rect.x(), center.y(), center.x() - dist, center.y())
            painter.drawLine(center.x() + dist, center.y(), rect.width() - 1, center.y())
            painter.drawLine(center.x(), rect.y(), center.x(), center.y() - dist)
            painter.drawLine(center.x(), center.y() + dist, center.x(), rect.height() - 1)

            if size.width() > 1:
                if self.mode == Canvas.LINE:
                    painter.setPen(QPen(QColor(0, 0, 0, tr_black), 3))
                    painter.drawPoint(center.x(), center.y())
                    painter.setPen(QPen(QColor(255, 255, 255, tr_white), 1))
                    painter.drawEllipse(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
                elif self.mode == Canvas.ERASE:
                    painter.drawRect(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
            else:
                painter.setPen(QPen(QColor(0, 0, 0, tr_black), 3))
                painter.drawPoint(center.x(), center.y())
                painter.setPen(QPen(QColor(255, 255, 255, tr_white), 1))
                painter.drawPoint(center.x(), center.y())

            painter.end()
        else:
            cursor = QPixmap(QSize(size.width() + 3 + 1, size.height() + 3 + 1))
            cursor.fill(Qt.transparent)
            painter = QPainter(cursor)
            painter.setPen(QPen(QColor(0, 0, 0, tr_black), 1))
            center = cursor.rect().center() + QPoint(1, 1)
            if self.mode == Canvas.LINE:
                painter.setRenderHint(QPainter.Antialiasing)
                painter.drawEllipse(center.x() - size.width() / 2, center.y() - size.height() / 2,
                                    size.width(), size.height())
                painter.setPen(QPen(QColor(255, 255, 255, tr_white), 1))
                painter.drawEllipse(center.x() - size.width() / 2 + 1, center.y() - size.height() / 2 + 1,
                                    size.width() - 2, size.height() - 2)
            elif self.mode == Canvas.ERASE:
                painter.drawRect(center.x() - size.width() / 2, center.y() - size.height() / 2,
                                 size.width(), size.height())
                painter.setPen(QPen(QColor(255, 255, 255, tr_white), 1))
                painter.drawRect(center.x() - size.width() / 2 + 1, center.y() - size.height() / 2 + 1,
                                 size.width() - 2, size.height() - 2)
            painter.end()

        super().setCursor(QCursor(cursor))


class Paint(QDialog):
    READY_ENDO = 1
    READY_EPI = 2

    def _setUI(self, background: str) -> None:
        self.setObjectName("paint")

        with open("static/styles/paint.css", "r") as style:
            self.setStyleSheet(style.read())

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        instruments = Instruments()
        picture = Canvas(background)

        layout.addWidget(instruments, alignment=Qt.AlignTop | Qt.AlignCenter)
        layout.addWidget(picture)

        self.setLayout(layout)
        Utils.move_center_hint(self)

    def __init__(self,
                 background: str,
                 type: int = None,
                 contour: list = None,
                 scale_start: QPointF = None,
                 scale_end: QPointF = None):
        super().__init__()

        from os.path import basename, dirname

        dir = basename(dirname(background))
        self.setWindowTitle(dir)

        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint)
        self.setWindowFlag(Qt.WindowMinimizeButtonHint)
        self._setUI(background)

        type_brush: QPushButton = self.findChild(QPushButton, "type_brush")
        brush: QPushButton = self.findChild(QPushButton, "brush")
        width: EntryLine = self.findChild(EntryLine, "width")
        eraser: QPushButton = self.findChild(QPushButton, "eraser")
        dot_brush: QPushButton = self.findChild(QPushButton, "dot_brush")
        accept: QPushButton = self.findChild(QPushButton, "accept")
        canvas: Canvas = self.findChild(Canvas)

        if scale_start is not None and scale_end is not None:
            dot_brush.setEnabled(False)
            dot_brush.setIcon(QIcon("static/images/dot_brush_disabled.png"))
            dot_brush.setIconSize(QSize(28, 28))

        if scale_start is not None:
            canvas.setBrush(mode=Canvas.POINT, width=1, color=Canvas.PURPLE)
            canvas.draw_scale(scale_start)

        if scale_end is not None:
            canvas.setBrush(mode=Canvas.POINT, width=1, color=Canvas.PURPLE)
            canvas.draw_scale(scale_end)

        if contour is not None:
            if type == Paint.READY_ENDO:
                canvas.setBrush(mode=Canvas.LINE, width=1, color=Canvas.RED)
                canvas.draw_contour(contour)
                type_brush.setChecked(Instruments.EPI)
                canvas.setBrush(mode=Canvas.LINE, width=int(width.text()), color=Canvas.YELLOW)
            elif type == Paint.READY_EPI:
                canvas.setBrush(mode=Canvas.LINE, width=1, color=Canvas.YELLOW)
                canvas.draw_contour(contour)
                type_brush.setChecked(Instruments.ENDO)
                canvas.setBrush(mode=Canvas.LINE, width=int(width.text()), color=Canvas.RED)
            type_brush.setEnabled(False)
        else:
            canvas.setBrush(mode=Canvas.LINE, width=int(width.text()), color=Canvas.RED)

        type_brush.toggled.connect(self.change_type_brush)
        brush.toggled.connect(self.change_brush)
        eraser.toggled.connect(self.change_eraser)
        dot_brush.toggled.connect(self.change_dot_brush)
        width.textEdited.connect(self.change_width)
        accept.clicked.connect(self.accept)

        self.showMaximized()

    def change_type_brush(self, type: int) -> None:
        dot_brush: QPushButton = self.findChild(QPushButton, "dot_brush")
        if dot_brush.isChecked():
            return

        canvas: Canvas = self.findChild(Canvas)
        width: EntryLine = self.findChild(EntryLine, "width")

        if type == Instruments.ENDO:
            canvas.setBrush(color=Canvas.RED)
        elif type == Instruments.EPI:
            canvas.setBrush(color=Canvas.YELLOW)

    def change_brush(self, enable: bool) -> None:
        if enable:
            type_brush: QPushButton = self.findChild(QPushButton, "type_brush")
            width: EntryLine = self.findChild(EntryLine, "width")
            canvas: Canvas = self.findChild(Canvas)
            if type_brush.isChecked() == Instruments.ENDO:
                canvas.setBrush(mode=Canvas.LINE, color=Canvas.RED, width=int(width.text()))
            elif type_brush.isChecked() == Instruments.EPI:
                canvas.setBrush(mode=Canvas.LINE, color=Canvas.YELLOW, width=int(width.text()))

    def change_width(self, width: int) -> None:
        dot_brush: QPushButton = self.findChild(QPushButton, "dot_brush")
        if dot_brush.isChecked():
            return

        if width:
            canvas: Canvas = self.findChild(Canvas)
            width: EntryLine = self.findChild(EntryLine, "width")
            canvas.setBrush(width=int(width.text()))

    def change_eraser(self, enable: bool) -> None:
        if enable:
            canvas: Canvas = self.findChild(Canvas)
            width: EntryLine = self.findChild(EntryLine, "width")
            canvas.setBrush(mode=Canvas.ERASE, width=int(width.text()) + 4)

    def change_dot_brush(self, enable: bool) -> None:
        if enable:
            canvas: Canvas = self.findChild(Canvas)
            canvas.setBrush(mode=Canvas.POINT, color=Canvas.PURPLE, width=1)

    def exec_(self) -> Union[dict, int]:
        done = super().exec_()

        if not done:
            return done

        canvas: Canvas = self.findChild(Canvas)
        image: np.ndarray = rgb_view(canvas.scene().items()[0].merge())

        contours = {
            "endo": np.all(image == (255, 0, 0), axis=-1),
            "epi": np.all(image == (255, 255, 0), axis=-1),
            "scale": np.array(np.where(np.all(image == np.array([255, 0, 255]), axis=2))).T
        }

        endo_exist = np.any(contours["endo"])
        epi_exist = np.any(contours["epi"])

        try:
            contours["scale_start"] = QPoint(contours.get("scale")[0][1], contours.get("scale")[0][0])
            contours["scale_end"] = QPoint(contours.get("scale")[1][1], contours.get("scale")[1][0])
        except IndexError:
            contours["scale_start"] = QPoint(-1, -1)
            contours["scale_end"] = QPoint(-1, -1)

        del contours["scale"]

        if not endo_exist:
            del contours["endo"]

        if not epi_exist:
            del contours["epi"]

        return contours
