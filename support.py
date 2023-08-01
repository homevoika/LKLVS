from PyQt5.QtWidgets import (QLineEdit, QGraphicsEllipseItem, QGraphicsLineItem,
                             QGraphicsItem, QWidget, QApplication, QStyle, QPushButton)
from PyQt5.Qt import (QKeyEvent, QValidator, pyqtSignal, QObject, Qt,
                      QPointF, QPen, QColor, QLineF, QSize, QPoint, QRect)


class ToggleButton(QPushButton):
    def __init__(self):
        super().__init__()
        self.setCheckable(True)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        pass


class GraphicLine(QGraphicsLineItem):
    def __init__(self, p1: QPointF, p2: QPointF, width: float = 2.0):
        super().__init__()
        self.setLine(p1.x(), p1.y(), p2.x(), p2.y())
        self.set_width(width)

    def set_width(self, width: float) -> None:
        super().setPen(QPen(QColor(255, 255, 0), width, cap=Qt.RoundCap, join=Qt.RoundJoin))

    def move_end(self, start: QPointF = None, end: QPointF = None):
        line: QLineF = self.line()
        if start is not None:
            line = QLineF(start, line.p2())
        if end is not None:
            line = QLineF(line.p1(), end)
        self.setLine(line)


class AddGraphicLine(GraphicLine):
    def __init__(self, p1: QPointF, p2: QPointF, width: float = 2.0):
        super().__init__(p1, p2, width)
        self.set_width(width)

    def set_width(self, width: float) -> None:
        super().setPen(QPen(QColor(255, 255, 128), width, cap=Qt.RoundCap, join=Qt.RoundJoin))


class GraphicPoint(QGraphicsEllipseItem):
    def __init__(self, point: QPointF, r: float = 5):
        super().__init__()
        self.point = point
        self.set_radius(r)
        self.setPos(point.x(), point.y())
        self.setPen(QPen(Qt.transparent, 0))
        self.setBrush(QColor(255, 0, 0))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges)
        self.setCursor(Qt.PointingHandCursor)

    def set_radius(self, r: float) -> None:
        super().setRect(-r, -r, r * 2, r * 2)

    def radius(self) -> float:
        return super().rect().width() / 2

    def set_lines(self, in_: GraphicLine = None, out_: GraphicLine = None):
        if in_ is not None and not hasattr(self, "in_"):
            self.in_ = in_
        if out_ is not None and not hasattr(self, "out_"):
            self.out_ = out_

    def scene_inside(self, value: QPointF) -> None:
        if value.x() - self.radius() < 0:
            value.setX(self.radius())
        if value.y() - self.radius() < 0:
            value.setY(self.radius())
        if value.x() + self.radius() > self.scene().width():
            value.setX(self.scene().width() - self.radius())
        if value.y() + self.radius() > self.scene().height():
            value.setY(self.scene().height() - self.radius())

    def itemChange(self, change: int, value: QPointF) -> QPointF:
        if change == QGraphicsItem.ItemPositionChange:
            self.scene_inside(value)
            if hasattr(self, "in_"):
                self.in_.move_end(end=value)
            if hasattr(self, "out_"):
                self.out_.move_end(start=value)
            self.point.setX(value.x())
            self.point.setY(value.y())
        return value


class AddGraphicPoint(GraphicPoint):
    def __init__(self, point: QPointF, r: float = 5):
        super().__init__(point, r)

        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, False)
        self.setCursor(Qt.ArrowCursor)
        self.setBrush(QColor(255, 128, 128))


class EntryLine(QLineEdit):
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Enter:
            self.clearFocus()

        if event.key() == Qt.Key_Return:
            self.clearFocus()

        if event.key() == Qt.Key_Escape:
            self.clearFocus()

        super().keyPressEvent(event)


class IntValid(QValidator):
    def validate(self, a0: str, a1: int):
        if a0[a1 - 1].isdigit():
            return QValidator.Acceptable, a0, a1
        else:
            return QValidator.Invalid, a0, a1


class EntryLinePostfix(QLineEdit):
    textChanged = pyqtSignal(str)

    def __init__(self, static_text: str, text: str = None, parent: QObject = None):
        super().__init__()

        self.setContextMenuPolicy(Qt.PreventContextMenu)
        self.static_text = static_text
        self.static_len = len(static_text)
        super().setText(static_text)
        self.setCursorPosition(0)
        if text is not None:
            self.setText(text)
        self.clearFocus()

    def setMaxLength(self, length: int) -> None:
        super().setMaxLength(length + self.static_len)

    def setText(self, text: str) -> None:
        super().setText(f"{text}{self.static_text}")

    def text(self) -> str:
        return super().text()[:-self.static_len]

    def keyPressEvent(self, event: QKeyEvent) -> None:

        is_text = event.text()
        is_del = event.key() == Qt.Key_Delete
        is_back = event.key() == Qt.Key_Backspace
        max_pos = len(super().text()) - self.static_len

        if self.selectionLength() > 0 and (is_text or is_del or is_back):
            if self.selectionStart() >= max_pos:
                self.setSelection(self.selectionStart(), 0)
                return
            elif self.selectionEnd() > max_pos:
                self.setSelection(self.selectionStart(), max_pos - self.selectionStart())
        elif is_del and self.cursorPosition() >= max_pos:
            return
        elif (is_back or is_text) and self.cursorPosition() > max_pos:
            self.setCursorPosition(max_pos)

        if event.key() == Qt.Key.Key_Return:
            if is_text:
                self.textChanged.emit(self.text())
            self.clearFocus()

        if event.key() == Qt.Key.Key_Enter:
            if is_text:
                self.textChanged.emit(self.text())
            self.clearFocus()

        if event.key() == Qt.Key.Key_Escape:
            self.clearFocus()

        super().keyPressEvent(event)


class Utils:

    @staticmethod
    def move_center(widget: QWidget) -> None:
        title = QApplication.style().pixelMetric(QStyle.PM_TitleBarHeight) // 2
        screen_center = QApplication.desktop().availableGeometry().center()
        widget_center = QPoint(widget.width() // 2, widget.height() // 2)
        frame = QRect(screen_center.x() - widget_center.x(), screen_center.y() - widget_center.y() + title,
                      widget.width(), widget.height())
        widget.setGeometry(frame)

    @staticmethod
    def move_center_hint(widget: QWidget) -> None:
        title = QApplication.style().pixelMetric(QStyle.PM_TitleBarHeight) // 2
        screen_center = QApplication.desktop().availableGeometry().center()
        size_hint = widget.sizeHint()
        widget_center = QPoint(size_hint.width() // 2, size_hint.height() // 2)
        frame = QRect(screen_center.x() - widget_center.x(), screen_center.y() - widget_center.y() + title,
                      size_hint.width(), size_hint.height())
        widget.setGeometry(frame)

    @staticmethod
    def get_scale_value(size: QSize) -> float:
        title = QApplication.style().pixelMetric(QStyle.PM_TitleBarHeight)
        screen_size = QApplication.desktop().availableGeometry().size()

        screen_aspect = screen_size.width() / screen_size.height()
        size_aspect = size.width() / size.height()

        if screen_aspect > size_aspect:
            value = (screen_size.height() + title) / size.height()
        else:
            value = screen_size.width() / size.width()

        return value * 0.9 if value < 1 else 1
