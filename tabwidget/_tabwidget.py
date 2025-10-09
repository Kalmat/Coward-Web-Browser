from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QTabWidget, QTabBar

from settings import DefaultSettings


class TabWidget(QTabWidget):

    def __init__(self, parent):
        super().__init__(parent)

        self.font_metrics = QFontMetrics(self.font())
        self.char_width = self.font_metrics.averageCharWidth()
        self.min_tab_width = self.parent().h_tab_size

        # this has no effect. Solved in qss (width: 0px)
        # self.setUsesScrollButtons(False)

        self.resizeEvent = self.on_resize

    def _getTextSize(self, index):
        if self.tabPosition() == QTabWidget.TabPosition.North:
            # button is not present, but pyqt6 reserves the space anyway
            button = self.tabBar().tabButton(index, QTabBar.ButtonPosition.RightSide)
            b_width = 8 if button is None else (button.width() + 6)  # add button padding
            available_width = max(0, self.width() - ((self.min_tab_width + b_width) * self.count()))
            label_width = available_width / self.count()
            if label_width < DefaultSettings.Tabs.maxWidth - (self.min_tab_width + b_width):
                target_length = int(label_width / self.char_width)
            else:
                target_length = len(self.tabText(index))
        else:
            target_length = 0 if 0 < index < self.count() - 1 else 1
        return target_length

    def on_resize(self, event=None):
        if event is not None:
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
        self.on_resize()
        return tabIndex

    def insertTab(self, index, widget, a2, forceSetText=True):
        if forceSetText:
            tabIndex = super().insertTab(index, widget, a2)
            self.setTabText(index, a2)
        else:
            tabIndex = super().insertTab(index, widget, "")
        self.setTabWhatsThis(tabIndex, a2)
        # force to recalculate all tabs text sizes
        self.on_resize()
        return tabIndex

    def removeTab(self, index):
        super().removeTab(index)
        # force to recalculate all tabs text sizes
        self.on_resize()

    def setTabText(self, index, a1):
        target_text = a1
        if 0 < index < self.count() - 1:
            target_length = self._getTextSize(index)
            target_text = a1[:target_length] + (" " * max(0, (target_length - len(a1))))
        super().setTabText(index, target_text)

    def setCurrentIndex(self, index):
        index = max(1, min(index, self.count() - 2))
        super().setCurrentIndex(index)

    def keyPressEvent(self, a0):
        pass

    def keyReleaseEvent(self, a0):
        self.parent().keyReleaseEvent(a0)
