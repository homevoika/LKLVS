from typing import Union, List, Dict
import numpy as np

from PyQt5.QtCore import QThread, pyqtSignal, QPoint, QPointF, QObject
from PyQt5.QtGui import QImage

from qimage2ndarray import rgb_view
from skimage.color.colorconv import rgb2gray, rgba2rgb, rgb2hsv
from skimage.transform import pyramid_gaussian


def _mean_vector(cont_x, cont_y, x_point, y_point):
    vec_x, vec_y = [], []
    for x, y in zip(cont_x - x_point, cont_y - y_point):
        cur_dist = np.linalg.norm((x, y))
        if cur_dist != 0:
            vec_x.append(x / cur_dist)
            vec_y.append(y / cur_dist)
    return np.mean(vec_x), np.mean(vec_y)


def _variance(cont_x, cont_y, vec_x, vec_y):
    var = []
    for x, y in zip(cont_x, cont_y):
        var.append(np.linalg.norm((x - vec_x * (x * vec_x + y * vec_y) / (vec_x ** 2 + vec_y ** 2),
                                   y - vec_y * (x * vec_x + y * vec_y) / (vec_x ** 2 + vec_y ** 2))))

    return np.mean(var)


def _imread(file: str, as_gray=False):
    img = rgb_view(QImage(file))

    if img.ndim > 2:
        if img.shape[-1] not in (3, 4) and img.shape[-3] in (3, 4):
            img = np.swapaxes(img, -1, -3)
            img = np.swapaxes(img, -2, -3)

        if as_gray:
            if img.shape[2] == 4:
                img = rgba2rgb(img)
            img = rgb2gray(img)

    return img


def _cart2pol(x, y, cent_x, cent_y, norm=2):
    """Return phi, rho"""
    rho = (abs(x - cent_x) ** norm + abs(y - cent_y) ** norm) ** (1 / norm)
    phi = np.arctan2(y - cent_y, x - cent_x)
    return phi, rho


def _area2cont(im_area):
    im_cont = im_area.copy()
    y, x = np.where(im_cont != 0)
    for i, j in zip(x, y):
        if im_area[j + 1, i] != 0 and im_area[j - 1, i] != 0 and im_area[j, i - 1] != 0 and im_area[j, i + 1] != 0:
            im_cont[j, i] = 0
    return im_cont


def _pol2cart(phi, rho, cent_x, cent_y):
    """Return x, y"""
    x = rho * np.cos(phi)
    y = rho * np.sin(phi)
    return x + cent_x, y + cent_y


