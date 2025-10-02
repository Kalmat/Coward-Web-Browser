import os.path

from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QSize, pyqtSlot
from PyQt6.QtGui import QPixmap, QAction
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QPushButton, QCheckBox, QScrollArea, QMenu, QStyle

from settings import DefaultSettings, Settings
from themes import Themes


class HistoryWidget(QWidget):

    eraseHistorySig = pyqtSignal()
    widgetClickedSig = pyqtSignal(Qt.MouseButton, QWidget)

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
        self.widgetClickedSig.connect(self.onWidgetClicked)
        self.widgetClicked = None
        self.eraseHistorySig.connect(self.eraseHistory)

        self.pendingTitles = {}
        self.pendingIcons = {}
        self.loading_ico = QPixmap(DefaultSettings.Icons.loading).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        for url in self.history_manager.history.keys():
            date = self.history_manager.history[url]["date"]
            title = self.history_manager.history[url]["title"]
            icon = self.history_manager.history[url]["icon"]
            self.addHistoryEntry([date, title, url, icon])

    def addHistoryEntry(self, entry):

        self.init_label.setText(self.historyText if self._settings.enableHistory else self.historyDisabled)

        date, title, url, icon = entry

        widget = Widget(None, self.widgetClickedSig)
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
        self.pendingTitles[url] = entryText
        layout.addWidget(entryText, 0, 1)

        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(1, 1)

        widget.setLayout(layout)
        self.content_layout.insertWidget(0, widget)

        if not self._settings.enableHistory:
            widget.hide()

        self.update()
        if self.isVisible():
            self.hide()
            self.show()

    def updateEntryTitle(self, title, url):
        entryText = self.pendingTitles.get(url, None)
        if entryText is not None:
            entryText.setText(title)
            entryText.update()
            if self.isVisible():
                self.hide()
                self.show()
            # can not delete pendingTitles item since this can be invoked several times
            # this below serves to control repeated entries for different URLs (typically generated by the website)
            self.history_manager.updateHistoryEntry(url, title=title)

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
            del self.pendingIcons[iconFile]
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
        self.pendingTitles = {}
        for i in range(0, self.content_layout.count()):
            w = self.content_layout.itemAt(i).widget()
            w.deleteLater()

    @pyqtSlot(Qt.MouseButton, QWidget)
    def onWidgetClicked(self, button, widget):
        if button == Qt.MouseButton.LeftButton:
            # load URL stored in history entry
            url = widget.layout().itemAt(1).widget().toolTip()
            if url:
                self.load_url_sig.emit(QUrl(url))

        elif button == Qt.MouseButton.RightButton:
            # save clicked widget in case user selects "delete entry" in context menu
            self.widgetClicked = widget

    def deleteHistoryEntryByPos(self, checked):
        if self.widgetClicked is not None:
            url = self.widgetClicked.layout().itemAt(1).widget().toolTip()
            if url:
                self.history_manager.deleteHistoryEntryByUrl(url)
            self.update()
            if self.isVisible():
                self.hide()
                self.show()
            self.widgetClicked.deleteLater()

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
        self.delete_action.triggered.connect(self.deleteHistoryEntryByPos)
        self.entryContextMenu.exec(self.mapToGlobal(point))


class Widget(QWidget):

    def __init__(self, parent=None, clickedSig=None):
        super(Widget, self).__init__(parent)

        self.clickedSig = clickedSig

    def mousePressEvent(self, a0):
        pass

    def mouseReleaseEvent(self, a0):
        self.clickedSig.emit(a0.button(), self)
