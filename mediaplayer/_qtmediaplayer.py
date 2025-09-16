import os
import time

from PyQt6.QtNetwork import QUdpSocket, QHostAddress
from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QSlider, QGraphicsScene, QGraphicsView
from PyQt6.QtGui import QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import Qt, QUrl, QTimer, pyqtSignal, QByteArray, QThread, QBuffer, QIODevice, pyqtSlot
from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem

from settings import DefaultSettings
from themes import Themes

os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'windowsmediafoundation'


class QtMediaPlayer(QWidget):

    swapTempAvailableSig = pyqtSignal()
    streamStartedSig = pyqtSignal(object)

    def __init__(self, title="Coward - Stream Player", url="", useFFmpeg=False, closedSig=None):
        super().__init__()

        self.url = url
        self.useFFmpeg = useFFmpeg

        # manage input temporary files
        self.temp_file = QUrl.fromLocalFile(DefaultSettings.Player.streamTempFile)
        self.next_temp_file = QUrl.fromLocalFile(DefaultSettings.Player.streamTempFile_2)
        self.prev_temp_file = ""

        self.swapTempAvailableSig.connect(self.manage_swap)
        self.swapAvailable = True

        self.streamStartedSig.connect(self.onMediaStarted)
        self.stream_process = None

        # buffer size
        self.buffer_size = DefaultSettings.Player.bufferSize

        # buffering video
        self.loading_video = QUrl.fromLocalFile(DefaultSettings.Media.bufferingVideo)

        # emit signal when closed
        self.closedSig = closedSig
        self.userClosed = True

        self.setGeometry(200, 200, 700, 400)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(DefaultSettings.Icons.appIcon_32))
        self.setStyleSheet(Themes.styleSheet(DefaultSettings.Theme.defaultTheme, Themes.Section.mediaplayer))

        self.mediaplayer = QMediaPlayer()
        self.audio = QAudioOutput()
        self.audio.setVolume(0.5)
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.video_item = QGraphicsVideoItem()
        # self.view.fitInView(self.video_item, Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        # self.view.setFrameShape(0) # no borders
        # self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scene.addItem(self.video_item)

        # btn for playing
        self.playBtn = QPushButton()
        self.playText = "▶️"
        self.pauseText = "⏸️"
        self.playBtn.setText(self.pauseText)
        self.playBtn.clicked.connect(self.togglePlayPause)

        # slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, self.buffer_size)

        hbox = QHBoxLayout()
        hbox.addWidget(self.playBtn)
        hbox.addWidget(self.slider)

        vbox = QVBoxLayout()
        vbox.addWidget(self.view)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        self.mediaplayer.setVideoOutput(self.video_item)
        self.mediaplayer.setAudioOutput(self.audio)

        # media player signals
        self.mediaplayer.mediaStatusChanged.connect(self.mediastate_changed)
        self.video_item.nativeSizeChanged.connect(self.resizeAll)

    def show(self):
        super().show()
        self.wGap = self.width() - int(self.view.size().width())
        self.hGap = self.height() - int(self.view.size().height())

    def start(self):
        self.play_loading_video()
        if self.useFFmpeg:
            # self.play_video_ffmpeg()
            # give time for the stream to start
            # QTimer.singleShot(3000, self.play_video_ffmpeg)
            pass

        else:
            self.play_loading_video()
            self.play_video()

    def play_loading_video(self):
        self.playBtn.setDisabled(True)
        self.mediaplayer.setSource(self.loading_video)
        self.mediaplayer.setLoops(QMediaPlayer.Loops.Infinite)
        self.mediaplayer.play()

    @pyqtSlot(object)
    def onMediaStarted(self, stream_process):
        self.stream_process = stream_process
        QTimer().singleShot(1000, self.play_video_ffmpeg)

    def play_video_ffmpeg(self):
        self.playBtn.setEnabled(True)
        self.playBtn.setText(self.pauseText)
        self.slider.setRange(0, self.mediaplayer.duration())
        self.mediaplayer.positionChanged.connect(self.position_changed)
        self.mediaplayer.durationChanged.connect(self.duration_changed)
        self.mediaplayer.setLoops(1)
        self.mediaplayer.stop()
        self.mediaplayer.setSource(QUrl())
        time.sleep(.01)
        # Read directly from udp (not working) or buffered (not working either)
        # self.mediaplayer.setSource(QUrl(DefaultSettings.Player.ffmpegStreamUrl))
        self.setBuffer()
        QTimer().singleShot(1000, self.mediaplayer.play)

    def setBuffer(self):

        self.byte_array = QByteArray()
        self.buffer = QBuffer(self.byte_array)
        self.buffer.setOpenMode(QIODevice.OpenModeFlag.ReadWrite)
        self.mediaplayer.setSourceDevice(self.buffer)

        if self.stream_process is None:
            # read from UDP port
            self.udp_receiver = UdpReceiver(self.buffer, self.byte_array)
            self.udp_receiver.start()

        else:
            self.stdout_receiver = StdoutReceiver(self.stream_process, self.buffer, self.byte_array)
            self.stdout_receiver.start()

    def play_video(self):

        # wait until cache stream file exits and has a reasonable size (20Mb)
        if (os.path.exists(self.temp_file.fileName()) and
                os.path.getsize(self.temp_file.fileName()) > self.buffer_size and
                self.swapAvailable):
            # control if EOF means changing temp file or stalled (must be managed in webpage class, passed by streamer class)
            # self.swapAvailable = False
            self.playBtn.setEnabled(True)
            self.playBtn.setText(self.pauseText)
            self.slider.setRange(0, self.mediaplayer.duration())
            self.mediaplayer.positionChanged.connect(self.position_changed)
            self.mediaplayer.durationChanged.connect(self.duration_changed)
            self.mediaplayer.setLoops(1)
            self.mediaplayer.stop()
            self.mediaplayer.setSource(QUrl())
            time.sleep(.01)
            self.mediaplayer.setSource(self.temp_file)
            self.mediaplayer.play()

        else:
            if os.path.exists(self.temp_file.fileName()):
                self.updateSlider(os.path.getsize(self.temp_file.fileName()), self.buffer_size)
            QTimer.singleShot(300, self.play_video)

    def resizeAll(self, size):
        self.video_item.setSize(size)
        self.resize(int(size.width()) + self.wGap, int(size.height()) + self.hGap)

    def manage_swap(self):
        self.swapAvailable = True

    def togglePlayPause(self):
        # MANAGE PAUSE at streamer level, avoiding writing,
        # thus skipping all content when in pause and coming back to live when playing again

        if self.mediaplayer.mediaStatus == QMediaPlayer.PlaybackState.PlayingState:
            self.playBtn.setText(self.playText)
            self.mediaplayer.pause()
        elif self.mediaplayer.mediaStatus == QMediaPlayer.PlaybackState.PausedState:
            self.playBtn.setText(self.pauseText)
            self.mediaplayer.play()

    def position_changed(self, position):
        self.slider.setValue(position)

    def duration_changed(self, duration):
        self.slider.setRange(0, duration)

    def updateSlider(self, progress, total):
        self.slider.setValue(progress)

    def mediastate_changed(self):

        if self.mediaplayer.mediaStatus() == QMediaPlayer.PlaybackState.PlayingState:
            self.playBtn.setText(self.pauseText)
            self.playBtn.setEnabled(True)

        elif self.mediaplayer.mediaStatus() == QMediaPlayer.PlaybackState.PausedState:
            self.playBtn.setText(self.playText)
            self.playBtn.setEnabled(True)

        elif self.mediaplayer.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
            # also check if streamer is alive
            self.prev_temp_file = self.temp_file
            self.temp_file = self.next_temp_file
            self.next_temp_file = self.prev_temp_file
            self.mediaplayer.setSource(self.temp_file)
            self.play_video()

        else:
            # self.playBtn.setDisabled(True)
            pass

    def stop(self):
        self.mediaplayer.stop()
        self.mediaplayer.setSource(QUrl())

    def close(self):
        self.userClosed = False
        super().close()

    def closeEvent(self, a0):
        self.mediaplayer.stop()
        if self.closedSig is not None and self.userClosed:
            self.closedSig.emit(self.url)


