from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QPushButton, QLabel, QLineEdit, QHBoxLayout, QWidget

import utils


class SearchWidget(QWidget):

    _width = 300
    _height = 54

    def __init__(self, parent, searchCallback):
        super(SearchWidget, self).__init__(parent)

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)

        self.setFixedSize(self._width, self._height)
        self.setContentsMargins(10, 0, 0, 0)

        self.searchCallback = searchCallback

        # create a horizontal layout
        self.mainLayout = QHBoxLayout()
        self.mainLayout.setContentsMargins(5, 5, 5, 5)
        self.mainLayout.setSpacing(10)
        self.setLayout(self.mainLayout)

        # text box to fill in target search
        self.search_box = QLineEdit()
        self.search_box.setFixedSize(self._width - 100, self._height - 30)
        self.search_box.returnPressed.connect(lambda checked=False, forward=True: self.searchCallback(checked, forward))
        self.mainLayout.addWidget(self.search_box)

        # adding a separator
        separator = QLabel()
        separator.setObjectName("sep")
        separator.setPixmap(QPixmap(utils.resource_path("res/tabsep.png")))
        self.mainLayout.addWidget(separator)

        # search forward button
        self.search_forward = QPushButton("▼")
        font = self.search_forward.font()
        font.setPointSize(font.pointSize() + 10)
        self.search_forward.setFont(font)
        self.search_forward.clicked.connect(lambda checked, forward=True: self.searchCallback(checked, forward))
        self.mainLayout.addWidget(self.search_forward)

        # search backward button
        self.search_backward = QPushButton("▲")
        font = self.search_backward.font()
        font.setPointSize(font.pointSize() + 10)
        font.setPointSize(font.pointSize() + 10)
        self.search_backward.setFont(font)
        self.search_backward.clicked.connect(lambda checked, forward=False: self.searchCallback(checked, forward))
        self.mainLayout.addWidget(self.search_backward)

    def show(self):
        super().show()
        self.activateWindow()
        self.search_box.setFocus()

    def hide(self):
        super().hide()
        self.search_box.setText("")

    def getText(self):
        return self.search_box.text()
