from PyQt6.QtWebEngineCore import qWebEngineChromiumVersion, QWebEngineProfile, QWebEnginePage

import utils
from themes import Themes


class DefaultSettings:

    class App:
        appName = "Coward"
        appIcon = utils.resource_path("res/coward.png")
        appIcon_32 = utils.resource_path("res/coward_32.png")

    class Grips:
        gripSize = 8

    class Theme:
        defaultTheme = Themes.dark
        deafultIncognitoTheme = Themes.incognito

    class Icons:
        appIcon = utils.resource_path("res/coward.png")
        appIcon_32 = utils.resource_path("res/coward_32.png")
        loading = utils.resource_path("res/web.png")
        # path separator inverted ("/") for qss files
        tabSeparator = utils.resource_path("res/tabsep.png", True)

    class Media:
        dialogInformationSound = utils.resource_path("res/dialog-information.wav")
        bufferingVideo = utils.resource_path("res/loading.mp4")

    class Player:

        class PlayerTypes:
            internal = "qt"
            app = "mpv"
            http = "http"

        externalPlayerType = PlayerTypes.app
        streamTempFile = "temp_1.mp4"
        streamTempFile_2 = "temp_2.mp4"
        chunkSize = 8192
        bufferSize = 5*1000*1000
        streamTempFileSize = 20 * 1000 * 1000
        appPlayerPath = utils.resource_path("dist/externalplayer/mpv/mpv.exe")
        httpStreamPort = 5467
        httpServerPort = 8098
        htmlPath = utils.resource_path("html")

    class Storage:

        class App:
            storageFolder = ".kalmat"

        class Cache:
            cacheFolder = ".cache"
            cacheFile = "coward_" + str(qWebEngineChromiumVersion()) + ("_debug" if not utils.is_packaged() else "")

        class Settings:
            settingsFile = "Coward" + ("_debug" if not utils.is_packaged() else "")

    class Browser:
        defaultPage = 'https://start.duckduckgo.com/?kae=d'
        defaultTabs = [[defaultPage, 1.0, True]]

    class Cookies:
        allow = True
        allowThirdParty = False
        persistentPolicy = QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        incognitoPersistentPolicy = QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies

    class StreamErrorMessages:
        tryLater = "Try after some minutes. If the problem persists, most likely the page can't be streamed"
        cantPlay = "Probably this content can't be streamed"

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
