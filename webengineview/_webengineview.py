from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView


class WebEngineView(QWebEngineView):

    def __init__(self, parent=None):
        super(WebEngineView, self).__init__(parent)

        # Enabling fullscreen
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)

        # Enabling some extra features (only those allegedly required for a "normal" / "safe" use only)
        # page.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        # self.settings().setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.FocusOnNavigationEnabled, False)
