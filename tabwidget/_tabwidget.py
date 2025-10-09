from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QTabWidget, QTabBar


class TabWidget(QTabWidget):

    def __init__(self, parent):
        super().__init__(parent)

        self.font_metrics = QFontMetrics(self.font())
        self.char_width = self.font_metrics.averageCharWidth()
        self.icon_size = self.parent().icon_size + 6  # add padding

        self.resizeEvent = self.on_resize

    def _getTextSize(self, index, orig_text):
        if self.tabPosition() == QTabWidget.TabPosition.North:
            # button is not present, but pyqt6 reserves the space anyway
            button = self.tabBar().tabButton(index, QTabBar.ButtonPosition.RightSide)
            b_width = 0 if button is None else (button.width() + 12)  # add padding too
            available_width = self.width() - ((self.icon_size + b_width) * self.count())
            target_length = min(len(orig_text), int(available_width / self.count() / self.char_width))
        else:
            target_length = 0 if 0 < index < self.count() - 1 else 1
        return target_length

    def on_resize(self, event):
        super().resizeEvent(event)
        if self.tabPosition() == QTabWidget.TabPosition.North:
            for i in range(1, self.count() - 1):
                orig_text = self.tabWhatsThis(i)
                self.setTabText(i, orig_text)

    def addTab(self, widget, a1, forceSetText=True):
        if forceSetText:
            tabIndex = super().addTab(widget, a1)
            self.setTabText(tabIndex, a1)
        else:
            tabIndex = super().addTab(widget, "")
        self.setTabWhatsThis(tabIndex, a1)
        # force to recalculate all tabs text sizes
        self.resize(self.size())
        return tabIndex

    def insertTab(self, index, widget, a2, forceSetText=True):
        if forceSetText:
            tabIndex = super().insertTab(index, widget, a2)
            self.setTabText(index, a2)
        else:
            tabIndex = super().insertTab(index, widget, "")
        self.setTabWhatsThis(tabIndex, a2)
        # force to recalculate all tabs text sizes
        self.resize(self.size())
        return tabIndex

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
