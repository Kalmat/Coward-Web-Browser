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

    def _getTextSize(self, index, title):
        padding_length = 0
        if 0 < index < self.count() - 1:
            if self.tabPosition() == QTabWidget.TabPosition.North:
                # button is not present, but pyqt6 reserves the space anyway
                button = self.tabBar().tabButton(index, QTabBar.ButtonPosition.RightSide)
                b_width = (0 if button is None else button.width()) + 8  # add button padding
                available_width = max(0, self.width() - ((self.min_tab_width + b_width) * self.count()))
                label_width = min(DefaultSettings.Tabs.maxWidth - b_width, available_width / self.count())
                title_width = len(title) * self.char_width
                if label_width < title_width:
                    target_length = int(label_width / self.char_width)
                else:
                    target_length = len(title)
                    padding_length = max(0, int((label_width - title_width) / self.char_width))
            else:
                target_length = 0
        else:
            target_length = len(title)
        return target_length, padding_length

    def resizeEvent(self, a0=None):
        if a0 is not None:
            super().resizeEvent(a0)
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
        self.resizeEvent()
        return tabIndex

    def insertTab(self, index, widget, a2, forceSetText=True):
        if forceSetText:
            tabIndex = super().insertTab(index, widget, a2)
            self.setTabText(index, a2)
        else:
            tabIndex = super().insertTab(index, widget, "")
        self.setTabWhatsThis(tabIndex, a2)
        # force to recalculate all tabs text sizes
        self.resizeEvent()
        return tabIndex

    def removeTab(self, index):
        super().removeTab(index)
        # force to recalculate all tabs text sizes
        self.resizeEvent()

    def setTabText(self, index, a1):
        target_text = a1
        if 0 < index < self.count() - 1:
            target_length, padding = self._getTextSize(index, a1)
            target_text = a1[:target_length] + (" " * padding)
        super().setTabText(index, target_text)

    def setCurrentIndex(self, index):
        index = max(1, min(index, self.count() - 2))
        super().setCurrentIndex(index)

    def keyPressEvent(self, a0):
        pass

    def keyReleaseEvent(self, a0):
        self.parent().keyReleaseEvent(a0)
