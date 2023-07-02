import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtCore import QPoint
# from PyQt5.QtWidgets import *
# from PyQt5.QtGui import *
# from PyQt5.QtCore import *

from home import Home
from paint import Paint
from workspace import Workspace, Wait, WallTypes

app = QApplication([])

fonts = [os.path.join("static/fonts", font) for font in os.listdir("static/fonts")]
for font in fonts:
    QFontDatabase.addApplicationFont(font)

# home = Home()
# home.show()

paint = Paint("C:/Users/Riddle/Desktop/01_np/00.jpeg")
paint.show()

# workspace = Workspace()
# workspace.show()

app.exec_()
