import os.path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QPushButton

from historymanager import History
from settings import DefaultSettings


class HistoryWidget(QWidget):

    def __init__(self, parent=None, history_manager=None, loadUrlSig=None):
        super(HistoryWidget, self).__init__(parent)

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)

        self.history_manager: History = history_manager
        self.load_url_sig = loadUrlSig

        self.setWindowTitle("Coward - History")
        self.setObjectName("main")
        self.setContentsMargins(0, 0, 0, 0)

        self.mainLayout = QVBoxLayout()
        self.mainLayout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(3)
        self.setLayout(self.mainLayout)

        self.init_label = QLabel("No history stored yet...")
        self.init_label.setFixedSize(400, 40)

        self.init_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.init_label.setContentsMargins(0, 0, 0, 0)
        # self.init_label.setFixedSize(self._item_width, self._item_height)
        self.mainLayout.addWidget(self.init_label)

        self.pendingIcons = {}
        self.loading_ico = QPixmap(DefaultSettings.Icons.loading).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        for key in self.history_manager.history.keys():
            date = key
            title = self.history_manager.history[key]["title"]
            url = self.history_manager.history[key]["url"]
            icon = self.history_manager.history[key]["icon"]
            self.addHistoryEntry([date, title, url, icon])

    def addHistoryEntry(self, entry):

        self.init_label.setText("Places visited so far")

        date, title, url, icon = entry

        widget = QWidget()
        widget.setObjectName("item")
        widget.setContentsMargins(5, 0, 0, 0)
        widget.setFixedSize(400, 32)
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        entryIcon = QLabel()
        entryIcon.setObjectName("entryIcon")
        # entryIcon.setDisabled(True)
        entryIcon.setFixedSize(24, 24)
        if not os.path.exists(icon):
            self.pendingIcons[icon] = entryIcon
            icon = self.loading_ico
        entryIcon.setPixmap(QPixmap(icon))
        layout.addWidget(entryIcon, 0, 0)

        entryText = QLabel()
        entryText.setObjectName("entryText")
        entryText.setContentsMargins(5, 0, 0, 0)
        entryText.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        entryText.setFixedSize(400, 32)
        entryText.setText(title)
        entryText.setToolTip(url)
        layout.addWidget(entryText, 0, 1)

        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(1, 1)

        widget.setLayout(layout)
        self.mainLayout.insertWidget(1, widget)

        self.update()
        if self.isVisible():
            self.hide()
            self.show()

    def updateEntryIcon(self, icon):
        entryIcon = self.pendingIcons.get(icon, None)
        if entryIcon is not None:
            entryIcon.setPixmap(QPixmap(icon))
            entryIcon.update()
            self.hide()
            self.show()


    def loadUrl(self, url):
        self.load_url_sig.emit(QUrl(url))

    def mousePressEvent(self, a0):
        index = int((a0.pos().y() - self.init_label.height()) / (32 + 3))
        try:
            url = self.layout().itemAt(index + 1).widget().layout().itemAt(1).widget().toolTip()
        except:
            url = ""
        if url:
            self.loadUrl(url)

    def keyReleaseEvent(self, a0):

        if a0.key() == Qt.Key.Key_H:
            if self.isVisible():
                self.hide()
