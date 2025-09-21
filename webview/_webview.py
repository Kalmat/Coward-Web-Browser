from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView


class WebView(QWebEngineView):

    def __init__(self, parent=None):
        super(WebView, self).__init__(parent)

    def applySettings(self):

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
