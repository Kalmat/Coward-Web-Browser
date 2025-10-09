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
        self.check_thread = _CheckMediaWorker(url, self.mediaErrorSig)
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
        self.isPlayingMediaSig.emit(self.page, False if isPlaying is None else isPlaying)

    def stop(self):
        self.mediaCheckTimer.stop()


class _CheckMediaWorker(QThread):

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


"""
# TWITCH:
# Error Level: JavaScriptConsoleMessageLevel.ErrorMessageLevel --- URL: ... --- Message: Player stopping playback - error Player:2 (ErrorNotSupported code 0 - No playable format) --- Line number: 1

# YOUTUBE:
# --> No error

if level == WebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
    # this is totally empyrical and based in just one a small number of cases
    # this is promising but... how to access this data?
    # "debug_error": "{\"errorCode\":\"html5.unsupportedlive\",\"errorMessage\":\"No se admite este formato de vídeo.\",\"Ua\":\"HTML5_NO_AVAILABLE_FORMATS_FALLBACK\",\"Cx\":\"\",\"cN\":\"buildRej.1;a.1;d.1;drm.0;f18.0;c18.0;f133.1;f140.1;f242.1;cAAC.0;cAVC.0;cVP9.1;a6s.1\",\"Rl\":2,\"cpn\":\"KSAdNV_auzm2Ivhf\"}",

    # this works for twitch, but not for YT live videos
    if "Player" in message and "ErrorNotSupported" in message:
        self.externalPlayer.handleExternalPlayerRequest(self.url().toString())       

Example for YouTube
Here’s how you can set up an error listener using the YouTube IFrame Player API:

<script src="https://www.youtube.com/iframe_api"></script>
<div id="player"></div>
<script>
    var player;

    function onYouTubeIframeAPIReady() {
        player = new YT.Player('player', {
            height: '390',
            width: '640',
            videoId: 'YOUR_VIDEO_ID',
            events: {
                'onError': onPlayerError,
            }
        });
    }

    function onPlayerError(event) {
        console.log('Error detected:', event.data);
        // Handle different error codes if needed
    }
</script>


Example for Twitch
For Twitch, you can set up an event listener like this:

<script src="https://embed.twitch.tv/embed/v1.js"></script>
<div id="twitch-embed"></div>
<script type="text/javascript">
    new Twitch.Embed("twitch-embed", {
        channel: "YOUR_CHANNEL",
        parent: ["YOUR_WEBSITE_DOMAIN"],
        width: 800,
        height: 600,
    });

    // Listen for errors
    Twitch.on(Embed.Events.ERROR, function(error) {
        console.log('Error detected:', error);
    });
</script>
"""
