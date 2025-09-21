from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QTabWidget


class TabWidget(QTabWidget):

    def __init__(self, parent):
        super().__init__(parent)

    def setCurrentIndex(self, index):
        index = max(1, min(index, self.count() - 2))
        if self.widget(index) is None or not isinstance(self.widget(index), QWebEngineView):
            index = 1
        super().setCurrentIndex(index)

    def keyReleaseEvent(self, a0):
        self.parent().keyReleaseEvent(a0)
