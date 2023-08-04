import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase

from home import Home, Paint

app = QApplication([])

fonts = [os.path.join("static/fonts", font) for font in os.listdir("static/fonts")]
for font in fonts:
    QFontDatabase.addApplicationFont(font)

home = Home()
home.show()

app.exec_()
