import os

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox
from PyQt5.QtGui import QMouseEvent, QIntValidator
from PyQt5.QtCore import QObject, Qt, QPoint, QPointF

from config import get_param, set_param
from options import Options
from paint import Paint
from workspace import Workspace
from diviewer import Diviewer

from pydicom import dcmread, errors
from pydicom.pixel_data_handlers import convert_color_space
from pathlib import Path

from typing import Union


class EntryLine(QWidget):
    def __init__(self, title: str, parent: QObject = None):
        super().__init__(parent)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(5)

        title = QLabel(title)
        title.setObjectName("title_entry")

        validator = QIntValidator()
        validator.setBottom(0)

        entry = QLineEdit()
        entry.setValidator(validator)
        entry.setObjectName("entry")
        entry.setContextMenuPolicy(Qt.PreventContextMenu)

        layout.addWidget(title, alignment=Qt.AlignCenter)
        layout.addWidget(entry, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def setMaxLengthEntry(self, value: int) -> None:
        entry: QLineEdit = self.findChild(QLineEdit, "entry")
        entry.setMaxLength(value)

    def setValueEntry(self, value: str) -> None:
        entry: QLineEdit = self.findChild(QLineEdit, "entry")
        entry.setText(value)

    def getText(self) -> str:
        entry: QLineEdit = self.findChild(QLineEdit, "entry")
        return entry.text()


class Home(QWidget):
    def _setUI(self) -> None:

        self.setObjectName("home")

        with open("static/styles/home.css", "r") as style:
            self.setStyleSheet(style.read())

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)
        layout.setContentsMargins(50, 40, 50, 60)

        title = QLabel("Lucas Kanade \nLeft Ventricle Segmentation")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("title")

        amount_points = EntryLine("Amount of points")
        amount_points.setObjectName("amount_of_points")
        amount_points.setMaxLengthEntry(3)
        amount_points.setValueEntry(get_param("amount_of_points"))

        step_processing = EntryLine("Step processing")
        step_processing.setObjectName("step_processing")
        step_processing.setMaxLengthEntry(2)
        step_processing.setValueEntry("1")

        select_files = QPushButton("Select files")
        select_files.setObjectName("select_files")
        select_files.setCursor(Qt.PointingHandCursor)
        select_files.setFixedWidth(310)
        select_files.clicked.connect(self.upload_files)

        dicom_viewer = QPushButton("Dicom viewer")
        dicom_viewer.setObjectName("dicom_viewer")
        dicom_viewer.setCursor(Qt.PointingHandCursor)
        dicom_viewer.setFixedWidth(310)
        dicom_viewer.clicked.connect(self.dicom_viewer)

        layout.addWidget(title)
        layout.addSpacing(20)
        layout.addWidget(amount_points)
        layout.addWidget(step_processing)
        layout.addSpacing(30)
        layout.addWidget(select_files, alignment=Qt.AlignCenter)
        layout.addSpacing(20)
        layout.addWidget(dicom_viewer, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def __init__(self):
        super().__init__()

        self._setUI()

        self.setWindowTitle("LKLVS")
        self.setFixedSize(self.sizeHint().width(), self.sizeHint().height())
        self.setFocus()

    def dicom_viewer(self) -> None:
        file = QFileDialog.getOpenFileName(
            self,
            caption="Select DICOM file",
            directory=get_param("open_dicom_dir_path")
        )

        if not file[0]:
            return

        set_param("open_dicom_dir_path", os.path.dirname(file[0]))

        try:
            dicom = dcmread(file[0])
        except (errors.InvalidDicomError, TypeError):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Error")
            msg.setText("Invalid DICOM file")
            msg.exec_()
            return

        data = None

        if "PixelData" in dicom:
            data = dicom.pixel_array
            if "PhotometricInterpretation" in dicom:
                interp = dicom.PhotometricInterpretation
                if interp in ("YBR_FULL_422", "YBR_FULL"):
                    data = convert_color_space(data, interp, "RGB")

        del dicom

        if data is None:
            return


        diviewer = Diviewer(data)
        self.hide()
        diviewer.exec_()
        self.show()
        if hasattr(diviewer, "converter"):
            diviewer.converter.deleteLater()
            del diviewer.converter
            del diviewer.save_dialog
        diviewer.deleteLater()

    def get_data(self, dir: str) -> dict:

        amount_points = int(self.findChild(EntryLine, "amount_of_points").getText())
        step_processing = int(self.findChild(EntryLine, "step_processing").getText())

        data = {
            "ready_contours": {
                "endo": [],
                "epi": []
            },
            "ready_images": {
                "endo": None,
                "epi": None
            },
            "amount_points": amount_points,
            "step_processing": step_processing,
            "frames": []
        }

        txt_exts = ("txt")
        img_exts = ("jpeg", "jpg", "png", "bmp")

        try:
            for file in os.listdir(dir):

                if os.path.isdir(os.path.join(dir, file)):
                    continue

                name, ext = file.split(".")
                path_file = os.path.join(dir, file)

                if ext in txt_exts and name.endswith("_endo"):
                    data["ready_contours"]["endo"].append(path_file)
                elif ext in txt_exts and name.endswith("_epi"):
                    data["ready_contours"]["epi"].append(path_file)
                elif ext in img_exts and name.endswith("_endo"):
                    data["ready_images"]["endo"] = path_file
                elif ext in img_exts and name.endswith("_epi"):
                    data["ready_images"]["epi"] = path_file
                elif ext in img_exts:
                    data["frames"].append(path_file)
        except PermissionError:
            return {}

        return data

    def exist_ready_data(self, data: dict) -> bool:

        exist_ready_contours = True
        exist_ready_images = True

        if not any((data["ready_contours"]["endo"], data["ready_contours"]["epi"])):
            exist_ready_contours = False
            del data["ready_contours"]

        if not any((data["ready_images"]["endo"], data["ready_images"]["epi"])):
            exist_ready_images = False
            del data["ready_images"]

        try:

            def key(path: str) -> int:
                name = Path(path).stem
                try:
                    return int("".join([v for v in name if v.isdigit()]))
                except ValueError:
                    return float("inf")

            data["frames"].sort(key=key)
        except:
            print("Failed sorting")

        return exist_ready_contours or exist_ready_images

    def read_ready_file(self, path: str) -> Union[tuple, dict]:

        data_file = {}

        with open(path, "r") as file:
            try:
                sys_id, y0, x0, y1, x1 = tuple(file.readline().strip().split(' '))
                data_file["sys_id"] = sys_id
                data_file["scale_start"] = QPoint(int(x0), int(y0))
                data_file["scale_end"] = QPoint(int(x1), int(y1))
            except ValueError:
                file.seek(0)

            contours = []
            lines = file.readlines()

            for coords in lines:
                points = []
                coords = iter(coords.strip().split(' '))
                while True:
                    try:
                        point = QPointF()
                        point.setY(float(next(coords)))
                        point.setX(float(next(coords)))
                        points.append(point)
                    except StopIteration:
                        break

                contours.append(points)

        data_file["contours"] = contours

        return data_file

    def upload_files(self) -> None:

        dir = QFileDialog.getExistingDirectory(caption="Select directory with images",
                                               directory=get_param("UPLOAD_DIR_PATH"))

        if dir:
            amount_points = self.findChild(EntryLine, "amount_of_points").getText()
            set_param("AMOUNT_OF_POINTS", amount_points)
            set_param("UPLOAD_DIR_PATH", dir)

            data = self.get_data(dir)

            if data.get("frames") is None:
                return

            if self.exist_ready_data(data):
                self.open_options(data)
            else:
                self.gallery_new_contours(data)

    def open_options(self, data: dict) -> None:
        options = Options(data)
        answer = options.exec_()

        if isinstance(answer, tuple):
            if answer[0] == Options.BOTH:
                data_files = {}
                endo_file = answer[1].get("endo")
                epi_file = answer[1].get("epi")
                if endo_file is not None and epi_file is not None:
                    data_files["endo"] = self.read_ready_file(endo_file)
                    data_files["epi"] = self.read_ready_file(epi_file)
                elif endo_file is not None:
                    data_files["endo"] = self.read_ready_file(endo_file)
                    del data["ready_contours"]["epi"]
                elif epi_file is not None:
                    data_files["epi"] = self.read_ready_file(epi_file)
                    del data["ready_contours"]["endo"]
                else:
                    return
                self.gallery_ready_contours(source_data=data, data_files=data_files)
            else:
                if answer[1] is None:
                    return
                type = Paint.READY_ENDO if answer[0] == Options.ENDO else Paint.READY_EPI
                contour = self.read_ready_file(answer[1])
                self.gallery_ready_contour(source_data=data, type=type, data_file=contour)
        elif answer == Options.NEW:
            self.gallery_new_contours(data)
        elif answer == Options.IMAGES:
            self.gallery_ready_images(data)

    def find_sys_id(self, frames: list, step: int) -> int:
        ids = list(filter(lambda file: Path(file).stem.endswith("s"), frames))
        try:
            index = frames.index(ids[0])
            left = step * (index // step)
            right = left + step
            index = left if abs(left - index) <= abs(right - index) else right
            # frame = Path(frames[index]).stem
            # return int(frame[:-1]) if frame.endswith("s") else int(frame)
            return index + 1
        except IndexError:
            return -1

    def gallery_ready_contours(self, source_data: dict, data_files: dict) -> None:
        frames = source_data.get("frames")
        endo = data_files.get("endo")
        epi = data_files.get("epi")

        if endo is not None:
            try:
                sys_id = int(endo.get("sys_id"))
            except TypeError:
                sys_id = -1
            scale_start = endo.get("scale_start")
            scale_end = endo.get("scale_end")

            step = 1
            if len(frames) != len(endo.get("contours")):
                step = round(len(frames) / len(endo.get("contours")))

            source_data["ready_contours"]["endo"] = endo.get("contours")

        if epi is not None:
            try:
                sys_id = int(epi.get("sys_id"))
            except TypeError:
                sys_id = -1
            scale_start = epi.get("scale_start")
            scale_end = epi.get("scale_end")

            step = 1
            if len(frames) != len(epi.get("contours")):
                step = round(len(frames) / len(epi.get("contours")))

            source_data["ready_contours"]["epi"] = epi.get("contours")

        del source_data["step_processing"]
        del source_data["amount_points"]

        source_data["frames"] = [source_data["frames"][n] for n in range(0, len(source_data["frames"]), step)]
        source_data["sys_id"] = sys_id
        source_data["scale_start"] = scale_start
        source_data["scale_end"] = scale_end

        self.workspace = Workspace(source_data)
        self.workspace.show()

    def gallery_ready_contour(self, source_data: dict, type: int, data_file: dict) -> None:
        frames = source_data.get("frames")
        contours = data_file.get("contours")
        sys_id = data_file.get("sys_id")
        scale_start = data_file.get("scale_start")
        scale_end = data_file.get("scale_end")
        del source_data["step_processing"]

        if scale_start == QPoint(-1, -1):
            scale_start = None

        if scale_end == QPoint(-1, -1):
            scale_end = None

        paint = Paint(background=frames[0],
                      type=type,
                      contour=contours[0],
                      scale_start=scale_start,
                      scale_end=scale_end)

        draw_result = paint.exec_()

        if not draw_result:
            return

        if type == Paint.READY_ENDO:
            source_data["ready_contours"]["endo"] = contours
            if draw_result.get("epi") is not None:
                source_data["ready_contours"]["epi"] = draw_result.get("epi")
            else:
                del source_data["ready_contours"]["epi"]
        elif type == Paint.READY_EPI:
            source_data["ready_contours"]["epi"] = contours
            if draw_result.get("endo") is not None:
                source_data["ready_contours"]["endo"] = draw_result.get("endo")
            else:
                del source_data["ready_contours"]["endo"]

        source_data["scale_start"] = scale_end if scale_start is not None else draw_result.get("scale_start")
        source_data["scale_end"] = scale_end if scale_end is not None else draw_result.get("scale_end")
        source_data["amount_points"] = len(contours[0])

        step = 1
        if len(frames) != len(contours):
            step = round(len(frames) / len(contours))

        source_data["sys_id"] = int(sys_id) if data_file.get("sys_id") is not None else self.find_sys_id(frames, step)
        source_data["frames"] = [source_data["frames"][n] for n in range(0, len(source_data["frames"]), step)]

        self.workspace = Workspace(source_data)
        self.workspace.show()

    def gallery_new_contours(self, source_data: dict) -> None:
        frames = source_data.get("frames")
        step = source_data.get("step_processing")
        paint = Paint(background=frames[0])
        draw_result = paint.exec_()

        if not draw_result or (draw_result.get("endo") is None and draw_result.get("epi") is None):
            return

        source_data["ready_contours"] = {}

        if draw_result.get("endo") is not None:
            source_data["ready_contours"]["endo"] = draw_result.get("endo")

        if draw_result.get("epi") is not None:
            source_data["ready_contours"]["epi"] = draw_result.get("epi")

        source_data["sys_id"] = self.find_sys_id(frames, step)
        source_data["scale_start"] = draw_result.get("scale_start")
        source_data["scale_end"] = draw_result.get("scale_end")

        if step > 1:
            source_data["frames"] = [source_data["frames"][n] for n in range(0, len(source_data["frames"]), step)]

        del source_data["step_processing"]

        self.workspace = Workspace(source_data)
        self.workspace.show()

    def gallery_ready_images(self, source_data: dict) -> None:
        frames = source_data.get("frames")
        step = source_data.get("step_processing")
        source_data["ready_contours"] = source_data["ready_images"]
        source_data["sys_id"] = self.find_sys_id(frames, step)

        if step > 1:
            source_data["frames"] = [source_data["frames"][n] for n in range(0, len(source_data["frames"]), step)]

        del source_data["ready_images"]
        self.workspace = Workspace(source_data)
        self.workspace.show()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus()
        super().mousePressEvent(event)
