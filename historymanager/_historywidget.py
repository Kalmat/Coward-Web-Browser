import os.path
import shutil

from PyQt6.QtCore import Qt, QUrl, pyqtSlot, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QAction
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QPushButton, QCheckBox, QScrollArea, QMenu, \
    QStyle, QApplication

from logger import LOGGER, LoggerSettings
from settings import DefaultSettings, Settings
from themes import Themes


class HistoryWidget(QWidget):

    eraseHistorySig = pyqtSignal()

    def __init__(self, parent=None, settings=None, history_manager=None, dialog_manager=None, loadUrlSig=None):
        super(HistoryWidget, self).__init__(parent)

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._settings: Settings = settings
        self.history_manager = history_manager
        self.dialog_manager = dialog_manager
        self.load_url_sig = loadUrlSig

        self.setWindowTitle("Coward - History")
        self.setObjectName("main")
        self.setContentsMargins(0, 0, 0, 0)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("content")
        self.setContentsMargins(0, 0, 0, 0)

        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(5, 3, 0, 0)
        self.content_layout.setSpacing(3)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignVCenter)

        self.scroll = QScrollArea()
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.content_widget)

        self.mainLayout = QGridLayout()
        self.mainLayout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        self.setLayout(self.mainLayout)

        self.init_widget = QWidget()
        self.init_widget.setObjectName("init_widget")
        self.init_widget.setFixedSize(480, 64)
        init_layout = QGridLayout()
        self.init_widget.setLayout(init_layout)

        self.toggle_chk = QCheckBox()
        self.toggle_chk.setText("Disable History" if self._settings.enableHistory else "Enable History")
        self.toggle_chk.setChecked(self._settings.enableHistory)
        self.toggle_chk.stateChanged.connect(self.toggleHistory)
        init_layout.addWidget(self.toggle_chk, 0, 0)

        self.historyEmpty = "No history available yet..."
        self.historyDisabled = "History is disabled"
        self.historyText = "Places visited so far"

        text = self.historyEmpty if self._settings.enableHistory else self.historyDisabled

        self.init_label = QLabel(text)
        self.init_label.setFixedSize(200, 40)
        self.init_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.init_label.setContentsMargins(0, 0, 0, 0)
        # self.init_label.setFixedSize(self._item_width, self._item_height)
        init_layout.addWidget(self.init_label, 0, 1)

        self.eraseHistory_btn = QPushButton("Erase History")
        self.eraseHistory_btn.clicked.connect(self.eraseHistoryRequest)
        init_layout.addWidget(self.eraseHistory_btn, 0, 2)

        init_layout.setColumnStretch(0, 0)
        init_layout.setColumnStretch(1, 1)
        init_layout.setColumnStretch(2, 0)

        self.mainLayout.addWidget(self.init_widget, 0, 0)
        self.mainLayout.addWidget(self.scroll, 1, 0)

        self.mainLayout.setRowStretch(0, 0)
        self.mainLayout.setRowStretch(1, 1)

        # creating a context menu to delete history entry
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.entryContextMenu = QMenu()
        self.entryContextMenu.setMinimumHeight(40)
        self.entryContextMenu.setContentsMargins(0, 5, 0, 0)
        self.delete_action = QAction()
        self.delete_action.setText("Delete this link from history")
        self.delete_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical))
        self.entryContextMenu.setStyleSheet(Themes.styleSheet(DefaultSettings.Theme.defaultTheme, Themes.Section.contextmenu))
        self.entryContextMenu.addAction(self.delete_action)

        self.customContextMenuRequested.connect(self.showContextMenu)
        self.eraseHistorySig.connect(self.eraseHistory)

        self.pendingIcons = {}
        self.loading_ico = QPixmap(DefaultSettings.Icons.loading).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        self._historyWidgets = {}
        for key in self.history_manager.history.keys():
            date = key
            title = self.history_manager.history[key]["title"]
            url = self.history_manager.history[key]["url"]
            icon = self.history_manager.history[key]["icon"]
            self.addHistoryEntry([date, title, url, icon])

    def addHistoryEntry(self, entry):

        self.init_label.setText(self.historyText if self._settings.enableHistory else self.historyDisabled)

        date, title, url, icon = entry

        widget = QWidget()
        widget.setObjectName("item")
        widget.setAccessibleName(str(date))
        widget.setContentsMargins(5, 0, 0, 0)
        widget.setFixedSize(460, 32)
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        entryIcon = QLabel()
        entryIcon.setObjectName("entryIcon")
        iconFile = os.path.basename(icon)
        entryIcon.setAccessibleName(iconFile)
        # entryIcon.setDisabled(True)
        entryIcon.setFixedSize(24, 24)
        if not os.path.exists(icon):
            iconFile = os.path.basename(icon)
            if iconFile in self.pendingIcons.keys():
                self.pendingIcons[iconFile] += [entryIcon]
            else:
                self.pendingIcons[iconFile] = [entryIcon]
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
        self.content_layout.insertWidget(1, widget)

        if not self._settings.enableHistory:
            widget.hide()

        self.update()
        if self.isVisible():
            self.hide()
            self.show()

        if iconFile in self._historyWidgets.keys():
            self._historyWidgets[iconFile] += [widget]
        else:
            self._historyWidgets[iconFile] = [widget]

    def updateHistoryEntry(self, entry):
        date, title, url, icon = entry
        widgets = self._historyWidgets.get(os.path.basename(icon), [])
        for w in widgets:
            w.layout().itemAt(1).widget().setText(title)
            w.setAccessibleName(date)
            w.update()
            if self.isVisible():
                self.hide()
                self.show()

    def updateEntryIcon(self, icon, iconPath):
        pixmap = icon.pixmap(QSize(16, 16))
        if not os.path.exists(iconPath):
            pixmap.save(iconPath, "PNG")
        iconFile = os.path.basename(iconPath)
        entryIcons = self.pendingIcons.get(iconFile, [])
        if entryIcons:
            for entryIcon in entryIcons:
                entryIcon.setPixmap(QPixmap(pixmap))
                entryIcon.update()
            self.pendingIcons.pop(iconFile)
            if self.isVisible():
                self.hide()
                self.show()

    def eraseHistoryRequest(self):
        dialog = self.dialog_manager.createDialog(
            message=DefaultSettings.DialogMessages.eraseHistorylRequest,
            acceptedSlot=self.eraseHistorySig
        )

    def eraseHistory(self):
        self.history_manager.deleteAllHistory()
        self.pendingIcons = {}
        self._historyWidgets = {}
        for i in range(0, self.content_layout.count()):
            w = self.content_layout.itemAt(i).widget()
            w.deleteLater()

    def deleteHistoryEntry(self, checked, point):
        w = self._getWidgetByPosition(point)
        if w:
            key = w.accessibleName()
            if key:
                self.history_manager.deleteHistoryEntry(key)
            self.update()
            if self.isVisible():
                self.hide()
                self.show()
            iconFile = w.layout().itemAt(0).widget().accessibleName()
            self._historyWidgets[iconFile].pop(self._historyWidgets[iconFile].index(w))
            iconPath = os.path.join(self.history_manager.historyFolder, iconFile)
            if os.path.exists(iconPath) and not self._historyWidgets[iconFile]:
                os.remove(iconPath)
            w.deleteLater()

    def loadHistoryEntry(self, url):
        self.load_url_sig.emit(QUrl(url))

    def toggleHistory(self, state):
        enabled = self.toggle_chk.checkState() == Qt.CheckState.Checked
        self.toggle_chk.setChecked(enabled)
        self.toggle_chk.setText("Disable History" if enabled else "Enable History")
        self._settings.setEnableHistory(enabled, persistent=True)
        widgets_count = self.content_layout.count()
        if enabled:
            self.scroll.show()
            self.content_widget.show()
            if widgets_count > 1:
                self.init_label.setText(self.historyText)
            else:
                self.init_label.setText(self.historyEmpty)
        else:
            self.scroll.hide()
            self.content_widget.hide()
            self.init_label.setText(self.historyDisabled)

    def showContextMenu(self, point):
        self.delete_action.triggered.disconnect()
        self.delete_action.triggered.connect(lambda checked, p=point: self.deleteHistoryEntry(checked, p))
        self.entryContextMenu.exec(self.mapToGlobal(point))

    def _getIndexByPosition(self, point):
        index = None
        index = None
        if point.y() > self.init_widget.height():
            index = int((point.y() - self.init_widget.height()) / (32 + 3))
            if index >= self.content_layout.count():
                index = None
        return index

    def _getWidgetByPosition(self, point):
        w = None
        index = self._getIndexByPosition(point)
        if index is not None:
            try:
                w = self.content_layout.itemAt(index).widget()
            except:
                w = None
        return w

    def _getUrlByPosition(self, point):
        url = None
        w = self._getWidgetByPosition(point)
        if w is not None:
            if w:
                url = w.layout().itemAt(1).widget().toolTip()
            else:
                url = None
        return url

    def _getDateByPosition(self, point):
        date = None
        w = self._getWidgetByPosition(point)
        if w is not None:
            if w:
                date = w.layout().itemAt(1).widget().accessibleName()
            else:
                date = ""
        return date

    def mousePressEvent(self, a0):
        if QApplication.mouseButtons() == Qt.MouseButton.LeftButton:
            url = self._getUrlByPosition(a0.pos())
            if url:
                self.load_url_sig.emit(QUrl(url))

    def keyReleaseEvent(self, a0):
        self.parent().keyReleaseEvent(a0)
