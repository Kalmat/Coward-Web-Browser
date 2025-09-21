from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView


class WebView(QWebEngineView):

    def __init__(self, parent=None):
        super(WebView, self).__init__(parent)

    def applySettings(self, dark_mode=False):

        # Enabling fullscreen
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)

        # Enabling some extra features (only those allegedly required for a "normal" / "safe" use only)
        # self.settings().setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        # page.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        # self.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.FocusOnNavigationEnabled, True)

        if dark_mode:
            self.settings().setAttribute(QWebEngineSettings.WebAttribute.ForceDarkMode, True)
        else:
            self.settings().setAttribute(QWebEngineSettings.WebAttribute.ForceDarkMode, False)

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
