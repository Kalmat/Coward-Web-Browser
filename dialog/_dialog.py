import os

from PyQt6.QtCore import QPoint, Qt, QUrl
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import QDialog, QWidget, QLabel, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QGridLayout

import utils
from settings import DefaultSettings


class Dialog(QDialog):

    def __init__(self, parent, icon=None, title="", message="", buttons=None, pos_offset=None, radius=0):
        super().__init__(parent)

        self.pos_offset = QPoint(pos_offset.x(), pos_offset.y() - radius * 2) if pos_offset is not None else None
        self.radius = radius

        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(utils.resource_path("res/coward.png")))

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
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

        self.buttonBox = QDialogButtonBox(buttons or (QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel))
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
        self.effect.play()

    def move(self, position, y=None):
        if y is not None:
            position = QPoint(position, y)
        super().move(QPoint(position.x(), position.y() - self.radius - 4))

    def setMessage(self, new_message):
        self.message.setText(new_message)

    def getInitMessage(self):
        return self.init_message

    def getCurrentMessage(self):
        return self.message.text()