def _get_main_points(img):
    """
    return apex_point, base_left_point, base_right_point
    """
    cont_y, cont_x = np.where(img != 0)
    cent_x, cent_y = np.mean(cont_x), np.mean(cont_y)

    h = 1000
    w = 1000
    k_w = w / img.shape[1]
    k_h = h / img.shape[0]

    new_cont_x, new_cont_y = cont_x * k_w, cont_y * k_h
    cont_phi, cont_rho = _cart2pol(new_cont_x,
                                   new_cont_y,
                                   np.mean(new_cont_x),
                                   np.mean(new_cont_y))
    indexes = np.argsort(cont_phi)
    cont_phi = cont_phi[indexes]
    cont_rho = cont_rho[indexes]
    pos_indexes = cont_phi >= 0
    neg_indexes = cont_phi < 0
    index = np.argmax(cont_rho[neg_indexes])
    top_x, top_y = _pol2cart(cont_phi[neg_indexes][index],
                             cont_rho[neg_indexes][index],
                             np.mean(new_cont_x),
                             np.mean(new_cont_y))
    dict_base = {}
    for i in range(-100, 101):
        base_phi, base_rho = _cart2pol(new_cont_x,
                                       new_cont_y,
                                       top_x + i,
                                       top_y)
        index = np.argmax(base_rho)
        if index in dict_base.keys():
            dict_base[index] += 1
        else:
            dict_base[index] = 1

    count = 0
    for k in dict_base.keys():
        if count < dict_base[k]:
            index = k
            count = dict_base[k]
    base_x, base_y = new_cont_x[index], new_cont_y[index]

    base_phi, base_rho = _cart2pol(base_x,
                                   base_y,
                                   np.mean(new_cont_x),
                                   np.mean(new_cont_y))

    check_r_phi = cont_phi[pos_indexes][cont_phi[pos_indexes] < base_phi]
    check_r_rho = cont_rho[pos_indexes][cont_phi[pos_indexes] < base_phi]
    check_l_phi = cont_phi[pos_indexes][cont_phi[pos_indexes] > base_phi]
    check_l_rho = cont_rho[pos_indexes][cont_phi[pos_indexes] > base_phi]

    r_x, r_y = _pol2cart(check_r_phi,
                         check_r_rho,
                         np.mean(new_cont_x),
                         np.mean(new_cont_y))

    l_x, l_y = _pol2cart(check_l_phi,
                         check_l_rho,
                         np.mean(new_cont_x),
                         np.mean(new_cont_y))

    var_l = _variance(l_x - base_x, l_y - base_y, l_x[0] - l_x[-1], l_y[0] - l_y[-1])
    var_r = _variance(r_x - base_x, r_y - base_y, r_x[0] - r_x[-1], r_y[0] - r_y[-1])
    base_l_x, base_l_y, base_r_x, base_r_y = None, None, None, None

    if var_r > var_l:
        check_x, check_y = r_x, r_y
        indexes = np.array(
            [i for i, (x, y) in enumerate(zip(check_x, check_y)) if np.linalg.norm((x - base_x, y - base_y)) < 200],
            dtype=int)
        norm_vec_x, norm_vec_y = _mean_vector(np.array(check_x)[indexes], np.array(check_y)[indexes], base_x, base_y)
        norm_vec_x, norm_vec_y = norm_vec_y, -norm_vec_x
        base_l_x, base_l_y = base_x / k_w, base_y / k_h
        edge_x, edge_y = check_x[0], check_y[0]
    else:
        check_x, check_y = l_x, l_y
        indexes = np.array(
            [i for i, (x, y) in enumerate(zip(check_x, check_y)) if np.linalg.norm((x - base_x, y - base_y)) < 200],
            dtype=int)
        norm_vec_x, norm_vec_y = _mean_vector(np.array(check_x)[indexes], np.array(check_y)[indexes], base_x, base_y)
        norm_vec_x, norm_vec_y = -norm_vec_y, norm_vec_x
        base_r_x, base_r_y = base_x / k_w, base_y / k_h
        edge_x, edge_y = check_x[-1], check_y[-1]

    k = 10
    c_x, c_y = base_x + k * norm_vec_x, base_y + k * norm_vec_y
    while np.linalg.norm((c_x - base_x, c_y - base_y)) <= np.linalg.norm((edge_x - c_x, edge_y - c_y)) or c_y > top_y:
        if k > 1000:
            break
        k += 1
        c_x, c_y = base_x + k * norm_vec_x, base_y + k * norm_vec_y

    check_phi, check_rho = _cart2pol(check_x,
                                     check_y,
                                     c_x,
                                     c_y,
                                     )

    check_phi[check_phi <= -np.pi / 2] += 2 * np.pi

    index = np.argmax(check_rho)
    base_x, base_y = check_x[index], check_y[index]

    if base_r_x is None and base_r_y is None:
        base_r_x, base_r_y = base_x / k_w, base_y / k_h

    elif base_l_x is None and base_l_y is None:
        base_l_x, base_l_y = base_x / k_w, base_y / k_h

    cont_phi, cont_rho = _cart2pol(cont_x, cont_y, (base_l_x + base_r_x) / 2, (base_l_y + base_r_y) / 2)
    index = np.argmax(cont_rho)
    apex_phi, apex_rho = cont_phi[index], cont_rho[index]
    apex_x, apex_y = _pol2cart(apex_phi,
                               apex_rho,
                               (base_l_x + base_r_x) / 2,
                               (base_l_y + base_r_y) / 2)

    return (apex_x, apex_y), (base_l_x, base_l_y), (base_r_x, base_r_y), cent_x, cent_y


