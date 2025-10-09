from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QTabWidget, QTabBar


class TabWidget(QTabWidget):

    def __init__(self, parent):
        super().__init__(parent)

        self.font_metrics = QFontMetrics(self.font())
        self.char_width = self.font_metrics.averageCharWidth()
        self.icon_size = self.parent().icon_size + 8  # add padding

        self.resizeEvent = self.on_resize

    def _getTextSize(self, index, orig_text):
        button = self.tabBar().tabButton(index, QTabBar.ButtonPosition.RightSide)
        if button is not None:
            b_width = button.width() + 10
            available_width = self.width() - ((self.icon_size + b_width) * self.count())
            target_length = min(len(orig_text), int(available_width / self.count() / self.char_width))
        else:
            target_length = 0 if 0 < index < self.count() -1 else 1
        return target_length

    def on_resize(self, event):
        for i in range(1, self.count() - 1):
            orig_text = self.tabWhatsThis(i)
            self.setTabText(i, orig_text)
        super().resizeEvent(event)

    def addTab(self, widget, a1, h_tabbar=True, forceText=False):
        if h_tabbar or forceText:
            tabIndex = super().addTab(widget, a1)
            self.setTabText(tabIndex, a1)
        else:
            tabIndex = super().addTab(widget, "")
        self.setTabWhatsThis(tabIndex, a1)
        # force to recalculate all tabs text sizes
        self.resize(self.size())
        return tabIndex

    def insertTab(self, index, widget, a2, h_tabbar=True, forceText=False):
        if h_tabbar or forceText:
            index = super().insertTab(index, widget, a2)
            self.setTabText(index, a2)
        else:
            index = super().insertTab(index, widget, "")
        if isinstance(a2, str):
            self.setTabWhatsThis(index, a2)
        # force to recalculate all tabs text sizes
        self.resize(self.size())
        return index

    def setTabText(self, index, a1):
        target_text = a1
        if 0 < index < self.count() - 1:
            target_text = a1[:self._getTextSize(index, a1)]
        super().setTabText(index, target_text)

    def removeTab(self, index):
        super().removeTab(index)
        # force to recalculate all tabs text sizes
        self.resize(self.size())

    def setCurrentIndex(self, index):
        index = max(1, min(index, self.count() - 2))
        super().setCurrentIndex(index)

    def keyPressEvent(self, a0):
        pass

    def keyReleaseEvent(self, a0):
        self.parent().keyReleaseEvent(a0)
