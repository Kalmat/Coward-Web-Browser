import os

from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView

import utils
from settings import DefaultSettings


class WebView(QWebEngineView):

    def __init__(self, parent=None):
        super(WebView, self).__init__(parent)

        self.fatal_error_page = os.path.join(DefaultSettings.Browser.htmlPath, DefaultSettings.Browser.fatalErrorPage)

    def setUrl(self, url):
        self.load(url)

    def load(self, *__args):
        try:
            super().load(*__args)
        except:
            self.load(self.fatal_error_page)

    def applySettings(self, security_level, dark_mode):

        # Apply security level settings
        # These values are enabled / disabled by default, but better set them in case it changes in the future

        # values for "mad" security level
        allow = security_level == DefaultSettings.Security.SecurityLevels.mad
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, allow)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.AllowGeolocationOnInsecureOrigins, allow)

        # values for "relaxed" security level
        allow = security_level <= DefaultSettings.Security.SecurityLevels.relaxed
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, allow)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, allow)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript, allow)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, allow)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, allow)

        # values for "safe" security level
        allow = security_level <= DefaultSettings.Security.SecurityLevels.safe
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, allow)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, allow)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, allow)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.ScreenCaptureEnabled, allow)

        # "paranoid" level means everything will be disabled

        # common values, not related to security level
        # self.settings().setAttribute(QWebEngineSettings.WebAttribute.ReadingFromCanvasEnabled, False)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.FocusOnNavigationEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.LinksIncludedInFocusChain, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.HyperlinkAuditingEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.SpatialNavigationEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.NavigateOnDropEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.ForceDarkMode, dark_mode)

        """ https://doc.qt.io/qt-6/qwebenginesettings.html
            WebAttribute.FocusOnNavigationEnabled
            WebAttribute.PrintElementBackgrounds
            WebAttribute.AllowRunningInsecureContent
            WebAttribute.AllowGeolocationOnInsecureOrigins
            WebAttribute.AllowWindowActivationFromJavaScript
            WebAttribute.ShowScrollBars
            WebAttribute.PlaybackRequiresUserGesture
            WebAttribute.WebRTCPublicInterfacesOnly
            WebAttribute.JavascriptCanPaste
            WebAttribute.DnsPrefetchEnabled
            WebAttribute.PdfViewerEnabled
            WebAttribute.NavigateOnDropEnabled
            WebAttribute.ReadingFromCanvasEnabled
            WebAttribute.ForceDarkMode
            WebAttribute.PrintHeaderAndFooter
            WebAttribute.PreferCSSMarginsForPrinting
            WebAttribute.TouchEventsApiEnabled
            WebAttribute.AutoLoadImages
            WebAttribute.JavascriptEnabled
            WebAttribute.JavascriptCanOpenWindows
            WebAttribute.JavascriptCanAccessClipboard
            WebAttribute.LinksIncludedInFocusChain
            WebAttribute.LocalStorageEnabled
            WebAttribute.LocalContentCanAccessRemoteUrls
            WebAttribute.XSSAuditingEnabled
            WebAttribute.SpatialNavigationEnabled
            WebAttribute.LocalContentCanAccessFileUrls
            WebAttribute.HyperlinkAuditingEnabled
            WebAttribute.ScrollAnimatorEnabled
            WebAttribute.ErrorPageEnabled
            WebAttribute.PluginsEnabled
            WebAttribute.FullScreenSupportEnabled
            WebAttribute.ScreenCaptureEnabled
            WebAttribute.WebGLEnabled
            WebAttribute.Accelerated2dCanvasEnabled
            WebAttribute.AutoLoadIconsForPage
            WebAttribute.TouchIconsEnabled
            WebAttribute.FocusOnNavigationEnabled
            WebAttribute.PrintElementBackgrounds
            WebAttribute.AllowRunningInsecureContent
            WebAttribute.AllowGeolocationOnInsecureOrigins
            WebAttribute.AllowWindowActivationFromJavaScript
            WebAttribute.ShowScrollBars
            WebAttribute.PlaybackRequiresUserGesture
            WebAttribute.WebRTCPublicInterfacesOnly
            WebAttribute.JavascriptCanPaste
            WebAttribute.DnsPrefetchEnabled
            WebAttribute.PdfViewerEnabled
            WebAttribute.NavigateOnDropEnabled
            WebAttribute.ReadingFromCanvasEnabled
            WebAttribute.ForceDarkMode
            WebAttribute.PrintHeaderAndFooter
            WebAttribute.PreferCSSMarginsForPrinting
            WebAttribute.TouchEventsApiEnabled
        """
