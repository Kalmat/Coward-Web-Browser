from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QTabWidget


class TabWidget(QTabWidget):

    def __init__(self, parent):
        super().__init__(parent)

    def setCurrentIndex(self, index):
        index = max(1, min(index, self.count() - 2))
        super().setCurrentIndex(index)

    def keyPressEvent(self, a0):
        pass

    def keyReleaseEvent(self, a0):
        self.parent().keyReleaseEvent(a0)
