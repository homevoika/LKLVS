from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import numpy as np

from support import GraphicPoint

app = QApplication([])

widget = QWidget()
view = QGraphicsView(widget)
view.setScene(QGraphicsScene())
widget.show()

app.exec_()
