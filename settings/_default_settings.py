from enum import Enum
import os

from PyQt6.QtWebEngineCore import qWebEngineChromiumVersion, QWebEngineProfile, QWebEnginePage

import utils
from themes import Themes


class DefaultSettings:

    class App:
        appName = "Coward"
        appIcon = utils.resource_path("res/coward.png")
        appIcon_32 = utils.resource_path("res/coward_32.png")
        tempFolder = os.path.join(os.getenv("SystemDrive"), "Windows", "Temp", "Coward")

    class History:
        historySize = 100

    class Grips:
        gripSize = 8

    class Theme:
        defaultTheme = Themes.Theme.dark.value
        deafultIncognitoTheme = Themes.Theme.incognito.value

    class Icons:
        appIcon = utils.resource_path("res/coward.png")
        appIcon_32 = utils.resource_path("res/coward_32.png")
        loading = utils.resource_path("res/web.png")
        # path separator inverted ("/") for qss files
        tabSeparator = utils.resource_path("res/tabsep.png", True)

    class Storage:

        class App:
            storageFolder = ".kalmat"

        class Cache:
            cacheFolder = ".cache"
            cacheFile = "coward_" + str(qWebEngineChromiumVersion()) + ("_debug" if not utils.is_packaged() else "")

        class Settings:
            settingsFile = "Coward" + ("_debug" if not utils.is_packaged() else "")

        class History:
            historyFolder = "coward.history"
            historyFile = "data"

    class Browser:
        defaultPage = 'https://start.duckduckgo.com/?kae=d'
        defaultTabs = [[defaultPage, 1.0, True]]
        htmlPath = utils.resource_path("html")
        fatalErrorPage = "fatal_error.html"

    class Cookies:
        allow = True
        allowThirdParty = False
        persistentPolicy = QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        incognitoPersistentPolicy = QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies

    class Security:

        class SecurityLevels(Enum):
            mad = 0
            relaxed = 1
            safe = 2
            paranoid = 3

        # This affects to QWebEngineView attributes only (see WebView class)
        # Other options like certificates, features or permissions will be asked to the user using dialogs
        securityLevel = SecurityLevels.safe

    class AdBlocker:
        enableAdBlocker = True
        urlBlackList = []  # "aswpsdkeu"]  # , "ads"]  # this is totally empyrical
        filterlistsFolder = ".filterlists"
        easylistUrl = 'https://easylist.to/easylist/easylist.txt'
        easylistFile = "easylist.txt"
        easyprivacyUrl = 'https://easylist.to/easylist/easyprivacy.txt'
        easyprivacytFile = "easyprivacy.txt"

    class Media:
        dialogInformationSound = utils.resource_path("res/dialog-information.wav")
        bufferingVideo = utils.resource_path("res/loading.mp4")

    class Player:

        class PlayerTypes(Enum):
            mpv = "mpv"          # strongly recommended, but requires mpv.exe in ./externalplayer/mpv/ folder
            http = "http"        # Not working with QWebEngine. Requires ffmpeg in ./externalplayer/ffmpeg/ folder
            qt = "qt"            # experimental. Buffering is not very well resolved
            qt_ffmpeg_Udp = "qt_ff_u"     # Not working with QMediaPlayer. Requires ffmpeg in ./externalplayer/ffmpeg/ folder
            qt_ffmpeg_Stdout = "qt_ff_s"  # Not working with QMediaPlayer. Requires ffmpeg in ./externalplayer/ffmpeg/ folder

        externalPlayerType = PlayerTypes.mpv
        streamTempFiles = ["temp_1.mp4", "temp_2.mp4", "temp_3.mp4"]
        streamTempFolder = "stream"
        ffmpegStreamUrl = "udp://@127.0.0.1:5000/stream?overrun_nonfatal=1&fifo_size=50000000"
        chunkSize = 8192
        bufferSize = 5 * 1024 * 1024
        streamTempFileSize = 50 * 1024 * 1024
        mpvPlayerPath = utils.resource_path("externalplayer/mpv/mpv.exe", use_dist_folder="dist")
        ffmpegPath = utils.resource_path("externalplayer/ffmpeg/bin/ffmpeg.exe", use_dist_folder="dist")
        httpStreamPort = 5123
        httpServerHost = "0.0.0.0"
        httpServerPort = 5000

    class Downloads:
        downloadTempFolder = "downloads"

    class Logger:

        class LogLevels(Enum):
            info = "[INFO]"
            warning = "[WARN]"
            error = "[ERROR]"
            fatal = "[FATAL]"

        debugEnabled = True      # print application messages and JavaScriptConsoleMessages
        loggingEnabled = False   # log messages to file instead of printing them (reequires debug enabled)
        loggerFolder = ".logs"
        logDepth = 0  # max number of old log files to keep (-1 = infinite)

    class StreamErrorMessages:
        tryLater = "Try after some minutes. If the problem persists, most likely the page can't be streamed"
        cantPlay = "Probably this content can't be streamed"
        mpvNotFound = "MPV player not found. please copy mpv.exe file in ./externalplayer/mpv folder"
        onePlayerOnly = "There is another player running for this URL. Please close it before opening a new one"

    class DialogMessages:
        featureRequest = "This page is asking for your permission to %s."
        permissionRequest = "This page is asking for your permission to %s."
        externalPlayerRequest = "This page contains non-compatible media.\n\n" \
                                "Do you want to try to load it using an external player?"
        bufferingStarted = "Buffering content to stream to external player.\n\n" \
                           "Your stream will start soon, please be patient."
        streamError = "There has been a problem while trying to stream this page.\n\n%s"
        cleanAllRequest = "This will erase all your history and stored cookies.\n" \
                          "This action can not be undone.\n\n" \
                          "Are you sure you want to proceed?"
        eraseHistorylRequest = "This will erase your navigation history.\n" \
                               "This action can not be undone.\n\n" \
                               "Are you sure you want to proceed?"
        certificateErrorThirdParty = "Certificate error while loading this URL:\n%s\n\n" \
                                     "From page:\n%s (%s)\n\n" \
                                     "%s\n\n" \
                                     "Do you want to ignore these errors and continue loading the page?"
        certificateErrorFirstParty = "The connection to this site is not secure\n\n" \
                                     "Certificate error from page:\n%s (%s)\n\n" \
                                     "%s\n\n" \
                                     "Do you want to ignore these errors and continue loading the page?"

    FeatureMessages = {
        QWebEnginePage.Feature.Notifications: "show Notifications",
        QWebEnginePage.Feature.Geolocation: "get your Geolocation",
        QWebEnginePage.Feature.MediaAudioCapture: "use your mic to capture audio",
        QWebEnginePage.Feature.MediaVideoCapture: "user your camera to capture video",
        QWebEnginePage.Feature.MediaAudioVideoCapture: "use your mic and camera to capture audio and video",
        QWebEnginePage.Feature.MouseLock: "lock your mouse",
        QWebEnginePage.Feature.DesktopVideoCapture: "capture your desktop as video",
        QWebEnginePage.Feature.DesktopAudioVideoCapture: "capture your desktop video and audio",
        QWebEnginePage.Feature.ClipboardReadWrite: "copy to the clipboard",
        QWebEnginePage.Feature.LocalFontsAccess: "access local fonts"
    }









