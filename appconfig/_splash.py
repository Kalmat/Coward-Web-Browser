from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QSplashScreen

import utils
from settings import DefaultSettings


class Splash(QSplashScreen):

    def __init__(self):
        super().__init__()

        if DefaultSettings.Splash.enableSplash:
            self.pixmap = QPixmap(DefaultSettings.Splash.splashImage)
            self.pixmap = self.pixmap.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.setPixmap(self.pixmap)

    def start(self, app):
        if DefaultSettings.Splash.enableSplash:
            self.show()
            screenSize = utils.screenSize(self)
            self.move((screenSize.width() - self.width()) // 2, (screenSize.height() - self.height()) // 2)
            app.processEvents()

    def stop(self, window):
        if DefaultSettings.Splash.enableSplash:
            self.finish(window)
