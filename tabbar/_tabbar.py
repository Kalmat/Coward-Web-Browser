from PyQt6.QtWidgets import QTabBar


class TabBar(QTabBar):

    def __init__(self, parent, enter_signal=None, leave_signal=None):
        super(TabBar, self).__init__(parent)

        self.enter_signal = enter_signal
        self.leave_signal = leave_signal

    # this will align tab titles to left (maybe a "little bit" excessive, but fun...)
    # WARNING: moving tabs produces weird behavior
    # def paintEvent(self, event):
    #     # thanks to Oleg Palamarchuk: https://stackoverflow.com/questions/77257766/left-alignment-of-tab-names
    #     painter = QStylePainter(self)
    #     opt = QStyleOptionTab()
    #
    #     for i in range(self.count()):
    #         self.initStyleOption(opt, i)
    #
    #         painter.drawControl(QStyle.ControlElement.CE_TabBarTabShape, opt)
    #         painter.save()
    #
    #         r = self.tabRect(i)
    #         opt.rect = r
    #
    #         textGap = 8
    #         if i < self.count() - 1:
    #             painter.drawImage(QRect(r.x() + 8, r.y() + ((r.height() - 32) // 2), self.iconSize().width(), self.iconSize().height()), QImage(opt.icon.pixmap(QSize(self.iconSize().width(), self.iconSize().height()))))
    #             textGap = 32
    #
    #         if self.parent().tabPosition() == QTabWidget.TabPosition.North or i == self.count() - 1:
    #             painter.drawText(QRect(r.x() + textGap, r.y(), r.width(), r.height()), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, opt.text)
    #
    #         painter.restore()

    def enterEvent(self, event):
        if self.enter_signal is not None:
            self.enter_signal.emit()

    def leaveEvent(self, event):
        if self.leave_signal is not None:
            self.leave_signal.emit()

    def keyReleaseEvent(self, a0):
        self.parent().keyReleaseEvent(a0)