from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineCore import qWebEngineChromiumVersion, QWebEngineProfile, QWebEnginePage

from themes import Themes
import utils


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

    class Sounds:
        dialogInformation = "res/dialog-information.wav"

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
