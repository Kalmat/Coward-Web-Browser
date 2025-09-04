from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget


class HoverWidget(QWidget):

    def __init__(self, parent, obj_to_show, enter_signal=None, leave_signal=None):
        super(HoverWidget, self).__init__(parent)

        self.obj_to_show = obj_to_show
        self.enter_signal = enter_signal
        self.leave_signal = leave_signal

        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodTransparent)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)

    def enterEvent(self, a0):
        if self.enter_signal is not None:
            self.enter_signal.emit()

    def leaveEvent(self, a0):
        if self.leave_signal is not None:
            self.leave_signal.emit()


