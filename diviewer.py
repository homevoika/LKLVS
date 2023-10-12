import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from qimage2ndarray import array2qimage as np2qim
import os
from support import Utils, EntryLine
from config import get_param, set_param

from PIL.Image import fromarray
from PIL.ImageDraw import Draw
from PIL.ImageFont import truetype
from PIL.PngImagePlugin import PngInfo
from skimage.color.colorconv import gray2rgb


class Animation(QPropertyAnimation):
    def __init__(self, *args):
        super().__init__(*args)
        self.setDuration(250)
        self.setEndValue(QColor('#ffffff'))

    def start(self, color: str) -> None:
        self.setStartValue(QColor(color))
        super().start(QAbstractAnimation.KeepWhenStopped)


class CommandLine(QLineEdit):
    def _setBackground(self, color) -> None:
        self.setStyleSheet(f"QLineEdit {{ background-color: {color.name()}; }}")

    background = pyqtProperty(QColor, fset=_setBackground)
    exec_command = pyqtSignal(str)

    def __init__(self, *__args):
        super().__init__(*__args)

        self.animation = Animation(self, b"background")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Enter:
            self.exec_command.emit(self.text())

        if event.key() == Qt.Key_Return:
            self.exec_command.emit(self.text())

        if event.key() == Qt.Key_Escape:
            self.clearFocus()

        super().keyPressEvent(event)


class Frame(QGraphicsView):
    def __init__(self, frame: np.ndarray, width: int = 0):
        super().__init__()
        self.setScene(QGraphicsScene())
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setFrameStyle(False)
        self.scale_counter = 0
        self.scale_value = Utils.get_scale_value(QSize(frame.shape[1], frame.shape[0]) + QSize(width, 0))
        self.scale(self.scale_value, self.scale_value)
        self.scene().addPixmap(QPixmap.fromImage(np2qim(frame)))

    def sizeHint(self) -> QSize:
        from math import ceil
        size = self.scene().items(order=Qt.AscendingOrder)[0].pixmap().size()
        width = ceil(size.width() * self.scale_value)
        height = ceil(size.height() * self.scale_value)
        return QSize(width, height)

    def setFrame(self, frame: np.ndarray) -> None:
        self.scene().clear()
        self.scene().addPixmap(QPixmap.fromImage(np2qim(frame)))

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()

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


class FrameList(QListWidget):
    def addFrame(self, name: str) -> None:
        item = QListWidgetItem(self)
        box = QCheckBox(str(name), self)
        box.setFocusPolicy(Qt.NoFocus)
        box.setChecked(True)
        self.addItem(item)
        self.setItemWidget(item, box)

    def _get_box(self, index: int) -> QCheckBox:
        item = self.item(index)
        return self.itemWidget(item)

    def includes_frames(self) -> list:
        result = []
        for n in range(self.count()):
            box = self._get_box(n)
            if box.isChecked():
                result.append(int(box.text()) - 1)
        return result

    def on_frame(self, index: int) -> None:
        self._get_box(index).setChecked(True)

    def off_frame(self, index: int) -> None:
        self._get_box(index).setChecked(False)


