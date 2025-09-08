from queue import Queue

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, pyqtSlot
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QDialogButtonBox

import utils
from settings import DefaultSettings
from themes import Themes
from ._dialog import Dialog


class DialogsManager(QObject):

    _closeSig = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)

        self.appIcon_32 = QPixmap(utils.resource_path(DefaultSettings.Icons.appIcon_32))

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
        icon = icon or self.appIcon_32
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
