from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QSplashScreen, QVBoxLayout, QLabel

import utils
from settings import DefaultSettings


class Splash(QSplashScreen):

    def __init__(self):
        super().__init__()

        self.pixmap = QPixmap(DefaultSettings.Icons.appIconTransp)
        self.setPixmap(self.pixmap)

    def start(self, app):
        self.show()
        screenSize = utils.screenSize(self)
        self.move((screenSize.width() - self.width()) // 2, (screenSize.height() - self.height()) // 2)
        app.processEvents()

    def stop(self, window):
        self.finish(window)