class HandlerFrames(QWidget):
    def __init__(self, count: int):
        super().__init__()

        self.setFixedWidth(250)
        self.count = count

        layout = QVBoxLayout()

        layout_pages = QHBoxLayout()
        layout_pages.setContentsMargins(0, 0, 0, 0)
        pages = QLabel(f"1 / {count}")
        sys_label = QLabel("sys")
        entry_sys = EntryLine()
        entry_sys.setValidator(QIntValidator(0, self.count))
        entry_sys.setMaxLength(len(str(self.count)))
        entry_sys.setObjectName("sys")
        entry_sys.setPlaceholderText("id")

        layout_pages.addWidget(pages, alignment=Qt.AlignRight)
        layout_pages.addStretch(True)
        layout_pages.addWidget(sys_label, alignment=Qt.AlignRight)
        layout_pages.addWidget(entry_sys)

        command = CommandLine()
        command.exec_command.connect(self.command_handler)
        command.setObjectName("command")
        command.setPlaceholderText("start-end, step; clear; all")

        frames = FrameList()
        frames.currentRowChanged.connect(lambda row: pages.setText(f"{row + 1} / {count}"))
        for n in range(1, count + 1):
            frames.addFrame(str(n))

        layout_buttons = QHBoxLayout()
        save = QPushButton("Save")
        save.setObjectName("Save")
        cancel = QPushButton("Cancel")
        cancel.setObjectName("Cancel")

        layout_buttons.addWidget(save)
        layout_buttons.addWidget(cancel)

        layout.addLayout(layout_pages)
        layout.addWidget(command)
        layout.addWidget(frames)
        layout.addSpacing(5)
        layout.addLayout(layout_buttons)

        self.setLayout(layout)

    def result(self) -> dict:
        frames: FrameList = self.findChild(FrameList)
        sys = self.findChild(EntryLine, "sys")
        count = frames.count()
        result = {"numbers": frames.includes_frames()}

        try:
            if (id := int(sys.text()) - 1) in result["numbers"]:
                result["sys"] = id
        except ValueError:
            pass

        return result

    def command_handler(self, command: str) -> None:
        frames: FrameList = self.findChild(FrameList)
        animation = self.findChild(CommandLine).animation
        count = frames.count()

        if command == "all":
            animation.start('#00FF91')
            for n in range(count):
                frames.on_frame(n)

        if command == "clear":
            animation.start('#00FF91')
            for n in range(count):
                frames.off_frame(n)

        frange = command.split("-")
        if len(frange) == 2:
            try:
                start = int(frange[0].strip())
                rval = frange[1].split(',')
                end = int(rval[0].strip())
                if len(rval) > 2:
                    return
                elif len(rval) == 2:
                    step = int(rval[1].strip())
                elif len(rval) == 1:
                    step = 1

                if not (1 <= start <= end <= count):
                    return

                if not step and end != start and step > end - start:
                    return

                animation.start('#00FF91')

                start -= 1
                end -= 1

                for n in range(0, start):
                    frames.off_frame(n)

                for i, n in enumerate(range(start, end + 1)):
                    frames.off_frame(n) if i % step else frames.on_frame(n)

                for n in range(end + 1, count):
                    frames.off_frame(n)

            except ValueError:
                pass


class Converter(QThread):
    progress = pyqtSignal(int)

    def __init__(self, data: np.ndarray, parent: QObject):
        super().__init__(parent)
        self.data = data
        self.stop = True
        self.finished.connect(lambda: setattr(self, "stop", True))

    def begin(self, dir: str, result: dict) -> None:
        self.dir = dir
        self.result = result
        self.start()
        self.stop = False

    def run(self) -> None:
        fcount = len(self.result["numbers"])
        font = truetype("static/fonts/HelveticaNowDisplay-Bold.ttf", 14)

        for n, fn in enumerate(self.result["numbers"]):

            if self.stop:
                break

            array = self.data[fn]
            channel = array.shape[-1]
            if channel not in (3, 4):
                array = gray2rgb(array)
            array = np.pad(array, ((16, 0), (0, 0), (0, 0)), "constant")

            image = fromarray(array)
            draw = Draw(image)

            sys = self.result.get("sys")
            sys_exist = sys is not None and sys == fn

            text = f"(s) {n + 1} / {fcount}" if sys_exist else f"{n + 1} / {fcount}"
            textlen = draw.textlength(text, font)
            draw.text((image.width - textlen - 5, 0), text=text, font=font)

            if sys_exist:
                metadata = PngInfo()
                metadata.add_text("sys_id", "1")
                image.save(os.path.join(self.dir, f"{n + 1}s.png"), pnginfo=metadata)
            else:
                image.save(os.path.join(self.dir, f"{n + 1}.png"))

            self.progress.emit(n)

        del self.result
        del self.dir


class SaveDialog(QDialog):
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


