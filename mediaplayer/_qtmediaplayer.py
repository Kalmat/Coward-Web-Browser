import os

from PyQt6.QtWidgets import QWidget, QPushButton, \
                            QHBoxLayout, QVBoxLayout, QStyle, QSlider
from PyQt6.QtGui import QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import Qt, QUrl, QTimer, QFile, QIODevice, QBuffer
from PyQt6.QtMultimediaWidgets import QVideoWidget

import utils
from settings import DefaultSettings

os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'windowsmediafoundation'


class QtMediaPlayer(QWidget):

    def __init__(self, stream_file="temp.mp4", title="Coward - Media Player", closedSig=None):
        super().__init__()

        self.stream_file = stream_file
        self.closedSig = closedSig

        self.setGeometry(200, 200, 700, 400)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(DefaultSettings.Icons.appIcon_32))
        self.setStyleSheet("background: #323232;")

        self.mediaplayer = QMediaPlayer()
        self.audio = QAudioOutput()

        videowidget = QVideoWidget()

        # btn for playing
        self.playBtn = QPushButton()
        self.playBtn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.playBtn.clicked.connect(self.togglePlayPause)

        # buffer size
        self.buffer_size = 20 * 1000 * 1000

        # slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, self.buffer_size)

        hbox = QHBoxLayout()

        # hbox.addWidget(openBtn)
        hbox.addWidget(self.playBtn)
        hbox.addWidget(self.slider)

        vbox = QVBoxLayout()

        vbox.addWidget(videowidget)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        self.mediaplayer.setVideoOutput(videowidget)
        self.mediaplayer.setAudioOutput(self.audio)

        # media player signals
        self.mediaplayer.mediaStatusChanged.connect(self.mediastate_changed)

    def start(self):
        self.play_loading_video()
        self.play_video()

    def togglePlayPause(self):
        print("TOGGLE")

        if self.mediaplayer.mediaStatus == QMediaPlayer.PlaybackState.PlayingState:
            self.playBtn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.mediaplayer.pause()
        else:
            self.playBtn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.mediaplayer.play()

    def play_loading_video(self):
        self.playBtn.setDisabled(True)
        self.mediaplayer.setSource(QUrl.fromLocalFile(utils.resource_path(DefaultSettings.Media.bufferingVideo)))
        self.mediaplayer.setLoops(QMediaPlayer.Loops.Infinite)
        self.mediaplayer.play()

    def position_changed(self, position):
        self.slider.setValue(position)

    def duration_changed(self, duration):
        self.slider.setRange(0, duration)

    def updateSlider(self, progress, total):
        self.slider.setValue(progress)

    def play_video(self):

        # wait until cache stream file exits and has a reasonable size (20Mb)
        if os.path.exists(self.stream_file) and os.path.getsize(self.stream_file) > self.buffer_size:
            self.playBtn.setEnabled(True)
            self.playBtn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.slider.setRange(0, self.mediaplayer.duration())
            self.mediaplayer.positionChanged.connect(self.position_changed)
            self.mediaplayer.durationChanged.connect(self.duration_changed)
            self.mediaplayer.pause()
            self.mediaplayer.setLoops(1)
            self.mediaplayer.setSource(QUrl.fromLocalFile(self.stream_file))
            # self.set_buffer()
            self.mediaplayer.play()

        else:
            if os.path.exists(self.stream_file):
                self.updateSlider(os.path.getsize(self.stream_file), self.buffer_size)
            QTimer.singleShot(300, self.play_video)

    def set_buffer(self):
        """Opens a single video file and writes it to a buffer to be read by QMediaPlayer"""

        # buffer for streaming
        self.buffer = QBuffer
        media_file_name = os.path.abspath(self.stream_file)
        media_file = QFile(media_file_name)
        media_file.open(QIODevice.OpenModeFlag.ReadOnly)
        print(f"The size of buffer before adding the byte_array is: {self.buffer.size()}")
        self.byte_array = media_file.readAll()
        self.buffer.setData(self.byte_array)
        self.buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        print(f"The size of buffer after adding the byte_array is: {self.buffer.size()}")
        self.mediaplayer.setSourceDevice(self.buffer)

    def mediastate_changed(self):

        if self.mediaplayer.mediaStatus() == QMediaPlayer.PlaybackState.PlayingState:
            self.playBtn.setIcon(
                self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
            )
            self.playBtn.setEnabled(True)

        elif self.mediaplayer.mediaStatus() == QMediaPlayer.PlaybackState.PausedState:
            self.playBtn.setIcon(
                self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
            )
            self.playBtn.setEnabled(True)

        elif self.mediaplayer.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
            # try to wait to buffer more media
            pass

        else:
            self.playBtn.setDisabled(True)

    def closeEvent(self, a0):
        self.mediaplayer.stop()
        if self.closedSig is not None:
            self.closedSig.emit()

    def stop(self):
        self.mediaplayer.stop()
