from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QSplashScreen

from settings import DefaultSettings


class Splash(QSplashScreen):

    def __init__(self):
        super().__init__()

        self.pixmap = QPixmap(DefaultSettings.Icons.appIcon)
        self.setPixmap(self.pixmap)

    def start(self, app):
        self.show()
        app.processEvents()

    def stop(self, window):
        self.finish(window)