def _get_points(img, amount_points):
    img_cont = _area2cont(img)

    h = 1000
    w = 1000
    k_w = w / img_cont.shape[1]
    k_h = h / img_cont.shape[0]
    cont_y, cont_x = np.where(img_cont != 0)

    top_point, base_l_point, base_r_point, orig_cent_x, orig_cent_y = _get_main_points(img_cont)

    cont_x, cont_y = cont_x * k_w, cont_y * k_h
    cent_x, cent_y = np.mean(cont_x), np.mean(cont_y)

    cont_phi, cont_rho = _cart2pol(cont_x, cont_y, cent_x, cent_y)
    base_l_point = _cart2pol(base_l_point[0] * k_w, base_l_point[1] * k_h, cent_x, cent_y)
    base_r_point = _cart2pol(base_r_point[0] * k_w, base_r_point[1] * k_h, cent_x, cent_y)
    top_point = _cart2pol(top_point[0] * k_w, top_point[1] * k_h, cent_x, cent_y)

    cont_rho = cont_rho[
        (cont_phi <= min(base_l_point[0], base_r_point[0])) | (cont_phi >= max(base_l_point[0], base_r_point[0]))]
    cont_phi = cont_phi[
        (cont_phi <= min(base_l_point[0], base_r_point[0])) | (cont_phi >= max(base_l_point[0], base_r_point[0]))]

    cont_phi[cont_phi >= max(base_l_point[0], base_r_point[0])] -= 2 * np.pi
    indexes = np.argsort(cont_phi)
    cont_phi = cont_phi[indexes]
    cont_rho = cont_rho[indexes]

    if amount_points % 2:
        cont_phi_l = cont_phi[cont_phi <= top_point[0]]
        cont_rho_l = cont_rho[cont_phi <= top_point[0]]
        cont_phi_r = cont_phi[cont_phi >= top_point[0]]
        cont_rho_r = cont_rho[cont_phi >= top_point[0]]
        cont_phi = np.concatenate((
            np.array([base_l_point[0]]),
            cont_phi_l[np.linspace(0, len(cont_phi_l) - 1, amount_points // 2 + 1, dtype=int)][1:-1],
            np.array([top_point[0]]),
            cont_phi_r[np.linspace(0, len(cont_phi_r) - 1, amount_points // 2 + 1, dtype=int)][1:-1],
            np.array([base_r_point[0]]),
        ))
        cont_rho = np.concatenate((
            np.array([base_l_point[1]]),
            cont_rho_l[np.linspace(0, len(cont_rho_l) - 1, amount_points // 2 + 1, dtype=int)][1:-1],
            np.array([top_point[1]]),
            cont_rho_r[np.linspace(0, len(cont_rho_r) - 1, amount_points // 2 + 1, dtype=int)][1:-1],
            np.array([base_r_point[1]]),
        ))
    else:
        cont_phi = cont_phi[np.linspace(0, len(cont_phi) - 1, amount_points, dtype=int)]
        cont_rho = cont_rho[np.linspace(0, len(cont_rho) - 1, amount_points, dtype=int)]

    cont_x, cont_y = _pol2cart(cont_phi, cont_rho, cent_x, cent_y)
    cont_x, cont_y = cont_x / k_w, cont_y / k_h
    cont_phi, cont_rho = _cart2pol(cont_x, cont_y, orig_cent_x, orig_cent_y)

    cont_x, cont_y = _pol2cart(cont_phi, cont_rho, orig_cent_x, orig_cent_y)
    return np.uint16(cont_x), np.uint16(cont_y), orig_cent_x, orig_cent_y


class LucasKanade(QThread):
    released = pyqtSignal(dict)

    def __init__(self, amount_points: int, parent: QObject):
        super().__init__(parent)

        self.amount_points = amount_points
        self.contours = {}
        self.files = []

    def begin(self, contours: dict, files: list):
        self.contours = contours
        self.files = files
        self.start()

    def win_image(self, img: np.ndarray, point: QPointF) -> np.ndarray:
        win = 61
        p1 = QPoint(round(point.x()) - win // 2, round(point.y()) - win // 2)
        p2 = QPoint(round(point.x()) + win // 2 + 1, round(point.y()) + win // 2 + 1)

        if p1.x() < 0:
            p1.setX(0)
        if p1.y() < 0:
            p1.setY(0)
        if p2.x() > img.shape[1]:
            p2.setX(img.shape[1])
        if p2.y() > img.shape[0]:
            p2.setY(img.shape[0])

        img: np.ndarray = img[p1.y():p2.y(), p1.x():p2.x()]

        if img.shape[0] != win:
            if p1.y() == 0:
                img = np.concatenate((np.zeros((win - img.shape[0], img.shape[1])), img), axis=0)
            elif p2.y() == img.shape[0]:
                img = np.concatenate((img, np.zeros((win - img.shape[0], img.shape[1]))), axis=0)

        if img.shape[1] != win:
            if p1.x() == 0:
                img = np.concatenate((np.zeros((img.shape[0], win - img.shape[1])), img), axis=1)
            elif p2.x() == image.shape[1]:
                img = np.concatenate((img, np.zeros((img.shape[0], win - img.shape[1]))), axis=1)

        return img

    def sorted(self, contours: dict, data: dict) -> None:
        for wall, contour in self.contours.items():
            if isinstance(contour, np.ndarray):
                x_s, y_s, *_ = _get_points(contour, self.amount_points)
                contours[wall] = [QPointF(x, y) for x, y in zip(x_s, y_s)]
            elif isinstance(contour, str):
                rang = (0.06, 0.07)
                cread = _imread(contour)

                scale = np.array(np.where(np.all(cread == np.array([163, 73, 164]), axis=2))).T
                try:
                    data["scale_start"] = QPoint(scale[0][0], scale[0][1])
                    data["scale_end"] = QPoint(scale[1][0], scale[1][1])
                except IndexError:
                    data["scale_start"] = QPoint(-1, -1)
                    data["scale_end"] = QPoint(-1, -1)

                hsvcont = rgb2hsv(cread[:, :, :3])
                contour = (hsvcont[:, :, 0] > rang[0]) & (hsvcont[:, :, 0] < rang[1])

                x_s, y_s, *_ = _get_points(contour, self.amount_points)
                contours[wall] = [QPointF(x, y) for x, y in zip(x_s, y_s)]
            elif isinstance(contour, list) and isinstance(contour[0], list):
                data[wall] = contour
            elif isinstance(contour, list):
                contours[wall] = contour
        self.contours = {}

    def run(self) -> None:

        contours, data = {}, {}
        self.sorted(contours, data)

        if not contours and not data:
            print("Set contours or data and restart")
            return

        if not self.files:
            print("Set files and restart")
            return

        for type, contour in contours.items():

            result = [contour]
            files = iter(self.files)

            im2read = _imread(next(files), as_gray=True)

            while True:
                try:
                    im1read = im2read
                    im2read = _imread(next(files), as_gray=True)
                except StopIteration:
                    break

                layers1 = list(pyramid_gaussian(im1read, max_layer=1))
                layers2 = list(pyramid_gaussian(im2read, max_layer=1))

                points = []

                for point in contour:
                    flow = np.array([[0], [0]])
                    for n, (layer1, layer2) in enumerate(zip(layers1[::-1], layers2[::-1])):
                        degree = 1 - n

                        layer1 = self.win_image(layer1, QPointF(point.x() / 2 ** degree,
                                                                point.y() / 2 ** degree))
                        layer2 = self.win_image(layer2, QPointF((point.x() + flow[0]) / 2 ** degree,
                                                                (point.y() + flow[1]) / 2 ** degree))

                        fy, fx = np.gradient(layer1)
                        ft = layer1 - layer2
                        A = np.array([[np.sum(fx ** 2), np.sum(fx * fy)],
                                      [np.sum(fx * fy), np.sum(fy ** 2)]])
                        B = np.array([[np.sum(fx * ft)],
                                      [np.sum(fy * ft)]])

                        solv_flow = np.linalg.lstsq(A, B, rcond=None)[0]
                        flow = (flow + solv_flow) * 2

                    points.append(QPointF(point.x() + int(flow[0]), point.y() + int(flow[1])))

                result.append(points)

            data[type] = result

        self.contours = {}
        self.files = []

        self.released.emit(data)
