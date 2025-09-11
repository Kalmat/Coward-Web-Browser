import http.server
import os
import socketserver
import subprocess
import sys

import streamlink.exceptions
from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QMainWindow, QWidget, QApplication
from streamlink import Streamlink

from settings import DefaultSettings


class Streamer(QThread):

    def __init__(self, url, qualities="720p,720p60,best", title="Coward stream", player_type=None,
                       buffering_started_sig=None, stream_started_sig=None, stream_error_sig=None, closed_sig=None):
        super().__init__()

        self.url = url
        self.qualities = qualities.replace(" ", "").split(",")
        self.title = title or "Coward stream"
        self.playerType = player_type or DefaultSettings.Player.PlayerTypes.internal

        self.stream_file = DefaultSettings.Player.streamTempFile
        self.next_stream_file = DefaultSettings.Player.streamTempFile_2
        self.externalPlayerPath = DefaultSettings.Player.appPlayerPath

        self.bufferingStartedSig = buffering_started_sig
        self.streamStartedSig = stream_started_sig
        self.startEmitted = False
        self.streamErrorSig = stream_error_sig
        self.closedSig = closed_sig

        self.stopStreaming = False
        self.playerProcess = None
        self.send_command = None
        self.stopHttpServer = False
        self.httpd = None

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

            if self.playerType == DefaultSettings.Player.PlayerTypes.app:
                self.runExternalPlayer(stream)

            elif self.playerType == DefaultSettings.Player.PlayerTypes.http:
                self.runHttpPlayer(stream)

            else:
                self.runInternalPlayer(stream)

    def runInternalPlayer(self, stream):
        ##### THIS WORKS!!! But must find a way to:
        #           1. Avoid huge temporary files
        #           2. Avoid QMediaPlayer stopping when getting to the end of file

        # write to temporary stream file (will be read by QMediaPlayer)
        totalbytes = 0
        try:
            with stream.open() as stream_fd:
                while not self.stopStreaming:
                    with open(self.stream_file, "wb") as f:
                        while not self.stopStreaming:
                            data = stream_fd.read(DefaultSettings.Player.chunkSize)
                            if not data:
                                self.stopStreaming = True
                                break
                            f.write(data)
                            f.flush()
                            totalbytes += DefaultSettings.Player.chunkSize
                            if totalbytes >= DefaultSettings.Player.streamTempFileSize:
                                totalbytes = 0
                                curr_stream_file = self.stream_file
                                self.stream_file = self.next_stream_file
                                self.next_stream_file = curr_stream_file
                                break

        except Exception as e:
            self.handleError(True)

        finally:
            self.stop()

    def runHttpPlayer(self, stream):
        # This will try to stream the video to localhost on default port
        stream.open()

        def start_html_server():
            """Serve a local HTML page that plays the stream."""

            class Handler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=DefaultSettings.Player.htmlPath, **kwargs)

                def end_headers(self):
                    # Allow video to be embedded and played properly
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Cross-Origin-Resource-Policy', 'cross-origin')
                    super().end_headers()

            os.chdir(".")  # Serve from current directory
            with socketserver.TCPServer(("", DefaultSettings.Player.httpServerPort), Handler) as httpd:
                # httpd.serve_forever()
                while not self.stopHttpServer:
                    httpd.handle_request()

        try:
            start_html_server()

        except:
            self.handleError(True)

        finally:
            self.stop()

    def runExternalPlayer(self, stream):
        # this works like a charm, but requires mpv (or another external player)...
        # can it be packed together with the pyinstaller .exe file?

        if not os.path.exists(self.externalPlayerPath):
            self.streamErrorSig.emit(DefaultSettings.StreamErrorMessages.mpvNotFound)
            return

        self.bufferingStartedSig.emit()

        # Open MPV player as subprocess
        mpvPipeName = r"\\.\pipe\mpv-pipe"
        mpv_cmd = [self.externalPlayerPath, "--title=%s - mpv" % self.title,
                                            "--no-cache",
                                            "--input-ipc-server=%s" % mpvPipeName,
                                            "--", "fd://0"]
        self.send_command = lambda command: subprocess.Popen(r"echo %s > %s" % (command, mpvPipeName), shell=True)
        self.playerProcess = subprocess.Popen(mpv_cmd, stdin=subprocess.PIPE)

        # write stream data to mpv's STDIN
        try:
            with stream.open() as stream_fd:
                while not self.stopStreaming:
                    data = stream_fd.read(DefaultSettings.Player.chunkSize)
                    if not data or self.playerProcess is None or self.playerProcess.poll() is not None:
                        break
                    if not self.startEmitted:
                        self.startEmitted = True
                        self.streamStartedSig.emit()
                    self.playerProcess.stdin.write(data)
                    self.playerProcess.stdin.flush()

        except Exception as e:
            print(f"Stream error: {e}")

        finally:
            self.stop()

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
                self.streamErrorSig.emit(DefaultSettings.StreamErrorMessages.tryLater)
            else:
                self.streamErrorSig.emit(DefaultSettings.StreamErrorMessages.cantPlay)
        self.stop()

    def stop(self):
        self.stopStreaming = True
        if self.playerType == DefaultSettings.Player.PlayerTypes.app:
            if self.playerProcess is not None and self.send_command is not None:
                self.send_command('quit')
                self.playerProcess = None
                self.send_command = None

        elif self.playerType == DefaultSettings.Player.PlayerTypes.http:
            self.stopHttpServer = True
        self.closedSig.emit(True)
        self.quit()


class Window(QMainWindow):

    def __init__(self, url):
        super().__init__()

        self.widget = QWidget()

        self.stream_thread = Streamer(url=url,
                                      title="lvpes - Twitch",
                                      player_type=DefaultSettings.Player.PlayerTypes.http
                                      )
        # qualities="720p,720p60,best", title="Coward stream", player_type=None
        self.stream_thread.start()

    def closeEvent(self, a0):
        self.stream_thread.stop()


if __name__ == "__main__":
    app = QApplication(sys.argv + ['-platform', 'windows:darkmode=1'])
    window = Window("https://www.twitch.tv/lvpes")
    window.show()

    app.exec()
