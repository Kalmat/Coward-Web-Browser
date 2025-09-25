from queue import Queue

from PyQt6 import sip
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, pyqtSlot, QSize
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QDialogButtonBox

import utils
from settings import DefaultSettings
from themes import Themes
from ._dialog import Dialog


class DialogsManager(QObject):

    _closeSig = pyqtSignal()

    def __init__(self, parent, theme, icon_size, target_dlg_func=None):
        super().__init__(parent)

        self.parent = parent
        self.theme = theme
        self.icon_size = icon_size
        self.targetDlgPos = target_dlg_func
        self.appIcon_32 = QPixmap(utils.resource_path(DefaultSettings.Icons.appIcon_32))

        # enqueue dialogs to avoid showing all at once
        self._dlg_queue = Queue()
        self._dlg_q_timer = QTimer()
        self._dlg_q_timer.timeout.connect(self._showDialogs)
        self.showingDlg = False
        self.currentDialog = None

        # dialogs that can be deleted before be shown
        self._dialogsToDelete = []

        # check when dialogs have been shown or closed to control queue
        self._closeSig.connect(self._dlgClosed)

    @pyqtSlot()
    def _dlgClosed(self):
        # can continue showing dialogs in the queue
        self.showingDlg = False
        self.currentDialog = None

    def createDialog(self, theme=None, icon=None, title=None, message=None, buttonOkOnly=False,
                     acceptedSlot=None, rejectedSlot=None):

        theme = theme or DefaultSettings.Theme.defaultTheme
        if icon is None:
            icon = self.appIcon_32
        elif isinstance(icon, QIcon):
            icon = icon.pixmap(QSize(self.icon_size, self.icon_size))
        icon = icon
        title = title or "Warning!"
        message = message or "Lorem ipsum consectetuer adipisci est"
        buttons = QDialogButtonBox.StandardButton.Ok
        if not buttonOkOnly:
            buttons = buttons | QDialogButtonBox.StandardButton.Cancel
        dialog = Dialog(
                parent=self.parent,
                icon=icon,
                title=title,
                message=message,
                buttons=buttons,
                radius=8,
                getPosFunc=self.targetDlgPos,
                showSig=None,
                closeSig=self._closeSig)
        dialog.setStyleSheet(Themes.styleSheet(theme, Themes.Section.dialog))
        if acceptedSlot is not None:
            if isinstance(acceptedSlot, pyqtSignal):
                dialog.accepted.connect(acceptedSlot.emit)
            else:
                dialog.accepted.connect(acceptedSlot)
        if rejectedSlot is not None:
            if isinstance(rejectedSlot, pyqtSignal):
                dialog.rejected.connect(rejectedSlot.emit)
            else:
                dialog.rejected.connect(rejectedSlot)
        self._queueDialogs(dialog)
        return dialog

    def deleteDialog(self, dialog):
        if dialog not in self._dialogsToDelete:
            if not sip.isdeleted(dialog):
                if dialog.isVisible():
                    dialog.close()
                else:
                    self._dialogsToDelete.append(dialog)

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
                if dialog in self._dialogsToDelete:
                    self._dialogsToDelete.pop(self._dialogsToDelete.index(dialog))
                else:
                    dialog.show()
                    self.currentDialog = dialog
                    self.showingDlg = True
            except:
                # with self._dlg_queue.mutex:
                #     self._dlg_queue.queue.clear()
                pass
