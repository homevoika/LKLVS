import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtCore import QPoint

from home import Home

app = QApplication([])

fonts = [os.path.join("static/fonts", font) for font in os.listdir("static/fonts")]
for font in fonts:
    QFontDatabase.addApplicationFont(font)

home = Home()
home.show()

app.exec_()
