from PyQt6.QtCore import pyqtSlot, QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QIcon
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineCertificateError
from PyQt6.QtWidgets import QMessageBox
from streamlink import Streamlink

from logger import LOGGER, LoggerSettings
from settings import DefaultSettings
from themes import Themes
from ._externalplayer import ExternalPlayer


class WebPage(QWebEnginePage):

    mediaErrorSig = pyqtSignal(str)

    def __init__(self, profile, parent, isPlayingMediaSig, dialog_manager, http_manager=None):
        super(WebPage, self).__init__(profile, parent)

        self.isPlayingMediaSig = isPlayingMediaSig
        self.dialog_manager = dialog_manager
        self.http_manager = http_manager

        self._debugInfoEnabled = False
        self._logToFile = False
        self._logFile = "pagelog.txt"
        self._logFileOpen = False

        self.http_manager = http_manager
        self.externalPlayer = ExternalPlayer(self, dialog_manager, http_manager)

        # manage other signals
        self.certificateError.connect(self.handleCertificateError)

        # translate JavaScriptConsole errors to Logger errors values:
        self.errorLevel = {
            QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel: LoggerSettings.LogLevels.info,
            QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel: LoggerSettings.LogLevels.warning,
            QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel: LoggerSettings.LogLevels.error
        }

        self.mediaErrorSig.connect(self.handleMediaError)

        self.mediaCheckTimer = QTimer()
        self.mediaCheckTimer.timeout.connect(self.checkMediaPlaying)
        self.mediaCheckTimer.start(60000)

    # def acceptNavigationRequest(self, url, type, isMainFrame: bool) -> bool:
    #     if type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked: return False
    #     return super().acceptNavigationRequest(url, type, isMainFrame)

    @pyqtSlot(QWebEngineCertificateError)
    def handleCertificateError(self, error: QWebEngineCertificateError):

        if error.isOverridable():
            # defer error to ask for user input
            error.defer()

            # select affected tab
            browser = self.parent()
            tabsWidget = browser.parent().parent()
            tabsWidget.setCurrentWidget(browser)

            # show dialog to ask user
            # this dialog has to be synchronous and executed in main thread, or it will crash when accessing error
            if error.isMainFrame():
                message = (DefaultSettings.DialogMessages.certificateErrorFirstParty
                           % (self.title(), error.url().toString(), error.description()))
            else:
                message = (DefaultSettings.DialogMessages.certificateErrorThirdParty
                           % (error.url().toString(), self.title(), self.url().toString(), error.description()))

            response = self.createCertificateErrorDialog(message)

            # apply user action
            if response == QMessageBox.StandardButton.Ok:
                error.acceptCertificate()
            else:
                error.rejectCertificate()
        else:
            # if error can not be overridden, accept or reject according to security level
            if DefaultSettings.Security.securityLevel == DefaultSettings.Security.SecurityLevels.mad:
                error.acceptCertificate()
            else:
                error.rejectCertificate()

    def createCertificateErrorDialog(self, message):
        # Create a synchronous message box to ask user
        msg_box = QMessageBox()
        msg_box.setStyleSheet(Themes.styleSheet(DefaultSettings.Theme.defaultTheme, Themes.Section.messagebox))
        msg_box.setWindowTitle("Security Certificate Error")
        msg_box.setWindowIcon(QIcon(DefaultSettings.Icons.appIcon_32))
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText(f"A certificate error occurred:")
        msg_box.setInformativeText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        return msg_box.exec()

    def handleFeatureRequested(self, origin, feature):
        message = DefaultSettings.DialogMessages.featureRequest % DefaultSettings.FeatureMessages[feature]
        self.showDialog(
            message=message,
            acceptSlot=(lambda o=origin, f=feature: self.accept_feature(o, f)),
            rejectSlot=(lambda o=origin, f=feature: self.reject_feature(o, f)))

    def accept_feature(self, origin, feature):
        self.setFeaturePermission(origin, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser)

    def reject_feature(self, origin, feature):
        self.setFeaturePermission(origin, feature, QWebEnginePage.PermissionPolicy.PermissionDeniedByUser)

    def handlePermissionRequested(self, request):
        message = DefaultSettings.DialogMessages.featureRequest % (DefaultSettings.FeatureMessages[request.type()])
        self.showDialog(
            message=message,
            acceptSlot=request.grant,
            rejectSlot=request.deny)

    def checkCanPlayMedia(self):
        # TODO: find a reliable way to check if there is a media playback error (most likely, there isn't)
        # instead, this detects if media can be streamed using streamlink (very likely media is not compatible, but not always)
        # the problem is that it takes A LOT of time (1.8 secs.), so running it in separate thread
        self.check_thread = CheckMedia(self, self.mediaErrorSig)
        self.check_thread.start()

    @pyqtSlot(str)
    def handleMediaError(self, url):
        # launch external player dialog if media can't be played
        self.externalPlayer.handleExternalPlayerRequest(url)

    def checkMediaPlaying(self):
        self.runJavaScript("""
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

    def handleMediaStatus(self, isPlaying):
        isPlaying = (isPlaying is not None and isPlaying) or self.externalPlayer.hasExternalPlayerOpen()
        self.isPlayingMediaSig.emit(self, isPlaying)

    def javaScriptConsoleMessage(self, level, message, lineNumber=0, sourceID=""):

        LOGGER.write(self.errorLevel.get(level, LoggerSettings.LogLevels.fatal), "JavaScriptConsole", message)

    def showDialog(self, message, buttonOkOnly=False, acceptSlot=None, rejectSlot=None):
        dialog = self.dialog_manager.createDialog(
            icon=self.icon(),
            title=self.title() or self.url().toString(),
            message=message,
            buttonOkOnly=buttonOkOnly,
            acceptedSlot=acceptSlot,
            rejectedSlot=rejectSlot
        )
        return dialog


class CheckMedia(QThread):

    def __init__(self, page, handleMediaErrorSig):
        super().__init__()

        self.page = page
        self.url = page.url().toString()
        self.handleMediaErrorSig = handleMediaErrorSig

    def run(self):
        session = Streamlink()
        try:
            streams = session.streams(self.url)
            stream = streams["best"]
        except:
            stream = None
        if stream:
            self.handleMediaErrorSig.emit(self.url)

        # this is ASYNCHRONOUS, so can't be used to return any value. Must use a method/function to handle return
        # this detects media failures, but sometimes it sends "false" alarms (e.g. in YT videos)
        # other times it returns ok, but it is not (e.g. 2nd time and following in Twitch)
        # see example of debug data at the end of the file. How could we get this info from python/PyQt?
        # self.runJavaScript("""
        #         var mediaElements = document.querySelectorAll('video, audio');
        #         var canPlay = Array.from(mediaElements).every(media => media.canPlayType(media.type) !== '');
        #         canPlay;
        #     """, lambda ok, u=self.url().toString(): self.handleMediaError(ok, u))

        # self.runJavaScript("""
        #     var mediaElements = document.querySelectorAll('video, audio');
        #     var hasError = false;
        #
        #     mediaElements.forEach(function(media) {
        #         media.onerror = function() {
        #             hasError = true;
        #             console.log('COWARD --- Error detected on media element:', media);
        #         };
        #     });
        #     if (!hasError) {
        #         console.log('COWARD --- All media elements loaded successfully.');
        #     };
        #     hasError;
        # """, lambda hasError, u=self.url().toString(): self.handleMediaError(hasError, u))


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