class InputDialog(QDialog):
    def __init__(self, parent: QObject = None):
        super().__init__(parent)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)

        layout_buttons = QHBoxLayout()
        layout_buttons.addStretch(True)

        accept = QPushButton("OK", clicked=self.accept)
        accept.setObjectName("accept")
        reject = QPushButton("Cancel", clicked=self.reject)
        reject.setObjectName("cancel")
        edit = QLineEdit()

        edit.textEdited.connect(self.validText)
        accept.setEnabled(False)

        layout_buttons.addWidget(accept, alignment=Qt.AlignRight)
        layout_buttons.addWidget(reject, alignment=Qt.AlignRight)

        layout.addWidget(QLabel("Folder name"))
        layout.addWidget(edit)
        layout.addSpacing(5)
        layout.addLayout(layout_buttons)

        self.setLayout(layout)
        self.setObjectName("input_dialog")
        self.setMinimumWidth(260)
        self.setFixedHeight(self.sizeHint().height())
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowTitle("Input")

    def getText(self) -> str:
        return self.findChild(QLineEdit).text()


    def validText(self, text: str) -> None:
        forbidden = """<>*?/\|":"""
        accept = self.findChild(QPushButton, "accept")
        if text and not any(fs in forbidden for fs in text):
            accept.setEnabled(True)
        else:
            accept.setEnabled(False)


class Diviewer(QDialog):
    def __init__(self, data: np.ndarray):
        super().__init__()

        self.setObjectName("Diviewer")
        self.setWindowTitle("Dicom Viewer")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint)
        self.setWindowFlag(Qt.WindowMinimizeButtonHint)
        self.data = data

        with open("static/styles/diviewer.css", "r") as style:
            self.setStyleSheet(style.read())

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        is_imgs = (self.data.ndim == 3 and self.data.shape[-1] not in (3, 4)) or self.data.ndim == 4
        is_img = (self.data.ndim == 3 and self.data.shape[-1] in (3, 4)) or self.data.ndim == 2

        if is_imgs:

            self.save_dialog = SaveDialog(self)
            save_bar: QProgressBar = self.save_dialog.findChild(QProgressBar)
            self.converter = Converter(self.data, self)
            self.save_dialog.rejected.connect(lambda: setattr(self.converter, "stop", True))
            self.converter.finished.connect(
                lambda: self.save_dialog.findChild(QPushButton, "accept").setEnabled(True))
            self.converter.progress.connect(
                lambda value: save_bar.setValue(value))

            frame = Frame(self.data[0], 250)
            handlerFrames = HandlerFrames(self.data.shape[0])
            list: QListWidget = handlerFrames.findChild(QListWidget)
            list.currentRowChanged.connect(lambda row: frame.setFrame(self.data[row]))

            save: QPushButton = handlerFrames.findChild(QPushButton, "Save")
            save.setCursor(Qt.PointingHandCursor)
            save.clicked.connect(self.save_files)
            cancel: QPushButton = handlerFrames.findChild(QPushButton, "Cancel")
            cancel.setCursor(Qt.PointingHandCursor)
            cancel.clicked.connect(self.close)

            layout.addWidget(frame)
            layout.addWidget(handlerFrames)
        elif is_img:
            frame = Frame(self.data)
            layout.addWidget(frame)

        self.setLayout(layout)
        Utils.move_center_hint(self)

    def keyPressEvent(self, event: QKeyEvent):
        pass

    def save_files(self) -> None:
        frames = self.findChild(HandlerFrames)
        result = frames.result()

        if not result.get("numbers"):
            return

        input = InputDialog(self)
        exec = input.exec_()

        if not exec:
            return

        dir = QFileDialog.getExistingDirectory(
            caption="Select directory for images",
            directory=get_param("SAVE_DICOM_DIR_PATH")
        )

        if not dir:
            return

        set_param("SAVE_DICOM_DIR_PATH", dir)


        dirsInDir = [d for d in os.listdir(dir) if os.path.isdir(os.path.join(dir, d))]
        name = input.getText()

        if name in dirsInDir:
            for n in range(2, 100):
                name = f"{name} ({n})"
                if name in dirsInDir:
                    name = name[:-3-len(str(n))]
                else:
                    break

        dir = os.path.join(dir, name)

        os.mkdir(dir)


        save_bar: QProgressBar = self.save_dialog.findChild(QProgressBar)
        save_bar.setRange(0, len(result["numbers"]) - 1)
        save_bar.reset()
        accept = self.save_dialog.findChild(QPushButton, "accept")
        accept.setEnabled(False)
        self.converter.begin(dir, result)
        self.save_dialog.clearFocus()
        self.save_dialog.exec_()
