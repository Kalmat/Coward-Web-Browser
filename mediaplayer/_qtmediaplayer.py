import os
import time

from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QSlider, QGraphicsScene, QGraphicsView
from PyQt6.QtGui import QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import Qt, QUrl, QTimer, pyqtSignal
from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem

from settings import DefaultSettings
from themes import Themes

os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'windowsmediafoundation'


class QtMediaPlayer(QWidget):

    swapTempAvailableSig = pyqtSignal()

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
            QTimer.singleShot(3000, self.play_video_ffmpeg)

        else:
            self.play_loading_video()
            self.play_video()

    def play_loading_video(self):
        self.playBtn.setDisabled(True)
        self.mediaplayer.setSource(self.loading_video)
        self.mediaplayer.setLoops(QMediaPlayer.Loops.Infinite)
        self.mediaplayer.play()

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
        self.mediaplayer.setSource(QUrl(DefaultSettings.Player.ffmpegStreamUrl))
        self.mediaplayer.play()
        # self.play_stream()

    # def play_stream(self):
    #
    #     self.udp_address = ('127.0.0.1', 5000)  # Replace with your UDP address and port
    #
    #     self.byte_array = QByteArray()
    #     self.buffer.setData(self.byte_array)
    #
    #     self.stream_thread = threading.Thread(target=lambda u=self.ffmpeg_process, b=self.byte_array: self.fetch_stream_data(u, b))
    #     self.stream_thread.start()
    #
    #     # Fetch the stream data
    #     # self.fetch_stream_data(self.udp_address, self.byte_array)
    #
    #     # Cache the stream data in the buffer
    #     self.buffer.open(QBuffer.OpenModeFlag.ReadOnly)
    #
    #     # Set the source device to the player
    #     self.mediaplayer.setSourceDevice(self.buffer)
    #
    #     # Start playback
    #     self.mediaplayer.play()
    #
    # def fetch_stream_data(self, udp_address, byte_array):
    #     try:
    #         # Create a UDP socket
    #         # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #         # sock.bind(udp_address)  # Bind to the UDP address
    #         stdout, stderr = udp_address().communicate()
    #
    #         print("Listening for UDP stream...")
    #
    #         max_buffer_size = 1024 * 1024 * 50  # Example: 10 MB
    #         while not self.stopStreaming:
    #             # Receive data from the UDP stream
    #             # data, _ = sock.recvfrom(1024 * 1024)  # Buffer size is 2048 bytes
    #             data = stdout.read(2048)
    #             byte_array.append(data)
    #
    #             # Manage buffer size
    #             if byte_array.size() > max_buffer_size:
    #                 # Remove old data to keep the buffer size manageable
    #                 byte_array.remove(0, byte_array.size() - max_buffer_size)
    #
    #     except Exception as e:
    #         print(f"Error fetching stream data: {e}")

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
            # self.mediaplayer.setSource("udp://127.0.0.1:5000")
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
