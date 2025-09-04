from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QLineEdit


class LineEdit(QLineEdit):

    def __init__(self, parent=None):
        super(LineEdit, self).__init__(parent)

    def focusInEvent(self, event):
        # this delay is needed to avoid other mouse events to interfere with selectAll() command
        super(LineEdit, self).focusInEvent(event)
        QTimer.singleShot(200, self.selectAll)
