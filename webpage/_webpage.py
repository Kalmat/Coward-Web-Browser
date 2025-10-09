from PyQt6.QtCore import pyqtSlot, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineCertificateError
from PyQt6.QtWidgets import QMessageBox

from logger import LOGGER, LoggerSettings
from settings import DefaultSettings
from themes import Themes
from . import CheckMedia
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

        self.mediaCheck = CheckMedia(self, self.isPlayingMediaSig, self.mediaErrorSig)
        self.mediaErrorSig.connect(self.handleMediaError)
        self.windowCloseRequested.connect(self.onCloseRequested)

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

    @pyqtSlot(str)
    def handleMediaError(self, url):
        # launch external player dialog if media can't be played
        self.externalPlayer.handleExternalPlayerRequest(url)

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

    def onCloseRequested(self):
        self.mediaCheck.stop()
