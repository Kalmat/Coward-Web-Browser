from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTabWidget


class TabWidget(QTabWidget):

    def __init__(self, parent):
        super().__init__(parent)

    def setCurrentIndex(self, index):
        index = max(1, min(index, self.count() - 2))
        super().setCurrentIndex(index)
    #
    def keyPressEvent(self, a0):
        pass

    def keyReleaseEvent(self, a0):

        if a0.key() == Qt.Key.Key_Backtab:
            if a0.modifiers() == Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier:
                index = self.currentIndex() - 1
                if index <= 0:
                    index = self.count() - 2
                self.setCurrentIndex(index)

        elif a0.key() == Qt.Key.Key_Tab:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                index = self.currentIndex() + 1
                if index >= self.count() - 1:
                    index = 1
                self.setCurrentIndex(index)

