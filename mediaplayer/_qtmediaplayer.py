import os
import subprocess
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

    streamStartedSig = pyqtSignal(subprocess.Popen, QUrl)

    def __init__(self, title, url, player_type, index=0, closedSig=None):
        super().__init__()

        self.title = title
        self.url = url
        self.playerType = player_type
        self.firstRun = True

        # manage input temporary files
        self.stream_files = [os.path.normpath(os.path.join(DefaultSettings.App.tempFolder,
                                                           DefaultSettings.Player.streamTempFolder,
                                                           str(index), temp_file))
                                    for temp_file in DefaultSettings.Player.streamTempFiles]
        self.stream_file_index = 0

        # set udp / stdout stream values
        self.streamStartedSig.connect(self.onMediaStarted)
        self.stream_process = None
        self.udpHost = None
        self.udpPort = None
        self.udp_receiver = None
        self.stdout_receiver = None

        # buffer size
        self.buffer_size = DefaultSettings.Player.bufferSize

        # buffering video
        self.loading_video = QUrl.fromLocalFile(DefaultSettings.Media.bufferingVideo)

        # emit signal when closed
        self.closedSig = closedSig
        self.userClosed = True

        # configure window
        self.setGeometry(200, 200, 700, 400)
        self.setWindowTitle(title + " / " + str(self.stream_file_index))
        self.setWindowIcon(QIcon(DefaultSettings.Icons.appIcon_32))
        self.setStyleSheet(Themes.styleSheet(DefaultSettings.Theme.defaultTheme, Themes.Section.mediaplayer))

        # create mediaplayer
        self.mediaplayer = QMediaPlayer()
        self.audio = QAudioOutput()
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.video_item = QGraphicsVideoItem()
        self.view.fitInView(self.video_item, Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        # self.view.setFrameShape(0) # no borders
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scene.addItem(self.video_item)

        # btn for play / pause
        self.playBtn = QPushButton()
        self.playText = "▶️"
        self.pauseText = "⏸️"
        self.playBtn.setText(self.pauseText)
        self.playBtn.clicked.connect(self.togglePlayPause)

        # slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, self.buffer_size)

        # btn for mute / unmute
        self.muteBtn = QPushButton()
        self.muteText = "🔇"
        self.nomuteText = "🕪"
        self.muteBtn.setText(self.nomuteText)
        self.muteBtn.clicked.connect(self.toggleMute)

        hbox = QHBoxLayout()
        hbox.addWidget(self.playBtn)
        hbox.addWidget(self.slider)
        hbox.addWidget(self.muteBtn)

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
        if self.playerType in (DefaultSettings.Player.PlayerTypes.qt_ffmpeg_Udp, DefaultSettings.Player.PlayerTypes.qt_ffmpeg_Stdout):
            # can't play media until stream is started (by onMediaStarted signal)
            pass

        else:
            self.play_loading_video()
            self.play_video()

    def play_loading_video(self):
        self.playBtn.setDisabled(True)
        self.mediaplayer.setSource(self.loading_video)
        self.mediaplayer.setLoops(QMediaPlayer.Loops.Infinite)
        self.mediaplayer.play()

    @pyqtSlot(subprocess.Popen, QUrl)
    def onMediaStarted(self, stream_process, stream_data=None):
        self.stream_process = stream_process
        if self.playerType == DefaultSettings.Player.PlayerTypes.qt_ffmpeg_Udp:
            self.udpHost = stream_data.host()
            self.udpPort = stream_data.port()
        self.startBufferReader()
        # give time for the reader to start?
        QTimer().singleShot(500, self.playFFmpegStream)

    def playFFmpegStream(self):
        self.playBtn.setEnabled(True)
        self.playBtn.setText(self.pauseText)
        self.slider.setRange(0, DefaultSettings.Player.streamTempFileSize)
        self.mediaplayer.positionChanged.connect(self.position_changed)
        self.mediaplayer.durationChanged.connect(self.duration_changed)
        self.mediaplayer.setLoops(1)
        self.mediaplayer.stop()
        self.mediaplayer.setSource(QUrl())
        time.sleep(.01)
        # Read directly from udp (not working) or buffered (not working either)
        # self.mediaplayer.setSource(QUrl(DefaultSettings.Player.ffmpegStreamUrl))
        self.mediaplayer.setSourceDevice(self.buffer)
        self.mediaplayer.play()

    def startBufferReader(self):

        self.byte_array = QByteArray()
        self.buffer = QBuffer(self.byte_array)
        self.buffer.setOpenMode(QIODevice.OpenModeFlag.ReadOnly)

        if self.playerType == DefaultSettings.Player.PlayerTypes.qt_ffmpeg_Udp:
            # read from UDP port
            self.udp_receiver = UdpReceiver(self.stream_process, self.udpHost, self.udpPort, self.buffer, self.byte_array)
            self.udp_receiver.start()

        else:
            # rad from stdout
            self.stdout_receiver = StdoutReceiver(self.stream_process, self.buffer, self.byte_array)
            self.stdout_receiver.start()

    def play_video(self, position=0):

        # wait until cache stream file exits and has a reasonable size
        self.temp_file = self.stream_files[self.stream_file_index]
        if os.path.exists(self.temp_file):
            if os.path.getsize(self.temp_file) - position > self.buffer_size or not self.firstRun:
                if self.firstRun:
                    self.firstRun = False
                    self.playBtn.setEnabled(True)
                    self.playBtn.setText(self.pauseText)
                    self.slider.setRange(0, DefaultSettings.Player.streamTempFileSize)
                    self.mediaplayer.positionChanged.connect(self.position_changed)
                    self.mediaplayer.durationChanged.connect(self.duration_changed)
                    self.mediaplayer.setLoops(1)
                # workaround to avoid qmediaplayer failing to change the source sometimes
                self.mediaplayer.stop()
                self.mediaplayer.setSource(QUrl())
                time.sleep(.01)
                self.mediaplayer.setSource(QUrl.fromLocalFile(self.temp_file))
                self.mediaplayer.play()

            else:
                self.updateSlider(os.path.getsize(self.temp_file), self.buffer_size)
                QTimer.singleShot(300, self.play_video)

        else:
            QTimer.singleShot(300, self.play_video)

    def resizeAll(self, size):
        self.video_item.setSize(size)
        # self.resize(int(size.width()) + self.wGap, int(size.height()) + self.hGap)
        self.setMinimumSize(int(size.width()) + self.wGap, int(size.height()) + self.hGap)
        self.setMaximumSize(int(size.width()) + self.wGap, int(size.height()) + self.hGap)

    def togglePlayPause(self):
        # MANAGE PAUSE at streamer level, avoiding writing,
        # thus skipping all content when in pause and coming back to live when playing again
        # if self.mediaplayer.mediaStatus == QMediaPlayer.PlaybackState.PlayingState:
        #     self.playBtn.setText(self.playText)
        #     self.mediaplayer.pause()
        # elif self.mediaplayer.mediaStatus == QMediaPlayer.PlaybackState.PausedState:
        #     self.playBtn.setText(self.pauseText)
        #     self.mediaplayer.play()
        pass

    def toggleMute(self):
        if self.audio.volume() == 0:
            self.muteBtn.setText(self.nomuteText)
            self.audio.setVolume(1)
        else:
            self.muteBtn.setText(self.muteText)
            self.audio.setVolume(0)

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
            # can also check streamer is alive?
            position = 0
            if os.path.exists(self.temp_file) and os.path.getsize(self.temp_file) >= DefaultSettings.Player.streamTempFileSize:
                # reached swap size: read from next file
                self.stream_file_index = (self.stream_file_index + 1) % len(DefaultSettings.Player.streamTempFiles)
                self.setWindowTitle(self.title + " / " + str(self.stream_file_index))
            else:
                self.mediaplayer.pause()
                position = self.mediaplayer.position()
                self.mediaplayer.pause()
            self.play_video(position)
            # probably no need for this since qmediaplayer will wait (forever?)
            # else:
            #     # not enough media to read, but temp file is not full yet. Pausing until there is more data
            #     self.mediaplayer.pause()
            #     QTimer.singleShot(100, self.play_video)

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
        if self.udp_receiver is not None:
            self.udp_receiver.stop()
        if self.stdout_receiver is not None:
            self.stdout_receiver.stop()


class UdpReceiver(QThread):

    def __init__(self, stream_process, host, port, buffer, byte_array):
        super().__init__()

        self.stopReading = False

        self.stream_process = stream_process
        self.host = host
        self.port = port
        self.buffer = buffer
        self.byte_array = byte_array
        self.socket = QUdpSocket()
        self.socket.bind(QHostAddress(host), port)

    def run(self):
        self.process_data()
        # self.socket.readyRead.connect(self.process_data)

    def process_data(self):

        # max_size = 5 * 1024 * 1024  # 5 MB

        while not self.stopReading:

            try:

                while self.socket.hasPendingDatagrams():

                    print("READING UDP")
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

            except:
                self.stop()

            finally:
                self.stream_process.kill()




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

        try:

            while not self.stopReading:

                print("READING STDOUT")
                # Read data from FFmpeg's stdout
                data = self.stream_process.stdout.read(8192)
                if not data:
                    print("NO DATA")
                    break  # Exit if no more data

                # Append data to QByteArray
                self.byte_array.append(data)

        except:
            self.stop()

        finally:
            try:
                self.stream_process.stdout.close()
                self.stream_process.kill()
            except:
                pass


    def stop(self):
        self.stopReading = True
        self.quit()
