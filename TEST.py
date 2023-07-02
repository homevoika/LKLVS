from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import numpy as np

app = QApplication([])

scene = QGraphicsScene()
view = QGraphicsView()
view.setScene(scene)
view.setFrameStyle(False)

view.resize(500, 500)
print(view.sizeHint())

# pixmap = QPixmap(1472, 688)
# pixmap.fill(Qt.darkGreen)
# GQPixmap = QGraphicsPixmapItem(pixmap)
# scene.addItem(GQPixmap)

view.show()

app.exec_()