class UdpReceiver(QThread):

    def __init__(self, buffer, byte_array):
        super().__init__()

        self.stopReading = False

        self.buffer = buffer
        self.byte_array = byte_array
        self.socket = QUdpSocket()
        self.socket.bind(QHostAddress.SpecialAddress.Any, 5000)  # Bind to port 5000

    def run(self):
        self.process_data()
        # self.socket.readyRead.connect(self.process_data)

    def process_data(self):

        # max_size = 5 * 1024 * 1024  # 5 MB

        while not self.stopReading:

            while self.socket.hasPendingDatagrams():

                print("READING")
                datagram, sender, port = self.socket.readDatagram(self.socket.pendingDatagramSize())
                if not datagram:
                    print("NO DATA")
                    break

                self.byte_array.append(datagram)  # Store the received data in QByteArray

                # if self.buffer.size() > max_size:
                #     # Resize the QByteArray to the maximum size
                #     self.media_data = self.media_data.mid(0, max_size)

                # Write the data to the QBuffer
                # self.buffer.write(self.byte_array)
                # self.buffer.seek(0)  # Reset the buffer position to the beginning

    def stop(self):
        self.stopReading = True
        self.quit()


class StdoutReceiver(QThread):

    def __init__(self, stream_process, buffer, byte_array):
        super().__init__()

        self.stopReading = False

        self.stream_process = stream_process
        self.buffer = buffer
        self.byte_array = byte_array

    def run(self):

        while not self.stopReading:

            print("READING")
            # Read data from FFmpeg's stdout
            data = self.stream_process.stdout.read(8192)
            if not data:
                print("NO DATA")
                break  # Exit if no more data

            # Append data to QByteArray
            self.byte_array.append(data)

        self.stream_process.stdout.close()
        self.stream_process.wait()

    def stop(self):
        self.stopReading = True
        self.quit()
