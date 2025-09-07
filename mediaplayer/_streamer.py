import os
import subprocess

import utils
from PyQt6.QtCore import QThread
from streamlink import Streamlink


class Streamer(QThread):

    def __init__(self, url, qualities="720p,720p60,best", stream_file="temp.mp4", external_player=None):
        super().__init__()

        self.url = url
        self.stream_file = stream_file
        self.qualities = qualities.replace(" ", "").split(",")
        self.externalPlayer = external_player

        self.playerProcess = None
        self.keep = True

    def run(self):

        # Create a Streamlink session
        session = Streamlink()

        # Get the stream object
        streams = session.streams(self.url)

        # Open the stream and pipe data to MPV
        stream = self._fetchStream(streams, self.qualities)
        if stream:
            if self.externalPlayer:
                self.runExternalPlayer(stream)
            else:
                self.runInternalPlayer(stream)

        else:
            print(f"No stream available for given parameters: URL {self.url} / Quality {self.qualities}")

    def runInternalPlayer(self, stream):
        ##### THIS WORKS!!! But must find a way to:
        #           1. Avoid huge temporary files
        #           2. Avoid QMediaPlayer stopping when getting to the end of file

        # delete previous temporary file (if exists)
        if os.path.exists(self.stream_file):
            try:
                os.remove(self.stream_file)
            except:
                pass

        # write to temporary stream file (will be read by QMediaPlayer)
        try:
            with open(self.stream_file, "wb") as f:
                with stream.open() as stream_fd:
                    while self.keep:
                        data = stream_fd.read(8192)
                        if not data:
                            break
                        f.write(data)
                        f.flush()

        except Exception as e:
            # self.keep = False
            print(f"Stream error: {e}")

    def runExternalPlayer(self, stream):
        # this works like a charm, but requires mpv (or another external player)...
        # cant it be packed together with the pyinstaller .exe file?

        # Open MPV player as subprocess
        mpv_cmd = [self.externalPlayer, "--no-cache", "--", "fd://0"]
        self.playerProcess = subprocess.Popen(mpv_cmd, stdin=subprocess.PIPE)

        # write stream data to mpv's STDIN
        try:
            with stream.open() as stream_fd:
                while self.keep:
                    data = stream_fd.read(8192)
                    if not data:
                        break
                    self.playerProcess.stdin.write(data)
                    self.playerProcess.stdin.flush()

        except Exception as e:
            print(f"Stream error: {e}")

        finally:
            if self.playerProcess.poll() is None:
                self.playerProcess.stdin.flush()
                self.playerProcess.stdin.close()

    def _fetchStream(self, streams, qualities):

        stream = None

        for quality in qualities:
            try:
                stream = streams[quality]
            except:
                pass
            if stream:
                break
        if not stream:
            print(f"Quality list not available. Available: {list(streams.keys())}")
        return stream

    def stop(self):
        self.keep = False
        if self.externalPlayer:
            if self.playerProcess is not None and self.playerProcess.poll() is None:
                utils.kill_process(self.playerProcess.pid)
        else:
            if os.path.exists(self.stream_file):
                os.remove(self.stream_file)
