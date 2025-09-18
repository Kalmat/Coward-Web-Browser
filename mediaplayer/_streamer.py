import os
import shutil
import subprocess
import sys
import time

import ffmpeg
import streamlink.exceptions
from PyQt6.QtCore import QThread, QUrl
from PyQt6.QtWidgets import QMainWindow, QWidget, QApplication
from streamlink import Streamlink

from settings import DefaultSettings


class Streamer(QThread):

    def __init__(self, url, qualities="720p,720p60,best", title="Coward stream", player_type=None, http_manager=None,
                       buffering_started_sig=None, stream_started_sig=None, stream_error_sig=None, closed_sig=None,
                       ffmpeg_started_sig=None, index=0):
        super().__init__()

        self.url = url
        self.qualities = qualities.replace(" ", "").split(",")
        self.title = title or "Coward stream"
        self.playerType = player_type
        self.index = index
        self.http_manager = http_manager
        self.temp_folder = str(os.path.join(DefaultSettings.App.tempFolder, DefaultSettings.Player.streamTempFolder))

        # mpv player path
        self.externalPlayerPath = DefaultSettings.Player.mpvPlayerPath

        # setting qt player temporary files
        self.stream_files = [os.path.normpath(os.path.join(self.temp_folder, str(index), temp_file))
                                    for temp_file in DefaultSettings.Player.streamTempFiles]
        self.stream_file_index = 0
        if not os.path.exists(os.path.normpath(os.path.join(self.temp_folder, str(index)))):
            os.makedirs(os.path.normpath(os.path.join(self.temp_folder, str(index))))

        # setting signals to control dialogs and stream lifecycle
        self.bufferingStartedSig = buffering_started_sig
        self.streamStartedSig = stream_started_sig
        self.startEmitted = False
        self.streamErrorSig = stream_error_sig
        self.closedSig = closed_sig
        self.ffmpegStartedSig = ffmpeg_started_sig

        # setting processes control variables
        self.mpv_process = None
        self.ffmpeg_process = None
        self.stopStreaming = False
        self.send_mpv_command = None

    def run(self):

        if self.playerType == DefaultSettings.Player.PlayerTypes.http:
            options = {
                "player-external-http": True,
                "player-external-http-port": DefaultSettings.Player.httpStreamPort,
                "player-external-http-continuous": True
            }
        else:
            options = {}
        session = Streamlink(options=options)

        stream = None
        errorRaised = False
        tryLater = False
        try:
            # Get the stream object
            streams = session.streams(self.url)

            # Open the stream and pipe data to MPV
            stream = self._fetchStream(streams, self.qualities)
            if not stream:
                errorRaised = True

        except streamlink.NoPluginError:
            errorRaised = True
        except streamlink.PluginError:
            errorRaised = True
            tryLater = True
        except streamlink.StreamError:
            errorRaised = True
        except streamlink.NoStreamsError:
            errorRaised = True
        except:
            errorRaised = True
            tryLater = True

        if errorRaised:
            self.handleError(tryLater)

        else:

            if self.playerType == DefaultSettings.Player.PlayerTypes.qt:
                self.runQtPlayer(stream)

            elif self.playerType == DefaultSettings.Player.PlayerTypes.qt_ffmpeg_Udp:
                self.runQtPlayerFFmpegUdp(stream)

            elif self.playerType == DefaultSettings.Player.PlayerTypes.qt_ffmpeg_Stdout:
                self.runQtPlayerFFmpegStdout(stream)

            elif self.playerType == DefaultSettings.Player.PlayerTypes.http:
                self.runHttpPlayer(stream)

            else:
                self.bufferingStartedSig.emit(self.url)
                self.runMPVPlayer(stream)

    def runMPVPlayer(self, stream):
        # this works like a charm, but requires mpv (or another external player)...
        # can it be packed together with the pyinstaller .exe file?

        if not os.path.exists(self.externalPlayerPath):
            self.streamErrorSig.emit(DefaultSettings.StreamErrorMessages.mpvNotFound, self.url)
            return

        # Open MPV player as subprocess
        mpvPipeName = r"\\.\pipe\mpv-pipe" + str(self.index)
        mpv_cmd = [self.externalPlayerPath, "--title=%s - mpv" % self.title,
                                            "--no-cache",
                                            "--input-ipc-server=%s" % mpvPipeName,
                                            "--", "fd://0"]
        self.send_mpv_command = lambda command: subprocess.Popen(r"echo %s > %s" % (command, mpvPipeName), shell=True)
        self.mpv_process = subprocess.Popen(mpv_cmd, stdin=subprocess.PIPE)

        # write stream data to mpv's STDIN
        try:
            with stream.open() as stream_fd:
                while not self.stopStreaming:
                    data = stream_fd.read(DefaultSettings.Player.chunkSize)
                    if not data or self.mpv_process is None or self.mpv_process.poll() is not None:
                        break
                    self.mpv_process.stdin.write(data)
                    self.mpv_process.stdin.flush()
                    if not self.startEmitted:
                        self.startEmitted = True
                        self.streamStartedSig.emit(self.url)

        except:
            self.handleError(True)

        finally:
            self.stop()

    def runQtPlayer(self, stream):
        ##### THIS WORKS!!! But must find a way to:
        #           1. Avoid huge temporary files
        #           2. Avoid files to be overwritten before qmediaplayer reads them

        # write to temporary stream file (will be read by QMediaPlayer)
        with stream.open() as stream_fd:
            tries_count = 0
            while not self.stopStreaming:
                self.temp_file = self.stream_files[self.stream_file_index]
                with open(self.temp_file, "wb") as f:
                    while not self.stopStreaming:
                        data = stream_fd.read(DefaultSettings.Player.chunkSize)
                        if data:
                            f.write(data)
                            f.flush()
                            tries_count = 0
                            if os.path.getsize(self.temp_file) >= DefaultSettings.Player.streamTempFileSize:
                                self.stream_file_index = (self.stream_file_index + 1) % len(self.stream_files)
                                # optimize disk space wiping the content of non-used file
                                del_file = self.stream_files[(self.stream_file_index + 1) % len(self.stream_files)]
                                if os.path.exists(del_file):
                                    with open(del_file, "wb") as file:
                                        pass
                                break
                        else:
                            # give some time to retrieve more data before giving up
                            tries_count += 1
                            if tries_count > 3:
                                self.stopStreaming = True
                                break
                            else:
                                time.sleep(1)

    def runQtPlayerFFmpegUdp(self, stream):

        try:
            # FFmpeg input: stream URL
            stream = ffmpeg.input(
                stream.to_url(),
                re=None,  # Allow real-time streaming
            )
            # Output: pipe as fragmented MP4 (streamable, supports seeking)
            # ffmpeg -f gdigrab -framerate 30 -probesize 100M -i title="" -c:v libx264 -preset veryfast -maxrate 1000k -bufsize 1000k -pix_fmt yuv420p -g 50 -c:a aac -b:a 128k -f rtsp -rtsp_transport udp rtsp://129.0.0.1:8554/stream
            stream = ffmpeg.output(
                stream, DefaultSettings.Player.ffmpegStreamUrl,
                format='mpegts',  # Use mpegts to stream to UDP
                vcodec='copy',    # Copy video without re-encoding
                acodec='aac',     # Use AAC audio
                flags='+global_header',
                **{'fifo_size': 50*1024*1024/188, 'overrun_nonfatal': 1},
                # **{'bsf:a': 'aac_adtstoasc'},
                movflags='frag_keyframe+empty_moov+default_base_moof',  # For streaming
                pix_fmt='bgr24',
                # flush_packets=0,
                # pkt_size=1316,
                # overrun_nonfatal=1,
                # fifo_size=50*1024*1024/188,
            )
            # Run: start ffmpeg process in separate thread
            self.ffmpeg_process = ffmpeg.run_async(
                stream,
                pipe_stdout=False,
                pipe_stderr=False,
                cmd=DefaultSettings.Player.ffmpegPath
            )

        except Exception as e:
            self.handleError(True)

        self.ffmpegStartedSig.emit(self.ffmpeg_process, QUrl(DefaultSettings.Player.ffmpegStreamUrl))

    def runQtPlayerFFmpegStdout(self, stream):

        try:
            # FFmpeg input: stream URL
            stream = ffmpeg.input(
                stream.to_url(),
                re=None,  # Allow real-time streaming
            )
            # Output: pipe as fragmented MP4 (streamable, supports seeking)
            stream = ffmpeg.output(
                stream, 'pipe:',
                format='mp4',      # check which format is better to read from stdout
                vcodec='copy',     # Copy video without re-encoding
                acodec='copy',     # Copy audio without re-encoding
                movflags='frag_keyframe+empty_moov+default_base_moof',  # For streaming
                pix_fmt='bgr24',
                # flush_packets=0,
                # pkt_size=1316,
                # overrun_nonfatal=1,
                # fifo_size=50*1024*1024/188,
                **{'bsf:a': 'aac_adtstoasc'}
            )
            # Run: start ffmpeg process in separate thread
            self.ffmpeg_process = ffmpeg.run_async(
                stream,
                pipe_stdout=True,
                pipe_stderr=False,
                cmd=DefaultSettings.Player.ffmpegPath
            )

        except Exception as e:
            self.handleError(True)

        self.ffmpegStartedSig.emit(self.ffmpeg_process, QUrl())

    def runHttpPlayer(self, stream):

        try:

            # FFmpeg input: stream URL
            stream = ffmpeg.input(
                stream.to_url(),
                re=None,  # Allow real-time streaming
            )
            # Output: pipe as fragmented MP4 (streamable, supports seeking)
            stream = ffmpeg.output(
                stream, 'pipe:',
                format='mp4',   # Use mp4 container with fragmentation
                vcodec='copy',  # Copy video without re-encoding
                acodec='copy',  # Copy audio without re-encoding
                movflags='frag_keyframe+empty_moov+default_base_moof',  # For streaming
                pix_fmt='bgr24',  # not sure if this helps
                **{'bsf:a': 'aac_adtstoasc'}
            )
            # Run ffmpeg to stream to stdout
            self.ffmpeg_process = ffmpeg.run_async(
                stream,
                pipe_stdout=True,
                pipe_stderr=False,
                cmd=DefaultSettings.Player.ffmpegPath
            )
            self.http_manager.setStreamData(self.ffmpeg_process.stdout, self.title, self.url)

            # Ideal scenario: launch a new window containing the stream, but... it doesn't work in QWebEngine
            # self.openPlayerInNewWindowSig.emit()

        except Exception as e:
            self.handleError(True)

    def _fetchStream(self, streams, qualities):

        stream = None
        available_qualities = streams.keys()

        for quality in qualities:
            if quality in available_qualities:
                stream = streams[quality]
                break
        if not stream:
            print(f"Quality list not available. Available: {list(available_qualities)}")
        return stream

    def handleError(self, tryLater):
        if self.streamErrorSig is not None:
            if tryLater:
                self.streamErrorSig.emit(DefaultSettings.StreamErrorMessages.tryLater, self.url)
            else:
                self.streamErrorSig.emit(DefaultSettings.StreamErrorMessages.cantPlay, self.url)
        self.stop()

    def stop(self):
        self.stopStreaming = True
        if self.playerType == DefaultSettings.Player.PlayerTypes.mpv:
            if self.mpv_process is not None and self.send_mpv_command is not None:
                self.send_mpv_command('quit')
                self.mpv_process = None
                self.send_mpv_command = None

        elif self.ffmpeg_process is not None:
                self.ffmpeg_process.kill()

        temp_folder = os.path.normpath(os.path.join(self.temp_folder, str(self.index)))
        if os.path.exists(temp_folder):
            try:
                # try to delete the temp folder
                shutil.rmtree(temp_folder)
            except:
                # if it fails (very likely), try to at least free the unnecessary space
                for file in os.listdir(temp_folder):
                    with open(file, "w") as f:
                        pass
                pass

        self.closedSig.emit(True, self.url)
        self.quit()


# this is for testing only
class Window(QMainWindow):

    def __init__(self, url):
        super().__init__()

        self.widget = QWidget()

        self.stream_thread = Streamer(url=url,
                                      title="lvpes - Twitch",
                                      player_type=DefaultSettings.Player.PlayerTypes.qt
                                      )
        self.stream_thread.start()

    def closeEvent(self, a0):
        self.stream_thread.stop()
        self.stream_thread.wait()
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv + ['-platform', 'windows:darkmode=1'])
    window = Window("https://www.twitch.tv/eslcs")
    window.show()
    app.exec()
