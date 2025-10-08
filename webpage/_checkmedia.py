from PyQt6.QtCore import QThread, pyqtSlot, QTimer
from streamlink import Streamlink


class CheckMedia:

    def __init__(self, page, isPlayingMediaSig, mediaErrorSig):

        self.page = page
        self.isPlayingMediaSig = isPlayingMediaSig
        self.mediaErrorSig = mediaErrorSig

        self.mediaCheckTimer = QTimer()
        self.mediaCheckTimer.timeout.connect(self.checkMediaPlaying)
        self.mediaCheckTimer.start(60000)

    def checkCanPlayMedia(self, url):
        # TODO: find a reliable way to check if there is a media playback error (most likely, there isn't)
        # instead, this detects if media can be streamed using streamlink (very likely media is not compatible, but not always)
        # the problem is that it takes A LOT of time (1.8 secs.), so running it in separate thread
        self.check_thread = CheckMediaWorker(url, self.mediaErrorSig)
        self.check_thread.start()

    def checkMediaPlaying(self):
        self.page.runJavaScript("""
            var mediaElements = document.querySelectorAll('video, audio');
            var isPlaying = false;

            for (var i = 0; i < mediaElements.length; i++) {
                if (!mediaElements[i].paused) {
                    isPlaying = true;
                    console.log('COWARD --- media is playing');
                    break;
                }
            }

            isPlaying;
        """, self.handleMediaStatus)

    @pyqtSlot(bool)
    def handleMediaStatus(self, isPlaying):
        # detect and update if there is media playing in page
        self.isPlayingMediaSig.emit(self.page, isPlaying)


class CheckMediaWorker(QThread):

    def __init__(self, url, handleMediaErrorSig):
        super().__init__()

        self.url = url
        self.handleMediaErrorSig = handleMediaErrorSig

    def run(self):
        session = Streamlink()
        try:
            streams = session.streams(self.url)
            stream = streams["best"]
            if stream:
                self.handleMediaErrorSig.emit(self.url)
        except:
            pass
