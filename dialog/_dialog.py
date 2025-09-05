import os
from queue import Queue

from PyQt6.QtCore import QPoint, Qt, QUrl, QTimer, pyqtSignal, pyqtSlot, QObject
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import QDialog, QWidget, QLabel, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QGridLayout

import utils
from settings import DefaultSettings
from themes import Themes


class Dialog(QDialog):

    def __init__(self, parent, icon, title, message, buttons, radius, getPosFunc=None, showSig=None, closeSig=None):
        super().__init__(parent)

        self._showSig = showSig
        self._closeSig = closeSig
        self._getPosFunc = getPosFunc

        self.radius = radius

        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(utils.resource_path("res/coward.png")))

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        if getPosFunc is not None:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint | Qt.WindowType.FramelessWindowHint)

        self.setContentsMargins(0, 0, 0, 0)

        self.widget = QWidget(self)
        self.widget.setContentsMargins(0, 0, 0, 0)

        self.icon = QLabel()
        self.icon.setObjectName("header")
        self.icon.setFixedSize(32, 32)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon is None:
            icon = QPixmap(utils.resource_path(DefaultSettings.App.appIcon_32))
        self.icon.setPixmap(icon)

        self.title = QLabel()
        self.title.setObjectName("header")
        if not title:
            title = "Coward"
        self.title.setText(title)

        self.init_message = message
        self.message = QLabel(message or "Lorem ipsum consectetuer adipisci est")
        self.message.setObjectName("body")
        self.message.setContentsMargins(25, 20, 25, 25)
        self.message.setMinimumWidth(400)
        self.message.setMaximumWidth(500)
        self.message.setWordWrap(True)

        self.title.setMinimumWidth(self.message.minimumWidth() - self.icon.width())
        self.title.setMaximumWidth(self.message.maximumWidth() - self.icon.width())

        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.setContentsMargins(0, 10, 0, 0)

        layout = QGridLayout()
        layout.setSpacing(5)
        layout.addWidget(self.icon, 0, 0)
        layout.addWidget(self.title, 0, 1)
        layout.addWidget(self.message, 1, 0, 1, 2)
        layout.addWidget(self.buttonBox, 2, 0, 1, 2)
        self.widget.setLayout(layout)

        self.mainLayout = QHBoxLayout()
        self.mainLayout.addWidget(self.widget)
        self.setLayout(self.mainLayout)

        filename = utils.resource_path(DefaultSettings.Sounds.dialogInformation)
        self.effect = QSoundEffect()
        self.effect.setSource(QUrl.fromLocalFile(filename))
        self.effect.setVolume(0.7)

    def show(self):
        super().show()
        if self._getPosFunc is not None:
            self.move(self._getPosFunc())
        self.effect.play()
        if self._showSig is not None:
            self._showSig.emit()

    def move(self, position, y=None):
        if y is not None:
            position = QPoint(position, y)
        super().move(QPoint(position.x(), position.y() - self.radius - 4))

    def accept(self):
        super().accept()
        if self._closeSig is not None:
            self._closeSig.emit()

    def reject(self):
        super().reject()
        if self._closeSig is not None:
            self._closeSig.emit()


class DialogsManager(QObject):

    _closeSig = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)

        # enqueue dialogs to avoid showing all at once
        self._dlg_queue = Queue()
        self._dlg_q_timer = QTimer()
        self._dlg_q_timer.timeout.connect(self._showDialogs)
        self.showingDlg = False
        self.currentDialog = None

        # check when dialogs have been shown or closed to control queue
        self._closeSig.connect(self._dlgClosed)

    @pyqtSlot()
    def _dlgClosed(self):
        # can continue showing dialogs in the queue
        self.showingDlg = False
        self.currentDialog = None

    def createDialog(self, parent, theme=None, icon=None, title=None, message=None, buttons=None,
                     getPosFunc=None, acceptedSlot=None, rejectedSlot=None):
        theme = theme or DefaultSettings.Theme.defaultTheme
        icon = icon or QIcon(utils.resource_path(DefaultSettings.Icons.appIcon))
        title = title or "Warning!"
        message = message or "Lorem ipsum consectetuer adipisci est"
        buttons = buttons or (QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        dialog = Dialog(parent,
                        icon=icon,
                        title=title,
                        message=message,
                        buttons=buttons,
                        radius=8,
                        getPosFunc=getPosFunc,
                        showSig=None,
                        closeSig=self._closeSig)
        dialog.setStyleSheet(Themes.styleSheet(theme, Themes.Section.dialog))
        if acceptedSlot is not None:
            dialog.accepted.connect(acceptedSlot)
        if rejectedSlot is not None:
            dialog.rejected.connect(rejectedSlot)
        self._queueDialogs(dialog)

    def _queueDialogs(self, dialog):
        self._dlg_queue.put_nowait(dialog)
        if not self._dlg_q_timer.isActive():
            self._dlg_q_timer.start(300)

    def _showDialogs(self):

        if self._dlg_queue.empty():
            self._dlg_q_timer.stop()

        elif not self.showingDlg:
            try:
                dialog = self._dlg_queue.get_nowait()
                dialog.show()
                self.currentDialog = dialog
                self.showingDlg = True
            except:
                with self._dlg_queue.mutex:
                    self._dlg_queue.queue.clear()
