from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QToolBar


class TitleBar(QToolBar):

    _sticky_margin = 20

    def __init__(self, parent, is_custom, enter_signal=None, leave_signal=None):
        super(TitleBar, self).__init__(parent)

        self.isCustom = is_custom
        self.enter_signal = enter_signal
        self.leave_signal = leave_signal

        self.setMouseTracking(True)

        self.moving = False
        self.offset = parent.pos()

        if is_custom:
            self.parent().setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            self.setAutoFillBackground(True)
            self.setBackgroundRole(QPalette.ColorRole.Highlight)

        self.screenSize = self.screen().availableGeometry()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isCustom:
            self.moving = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.moving:
            # in PyQt6 globalPos() has been replaced by globalPosition(), which returns a QPointF() object
            self.parent().move(event.globalPosition().toPoint() - self.offset)

    def mouseReleaseEvent(self, event):
        self.moving = False

        x = y = None

        if -self._sticky_margin < self.parent().x() < self._sticky_margin:
            x = 0
        elif -self._sticky_margin < self.screenSize.width() - (self.parent().x() + self.parent().width()) < self._sticky_margin:
            x = self.screenSize.width() - self.parent().width()

        if -self._sticky_margin < self.parent().y() < self._sticky_margin:
            y = 0
        elif -self._sticky_margin < self.screenSize.height() - (self.parent().y() + self.parent().height()) < self._sticky_margin:
            y = self.screenSize.height() - self.parent().height()

        if x is not None or y is not None:
            pos = QPoint(self.parent().x() if x is None else x, self.parent().y() if y is None else y)
            self.parent().move(pos)

    def enterEvent(self, event):
        if self.enter_signal is not None:
            self.enter_signal.emit()

    def leaveEvent(self, event):
        if self.leave_signal is not None:
            self.leave_signal.emit()
