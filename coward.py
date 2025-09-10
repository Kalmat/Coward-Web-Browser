# based on: https://www.geeksforgeeks.org/python/creating-a-tabbed-browser-using-pyqt5/
import os
import sys
import time

from PyQt6 import sip
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWebEngineCore import *
from PyQt6.QtWebEngineWidgets import *
from PyQt6.QtWidgets import *

import appconfig
from appconfig import Options
from cachemanager import CacheManager
from dialog import DialogsManager
from settings import Settings, DefaultSettings
from themes import Themes
from ui import Ui_MainWindow
import utils
from webpage import WebPage
from webprofile import WebProfile
from webview import WebView


class MainWindow(QMainWindow):

    # auto-hide signals
    enterHHoverSig = pyqtSignal()
    leaveHHoverSig = pyqtSignal()
    enterVHoverSig = pyqtSignal()
    leaveVHoverSig = pyqtSignal()
    enterNavBarSig = pyqtSignal()
    leaveNavBarSig = pyqtSignal()
    enterTabBarSig = pyqtSignal()
    leaveTabBarSig = pyqtSignal()

    # manage page streaming lifecycle (started and errors)
    bufferingStartedSignal = pyqtSignal(QWebEnginePage)
    streamStartedSignal = pyqtSignal(QWebEnginePage)
    mediaErrorSignal = pyqtSignal(QWebEnginePage)
    streamErrorSignal = pyqtSignal(QWebEnginePage, str)

    # constructor
    def __init__(self, new_win=False, init_tabs=None, incognito=None):
        super(MainWindow, self).__init__()

        # get Settings
        self.loadSettings(new_win, incognito)

        # configure cache and check if relaunched to delete it
        self.cache_manager = CacheManager(self.appStorageFolder)
        self.deletePreviousCache()

        # delete previous stream temp files too (for internal Qt player only)
        self.deletePreviousTemp()

        # apply main window settings
        self.configureMainWindow()

        # create UI
        self.setUI()

        # open previous tabs and child windows
        self.createTabs(init_tabs)

        # connect all signals
        self.connectSignalSlots()

    def loadSettings(self, new_win, incognito):

        # get settings
        self.settings = Settings(self, DefaultSettings.Storage.App.storageFolder, DefaultSettings.Storage.Settings.settingsFile)
        self.appStorageFolder = self.settings.settingsFolder

        # prepare new wins config, with or without initial tabs
        self.isNewWin = new_win

        # Enable/Disable cookies and prepare incognito environment
        if new_win and incognito is not None:
            self.cookies = True
            self.isIncognito = incognito
        else:
            self.cookies = self.settings.allowCookies
            self.isIncognito = False

        # set icon size (also affects to tabs and actions sizes)
        # since most "icons" are actually characters, we should also adjust fonts or stick to values between 24 and 32
        self.icon_size = int(max(24, min(32, self.settings.iconSize)))
        self.action_size = self.settings.iconSize + max(16, self.settings.iconSize // 2)

        # set auto-hide
        self.autoHide = self.settings.autoHide
        self.isPageFullscreen = False
        self.prevFullScreen = False

        # set tabbar orientation
        self.h_tabbar = self.settings.isTabBarHorizontal

    def saveSettings(self, tabs, new_wins):

        # backup .ini file
        self.settings.backupSettings()

        # save all values (even those blocked, in case .ini file didn't exist)
        self.settings.setAllowCookies(self.cookies, True)
        self.settings.setTheme(self.settings.theme, True)
        self.settings.setIncognitoTheme(self.settings.incognitoTheme, True)
        self.settings.setCustomTitleBar(self.settings.isCustomTitleBar, True)
        self.settings.setAutoHide(self.autoHide, True)
        self.settings.setTabBarHorizontal(self.h_tabbar, True)
        self.settings.setIconSize(self.settings.iconSize, True)
        self.settings.setRadius(self.settings.radius, True)
        self.settings.setPosition(self.pos(), True)
        self.settings.setSize(self.size(), True)
        self.settings.setPreviousTabs(tabs, True)
        self.settings.setNewWindows(new_wins, True)

    def configureMainWindow(self):

        # prepare initial application attributes
        appconfig.setAppAttributes(self)

        # this works but, when applied, resizing with sidegrips does not update the QWebEngine in a smooth way
        # appconfig.setGraphicsEffects(self)

        # apply style from qss folder
        if self.isIncognito:
            self.setStyleSheet(Themes.styleSheet(self.settings.incognitoTheme, Themes.Section.mainWindow))
        else:
            self.setStyleSheet(Themes.styleSheet(self.settings.theme, Themes.Section.mainWindow))

        # set initial position and size
        self.setGeometry(appconfig.appGeometry(self, self.settings.position, self.settings.size, self.settings.isCustomTitleBar, self.isNewWin))
        self.setMinimumWidth(48*16)
        self.setMinimumHeight(96)

    def setUI(self):

        # create UI
        self.ui = Ui_MainWindow(self, self.settings, self.isNewWin, self.isIncognito)

        # apply styles to independent widgets
        self.applyStyles()

        # connect all UI slots to handle requested actions
        self.connectUiSlots()

        # set cookies configuration according to settings
        self.manage_cookies(clicked=False)

        # set tabbar configuration according to orientation
        self.toggle_tabbar(clicked=False)
        self.prevTabIndex = 1

        # keep track of open popups and assure their persintence (anywaym, we are not allowing popups by now)
        self.popups = []

        # use a dialog manager to enqueue dialogs and avoid showing all at once
        self.dialog_manager = DialogsManager(self)
        self.buffer_dialogs = {}

        # pre-load icons
        self.appIcon = QIcon(DefaultSettings.Icons.appIcon)
        self.appIcon_32 = QIcon(DefaultSettings.Icons.appIcon_32)
        self.appPix = QPixmap(DefaultSettings.Icons.appIcon)
        self.appPix_32 = QPixmap(DefaultSettings.Icons.appIcon_32)
        self.web_ico = QIcon(DefaultSettings.Icons.loading)

    def applyStyles(self):

        # select normal or incognito theme
        if self.isIncognito:
            theme = self.settings.incognitoTheme
        else:
            theme = self.settings.theme

        # navigation bar styles
        self.ui.navtab.setStyleSheet(Themes.styleSheet(theme, Themes.Section.titleBar))

        # tab bar styles
        self.h_tab_style = Themes.styleSheet(theme, Themes.Section.horizontalTabs)
        self.h_tab_style = self.h_tab_style % (DefaultSettings.Icons.tabSeparator, self.action_size, int(self.action_size * 0.75))
        self.v_tab_style = Themes.styleSheet(theme, Themes.Section.verticalTabs)
        self.v_tab_style = self.v_tab_style % (self.action_size, self.action_size)
        self.ui.tabs.setStyleSheet(self.h_tab_style if self.h_tabbar else self.v_tab_style)

        # apply styles to independent widgets
        self.ui.dl_manager.setStyleSheet(Themes.styleSheet(theme, Themes.Section.downloadManager))
        self.ui.search_widget.setStyleSheet(Themes.styleSheet(theme, Themes.Section.searchWidget))

        # context menu styles
        self.ui.tabsContextMenu.setStyleSheet(Themes.styleSheet(theme, Themes.Section.contextmenu))
        self.ui.newTabContextMenu.setStyleSheet(Themes.styleSheet(theme, Themes.Section.contextmenu))

    def connectUiSlots(self):

        # navigation bar buttons
        self.ui.back_btn.triggered.connect(self.goBack)
        self.ui.next_btn.triggered.connect(self.goForward)
        self.ui.urlbar.returnPressed.connect(self.navigate_to_url)
        self.ui.reload_btn.triggered.connect(self.reloadPage)
        self.ui.ext_player_btn.triggered.connect(self.openExternalPlayer)
        self.ui.auto_btn.triggered.connect(self.manage_autohide)
        self.ui.search_off_btn.clicked.connect(self.manage_search)
        self.ui.search_on_btn.clicked.connect(self.manage_search)
        self.ui.dl_on_btn.clicked.connect(self.manage_downloads)
        self.ui.dl_off_btn.clicked.connect(self.manage_downloads)
        self.ui.cookie_btn.triggered.connect(lambda: self.manage_cookies(clicked=True))
        self.ui.clean_btn.triggered.connect(self.show_clean_dlg)
        self.ui.ninja_btn.clicked.connect(lambda: self.show_in_new_window(incognito=True))

        # window buttons if custom title bar
        if self.settings.isCustomTitleBar:
            self.ui.min_btn.triggered.connect(self.showMinimized)
            self.ui.max_btn.triggered.connect(self.showMaxRestore)
            self.ui.closewin_btn.clicked.connect(self.close)

        # tab bar events management
        self.ui.tabs.currentChanged.connect(self.current_tab_changed)
        self.ui.tabs.tabBarClicked.connect(self.tab_clicked)
        # self.ui.tabs.tabCloseRequested.connect(self.tab_closed)
        self.ui.tabs.tabBar().tabMoved.connect(self.tab_moved)
        self.ui.tabs.customContextMenuRequested.connect(self.showContextMenu)
        self.ui.newWindow_action.triggered.connect(self.show_in_new_window)

    def connectSignalSlots(self):

        # define signals for auto-hide events
        self.enterHHoverSig.connect(self.enterHHover)
        self.leaveHHoverSig.connect(self.leaveHHover)
        self.enterVHoverSig.connect(self.enterVHover)
        self.leaveVHoverSig.connect(self.leaveVHover)
        self.enterNavBarSig.connect(self.enterNavBar)
        self.leaveNavBarSig.connect(self.leaveNavBar)
        self.enterTabBarSig.connect(self.enterTabBar)
        self.leaveTabBarSig.connect(self.leaveTabBar)

        # signal to show dialog to open an external player for non-compatible media
        self.bufferingStartedSignal.connect(self.show_buffering_started)
        self.streamStartedSignal.connect(self.show_stream_started)
        self.mediaErrorSignal.connect(self.show_player_request)
        self.streamErrorSignal.connect(self.show_stream_error)

    def show(self):
        super().show()

        # setup autohide if enabled
        self.manage_autohide(enabled=self.autoHide)

        # adjust button width to tabbar width
        # self.ui.auto_btn.setFixedSize(self.ui.tabs.tabBar().width() - 3, self.ui.ninja_btn.height())

        # thanks to Maxim Paperno: https://stackoverflow.com/questions/58145272/qdialog-with-rounded-corners-have-black-corners-instead-of-being-translucent
        if self.settings.radius != 0:
            # prepare painter and mask to draw rounded corners
            rect = QRect(QPoint(0, 0), self.geometry().size())
            b = QBitmap(rect.size())
            b.fill(QColor(Qt.GlobalColor.color0))
            painter = QPainter(b)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(Qt.GlobalColor.color1)
            painter.drawRoundedRect(rect, self.settings.radius, self.settings.radius, Qt.SizeMode.AbsoluteSize)
            painter.end()
            self.setMask(b)
            self.setMask(b)

    def createTabs(self, init_tabs):

        # open all windows and their tabs
        if self.isNewWin or self.isIncognito:
            # get open tabs for child window instance
            tabs = init_tabs or DefaultSettings.Browser.defaultTabs
            # no child windows allowed for child instances
            new_wins = []
        else:
            # get open tabs for  main instance window
            tabs = self.settings.previousTabs
            # get child windows instances and their open tabs
            new_wins = self.settings.newWindows

        # add the new toggle vertical / horizontal tabs action in tab bar
        self.add_toggletab_action()

        # open all tabs in main / child window
        current = 1
        if tabs:
            for i, tab in enumerate(tabs):
                qurl, zoom, active = tab
                if active:
                    current = i + 1
                    QTimer.singleShot(0, lambda u=qurl: self.ui.urlbar.setText(u))
                self.add_tab(QUrl(qurl), zoom)

        else:
            self.add_tab(QUrl(DefaultSettings.Browser.defaultPage))
        self.ui.tabs.setCurrentIndex(current)

        # add the new tab action ("+") in tab bar
        self.add_tab_action()

        self.instances = []
        for new_tabs in new_wins:
            self.show_in_new_window(new_tabs)

    def add_tab(self, qurl, zoom=1.0, label="Loading..."):

        # create webengineview as tab widget
        browser = self.getBrowser(qurl, zoom)

        # setting tab index and default icon
        tabIndex = self.ui.tabs.addTab(browser, label if self.h_tabbar else "")

        # connect browser and page signals (once we have the tab index)
        self.connectBrowserSlots(browser, tabIndex)
        self.connectPageSlots(browser.page(), tabIndex)

        return tabIndex

    def getBrowser(self, qurl, zoom):

        # this will create the browser and apply all selected settings
        browser = WebView()
        profile = self.getProfile(browser)
        page = self.getPage(profile, browser, zoom)
        browser.setPage(page)

        browser.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)

        # setting url to browser. Using a timer (thread) it seems to load faster
        QTimer.singleShot(0, lambda u=qurl: browser.load(u))

        return browser

    def connectBrowserSlots(self, browser, tabIndex):

        # adding action to the browser when url changes
        browser.urlChanged.connect(lambda u, b=browser: self.update_urlbar(u, b))

        # check start/finish loading (e.g. for loading animations)
        browser.loadStarted.connect(lambda b=browser, index=tabIndex: self.onLoadStarted(b, index))
        browser.loadFinished.connect(lambda a, b=browser, index=tabIndex: self.onLoadFinished(a, b, index))

    def onLoadStarted(self, browser, index):
        self.ui.tabs.setTabIcon(index, self.web_ico)
        if browser == self.ui.tabs.currentWidget():
            self.ui.reload_btn.setText(self.ui.stop_char)
            self.ui.reload_btn.setToolTip("Stop loading page")

    def onLoadFinished(self, a0, browser, index):
        if browser == self.ui.tabs.currentWidget():
            self.ui.reload_btn.setText(self.ui.reload_char)
            self.ui.reload_btn.setToolTip("Reload page")

    def getProfile(self, browser):

        if self.isIncognito:
            # apply no persistent cache
            cache_path = None
        elif self.cache_manager.lastCache:
            # apply temporary cache location to delete all previous cache when app is closed, but keeping these last
            cache_path = self.cache_manager.lastCache
        else:
            # apply application cache location
            cache_path = self.cache_manager.cachePath

        profile = WebProfile(cache_path, browser, self.cookie_filter)

        return profile

    def getPage(self, profile, browser, zoom):

        # this will create the page and apply all selected settings
        page = WebPage(profile, browser, self.bufferingStartedSignal, self.streamStartedSignal, self.mediaErrorSignal, self.streamErrorSignal)

        # set page zoom factor
        page.setZoomFactor(zoom)

        # customize browser context menu
        self.setPageContextMenu(page)

        return page

    def setPageContextMenu(self, page):

        # manage context menu options (only those not already working out-of-the-box)
        if self.isNewWin:
            act2 = page.action(page.WebAction.OpenLinkInNewWindow)
            act2.disconnect()
            act2.setVisible(False)
        else:
            page.newWindowRequested.connect(self.openLinkRequested)
        inspect_act = page.action(page.WebAction.ViewSource)
        self.inspector = QWebEngineView()
        inspect_act.disconnect()
        inspect_act.triggered.connect(lambda checked, p=page: self.inspect_page(p))

    def connectPageSlots(self, page, tabIndex):

        # manage fullscreen requests (enabled at browser level)
        page.fullScreenRequested.connect(self.page_fullscr)

        # Preparing asking for permissions
        page.featurePermissionRequested.connect(lambda origin, feature, p=page: self.show_feature_request(origin, feature, p))
        # Are these included in previous one? or the opposite? or none?
        # page.permissionRequested.connect(lambda request, p=page: self.show_permission_request(request, p))
        page.fileSystemAccessRequested.connect(lambda request, p=page: print("FS ACCESS REQUESTED", request))
        page.desktopMediaRequested.connect(lambda request, p=page: print("MEDIA REQUESTED", request))
        # how to fix this (live video)?
        # JavaScriptConsoleMessageLevel.ErrorMessageLevel requestStorageAccessFor: Permission denied. 0 https://www.youtube.com/watch?v=cj-CoeHpXWQ

        # adding action to the browser when title or icon change
        page.titleChanged.connect(lambda title, index=tabIndex: self.title_changed(title, index))
        page.iconChanged.connect(lambda icon, index=tabIndex: self.icon_changed(icon, index))

        # manage file downloads (including pages and files)
        page.profile().downloadRequested.connect(self.download_file)

    def page_fullscr(self, request):
        self.manage_fullscr(request.toggleOn(), page_fullscr=True)
        request.accept()
        request.accept()

    def manage_fullscr(self, on, page_fullscr=False):

        if on:
            if page_fullscr:
                self.isPageFullscreen = True
                self.manage_autohide(hide_all=True)
                if self.isFullScreen():
                    self.prevFullScreen = True
            if not self.isFullScreen():
                for w in self.ui.appGrips.sideGrips + self.ui.appGrips.cornerGrips:
                    w.hide()
                self.showFullScreen()
                self.moveOtherWidgets()

        else:
            if page_fullscr:
                self.isPageFullscreen = False
                self.manage_autohide(hide_all=False)
            if not page_fullscr or (page_fullscr and not self.prevFullScreen):
                for w in self.ui.appGrips.sideGrips + self.ui.appGrips.cornerGrips:
                    w.show()
                self.showNormal()
                self.moveOtherWidgets()

    def show_feature_request(self, origin, feature=None, page=None):
        icon = page.icon().pixmap(QSize(self.icon_size, self.icon_size))
        title = page.title() or page.url().toString()
        message = "This page is asking for your permission to %s." % (DefaultSettings.FeatureMessages[feature])
        theme = self.settings.incognitoTheme if self.isIncognito else self.settings.theme
        self.dialog_manager.createDialog(
            parent=self,
            theme=theme,
            icon=icon,
            title=title,
            message=message,
            getPosFunc=self.targetDlgPos,
            acceptedSlot=(lambda o=origin, f=feature: page.accept_feature(o, f)),
            rejectedSlot=(lambda o=origin, f=feature: page.reject_feature(o, f))
        )

    def show_permission_request(self, request, page):
        icon = page.icon().pixmap(QSize(self.icon_size, self.icon_size))
        title = page.title() or page.url().toString()
        message = "This page is asking for your permission to %s." % (DefaultSettings.FeatureMessages[request.type()])
        theme = self.settings.incognitoTheme if self.isIncognito else self.settings.theme
        self.dialog_manager.createDialog(
            parent=self,
            theme=theme,
            icon=icon,
            title=title,
            message=message,
            getPosFunc=self.targetDlgPos,
            acceptedSlot=request.grant,
            rejectedSlot=request.deny
        )

    @pyqtSlot(QWebEnginePage)
    def show_player_request(self, page):
        icon = page.icon().pixmap(QSize(self.icon_size, self.icon_size))
        title = page.title() or page.url().toString()
        message = "This page contains non-compatible media.\n\n" \
                  "Do you want to try to load it using an external player?"
        theme = self.settings.incognitoTheme if self.isIncognito else self.settings.theme
        self.dialog_manager.createDialog(
            parent=self,
            theme=theme,
            icon=icon,
            title=title,
            message=message,
            getPosFunc=self.targetDlgPos,
            acceptedSlot=page.accept_player,
            rejectedSlot=page.reject_player
        )

    @pyqtSlot(QWebEnginePage)
    def show_buffering_started(self, page):
        icon = page.icon().pixmap(QSize(self.icon_size, self.icon_size))
        title = page.title() or page.url().toString()
        message = ("Buffering content to stream to external player.\n\n"
                   "Your stream will start soon, please be patient.")
        theme = self.settings.incognitoTheme if self.isIncognito else self.settings.theme
        page: QWebEnginePage = page
        self.buffer_dialogs[str(page)] = self.dialog_manager.createDialog(
            parent=self,
            theme=theme,
            icon=icon,
            title=title,
            message=message,
            buttons=QDialogButtonBox.StandardButton.Ok,
            getPosFunc=self.targetDlgPos
        )

    @pyqtSlot(QWebEnginePage)
    def show_stream_started(self, page):
        dialog = self.buffer_dialogs.get(str(page), None)
        if dialog is not None:
            if not sip.isdeleted(dialog):
                if dialog.isVisible():
                    dialog.close()
                else:
                    self.dialog_manager.deleteDialog(dialog)
                    self.dialog_manager.deleteDialog(dialog)
            del self.buffer_dialogs[str(page)]

    @pyqtSlot(QWebEnginePage, str)
    def show_stream_error(self, page, error):
        icon = page.icon().pixmap(QSize(self.icon_size, self.icon_size))
        title = page.title() or page.url().toString()
        message = ("There has been a problem while trying to stream this page.\n\n"
                   "%s\n\n" % error)
        theme = self.settings.incognitoTheme if self.isIncognito else self.settings.theme
        self.dialog_manager.createDialog(
            parent=self,
            theme=theme,
            icon=icon,
            title=title,
            message=message,
            buttons=QDialogButtonBox.StandardButton.Ok,
            getPosFunc=self.targetDlgPos
        )

    def title_changed(self, title, i):
        self.ui.tabs.tabBar().setTabText(i, (("  " + title[:20]) if len(title) > 20 else title) if self.h_tabbar else "")
        self.ui.tabs.setTabToolTip(i, title + ("" if self.h_tabbar else "\n(Right-click to close)"))

    def icon_changed(self, icon, i):

        # works fine but sometimes it takes too long (0,17sec.)...
        # TODO: find another way (test with github site)
        # icon = utils.fixDarkImage(icon, self.icon_size, self.icon_size)

        if self.h_tabbar:
            new_icon = icon
        else:
            # icon rotation is required if not using custom painter in TabBar class
            new_icon = QIcon(icon.pixmap(QSize(self.icon_size, self.icon_size)).transformed(QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation))
        self.ui.tabs.tabBar().setTabIcon(i, new_icon)

    def add_toggletab_action(self):
        self.toggletab_btn = QLabel()
        self.ui.tabs.insertTab(0, self.toggletab_btn, " ▼ ") #🢃⯯⛛▼🞃▼⮟⬎
        self.ui.tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self.ui.tabs.widget(0).setDisabled(True)

    def add_tab_action(self):
        self.addtab_btn = QLabel()
        i = self.ui.tabs.addTab(self.addtab_btn, " ✚ ")
        self.ui.tabs.tabBar().setTabButton(i, QTabBar.ButtonPosition.RightSide, None)
        self.ui.tabs.widget(i).setDisabled(True)
        self.ui.tabs.tabBar().setTabToolTip(i, "New tab")

    # method for adding new tab when requested by user
    def add_new_tab(self, qurl=None):
        self.ui.tabs.removeTab(self.ui.tabs.count() - 1)
        i = self.add_tab(qurl or QUrl(DefaultSettings.Browser.defaultPage))
        self.add_tab_action()
        self.ui.tabs.setCurrentIndex(i)
        self.update_urlbar(self.ui.tabs.currentWidget().url(), self.ui.tabs.currentWidget())

    # method to update the url when tab is changed
    def navigate_to_url(self):

        # get the line edit text and convert it to QUrl object
        qurl = QUrl(self.ui.urlbar.text())

        # if scheme is blank
        if not qurl.isValid() or "." not in qurl.url() or " " in qurl.url():
            # search in Google
            # qurl.setUrl("https://www.google.es/search?q=%s&safe=off" % self.urlbar.text())
            # search in DuckDuckGo (safer)
            qurl.setUrl("https://duckduckgo.com/?t=h_&hps=1&start=1&q=%s&ia=web&kae=d" % self.ui.urlbar.text().replace(" ", "+"))

        elif qurl.scheme() == "":
            # set scheme
            qurl.setScheme("https")

        # set the url
        QTimer.singleShot(0, lambda u=qurl: self.ui.tabs.currentWidget().load(u))

    def update_urlbar(self, qurl, browser: QWidget = None):

        # If this signal is not from the current tab, ignore
        if browser != self.ui.tabs.currentWidget():
            # do nothing
            return

        # set text to the url bar
        self.ui.urlbar.setText(qurl.toString())

        # Enable/Disable navigation arrows according to page history
        self.ui.back_btn.setEnabled(browser.history().canGoBack())
        self.ui.next_btn.setEnabled(browser.history().canGoForward())

    def current_tab_changed(self, i):

        if i == 0:
            self.ui.tabs.setCurrentIndex(self.prevTabIndex or 1)

        if i < self.ui.tabs.count() - 1:

            # update the url
            self.update_urlbar(self.ui.tabs.currentWidget().url(), self.ui.tabs.currentWidget())

            if self.ui.tabs.currentWidget().page().isLoading():
                self.ui.reload_btn.setText(self.ui.stop_char)
                self.ui.reload_btn.setToolTip("Stop loading page")
            else:
                self.ui.reload_btn.setText(self.ui.reload_char)
                self.ui.reload_btn.setToolTip("Reload page")

        if self.ui.search_widget.isVisible():
            self.ui.tabs.currentWidget().findText("")
            self.ui.search_widget.hide()

    def tab_clicked(self, i):
        if QApplication.mouseButtons() == Qt.MouseButton.LeftButton:
            if i == 0:
                self.prevTabIndex = self.ui.tabs.currentIndex()
                self.toggle_tabbar(clicked=True)
            elif i == self.ui.tabs.count() - 1:
                # this is needed to immediately refresh url bar content (maybe locked by qwebengineview?)
                QTimer.singleShot(0, lambda p=DefaultSettings.Browser.defaultPage: self.ui.urlbar.setText(p))
                self.add_new_tab()

    def tab_moved(self, to_index, from_index):

        # updating index-dependent signals when tab is moved
        # destination tab
        self.update_index_dependent_signals(to_index)

        if to_index == self.ui.tabs.count() - 1:
            # Avoid moving last tab (add new tab) if dragging another tab onto it
            self.ui.tabs.removeTab(from_index)
            self.add_tab_action()

        elif to_index == 0:
            # Avoid moving first tab (toggle tab orientation) if dragging another tab onto it
            self.ui.tabs.removeTab(from_index)
            self.add_toggletab_action()

        else:
            # origin tab
            self.update_index_dependent_signals(from_index)

    def tab_closed(self, tabIndex):

        # if there is only one tab
        if self.ui.tabs.count() == 3:
            if self.isNewWin:
                # close additional window only
                self.close()
            else:
                # close application
                QCoreApplication.quit()

        else:
            # calculate next tab position
            targetIndex = self.ui.tabs.currentIndex() if tabIndex != self.ui.tabs.currentIndex() else self.ui.tabs.currentIndex() + 1

            # just removing the tab doesn't destroy associated widget
            self.ui.tabs.widget(tabIndex).deleteLater()
            # remove the tab
            self.ui.tabs.removeTab(tabIndex)

            # adjust target tab index according to new tabs number (but not tab 0, the toggle button)
            if targetIndex >= self.ui.tabs.count() - 1:
                targetIndex = self.ui.tabs.count() - 2
            elif targetIndex <= 0:
                targetIndex = 1
            self.ui.tabs.setCurrentIndex(targetIndex)

        # updating index-dependent signals when tab is moved
        for i in range(tabIndex, self.ui.tabs.count() - 1):
            self.update_index_dependent_signals(i)

    # method for navigate to url
    def update_index_dependent_signals(self, tabIndex):
        browser = self.ui.tabs.widget(tabIndex)
        browser.loadStarted.disconnect()
        browser.loadStarted.connect(lambda b=browser, index=tabIndex: self.onLoadStarted(b, index))
        browser.loadFinished.disconnect()
        browser.loadFinished.connect(lambda a, b=browser, index=tabIndex: self.onLoadFinished(a, b, index))

        page = browser.page()
        page.titleChanged.disconnect()
        page.titleChanged.connect(lambda title, index=tabIndex: self.title_changed(title, index))
        page.iconChanged.disconnect()
        page.iconChanged.connect(lambda icon, index=tabIndex: self.icon_changed(icon, index))

    def showContextMenu(self, point):
        tabIndex = self.ui.tabs.tabBar().tabAt(point)
        if 1 <= tabIndex < self.ui.tabs.count() - 1:
            self.createCloseTabContextMenu(tabIndex)
        elif tabIndex == self.ui.tabs.count() - 1:
            self.createNewTabContextMenu(tabIndex)

    def createCloseTabContextMenu(self, i):
        text = self.ui.tabs.tabBar().tabToolTip(i).replace("\n(Right-click to close)", "")
        self.ui.close_action.setText('Close tab: "' + text + '"')
        self.ui.close_action.triggered.disconnect()
        self.ui.close_action.triggered.connect(lambda checked, index=i: self.tab_closed(index))
        first_tab_rect = self.ui.tabs.tabBar().tabRect(0)
        first_tab_height =  first_tab_rect.height()
        tab_rect = self.ui.tabs.tabBar().tabRect(i)
        tab_width = tab_rect.width()
        tab_height = tab_rect.height()
        pos = QPoint(self.ui.tabs.tabBar().x() + tab_width, self.ui.tabs.tabBar().y() + first_tab_height + (tab_height * (i - 1)))
        self.ui.tabsContextMenu.exec(self.ui.tabs.mapToGlobal(pos))

    def createNewTabContextMenu(self, i):
        first_tab_rect = self.ui.tabs.tabBar().tabRect(0)
        first_tab_height =  first_tab_rect.height()
        tab_rect = self.ui.tabs.tabBar().tabRect(i)
        tab_width = tab_rect.width()
        tab_height = tab_rect.height()
        pos = QPoint(self.ui.tabs.tabBar().x() + tab_width, self.ui.tabs.tabBar().y() + first_tab_height + (tab_height * i))
        self.ui.newTabContextMenu.exec(self.ui.tabs.mapToGlobal(pos))

    def openLinkRequested(self, request):

        if request.destination() == QWebEngineNewWindowRequest.DestinationType.InNewWindow:
            self.show_in_new_window([[request.requestedUrl().toString(), 1.0, True]])

        elif request.destination() == QWebEngineNewWindowRequest.DestinationType.InNewTab:
            self.add_new_tab(request.requestedUrl())

        elif request.destination() == QWebEngineNewWindowRequest.DestinationType.InNewDialog:
            if request.isUserInitiated():
                self.show_in_new_dialog(request)
        #     else:
        #         # This would allow popups... something we don't want, of course
        #         self.show_in_new_dialog(request)

    def show_in_new_window(self, tabs=None, incognito=None):

        if not self.isNewWin:
            w = MainWindow(new_win=True, init_tabs=tabs, incognito=incognito)
            self.instances.append(w)
            w.show()

    def show_in_new_dialog(self, request):

        popup = QWebEngineView()
        geom = request.requestedGeometry()
        popup.setGeometry(50 if geom.x() < 50 else geom.x(), 50 if geom.y() < 50 else geom.y(), geom.width(), geom.height())
        popup.load(request.requestedUrl())
        self.popups.append(popup)
        popup.show()

    def inspect_page(self, p):

        self.inspector.page().setInspectedPage(p)
        self.inspector.setWindowTitle("Web Inspector - " + p.title())
        self.inspector.show()

    def toggle_tabbar(self, clicked=True):

        if clicked:
            self.h_tabbar = not self.h_tabbar

            for i in range(1, self.ui.tabs.count() - 1):
                icon = self.ui.tabs.widget(i).page().icon()
                if not icon.availableSizes():
                    icon = self.web_ico
                if self.h_tabbar:
                    self.title_changed(self.ui.tabs.widget(i).page().title(), i)
                    new_icon = icon
                else:
                    self.ui.tabs.tabBar().setTabText(i, "")
                    new_icon = QIcon(icon.pixmap(QSize(self.icon_size, self.icon_size)).transformed(QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation))
                self.ui.tabs.tabBar().setTabIcon(i, new_icon)

        if self.isIncognito:
            theme = self.settings.incognitoTheme
        else:
            theme = self.settings.theme

        self.ui.tabs.setStyleSheet(Themes.styleSheet(theme, Themes.Section.horizontalTabs) if self.h_tabbar else Themes.styleSheet(theme, Themes.Section.verticalTabs))
        self.ui.tabs.setTabPosition(QTabWidget.TabPosition.North if self.h_tabbar else QTabWidget.TabPosition.West)
        self.ui.tabs.setTabsClosable(self.h_tabbar)
        self.ui.tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self.ui.tabs.tabBar().setTabButton(self.ui.tabs.count() - 1, QTabBar.ButtonPosition.RightSide, None)
        self.ui.tabs.tabBar().setStyleSheet(self.h_tab_style if self.h_tabbar else self.v_tab_style)
        self.ui.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu if self.h_tabbar else Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.tabs.setTabToolTip(0, "Set %s tabs" % ("vertical" if self.h_tabbar else "horizontal"))

        if self.autoHide:
            if self.h_tabbar:
                self.ui.tabs.tabBar().show()
            if hasattr(self, "hoverHWidget"):
                self.hoverHWidget.show()
            if hasattr(self, "hoverVWidget"):
                if self.h_tabbar:
                    self.hoverVWidget.hide()
                else:
                    self.hoverVWidget.show()

    def goBack(self):
        self.ui.tabs.currentWidget().back()

    def goForward(self):
        self.ui.tabs.currentWidget().forward()

    def reloadPage(self):
        if self.ui.reload_btn.text() == self.ui.reload_char:
            QTimer.singleShot(0, lambda: self.ui.tabs.currentWidget().reload())
        else:
            self.ui.tabs.currentWidget().stop()

    def get_search_widget_pos(self):

        # getting title bar height (custom or standard)
        gap = self.mapToGlobal(self.ui.navtab.pos()).y() - self.y()

        # take the visible action as reference to calculate position
        refWidget = self.ui.search_off_btn if self.ui.search_off_btn.isVisible() else self.ui.search_on_btn

        # calculate position
        actRect = refWidget.geometry()
        actPos = self.mapToGlobal(actRect.topLeft())
        x = actPos.x() + actRect.width() - self.ui.search_widget.width()
        y = self.y() + self.ui.navtab.height() + gap
        return QPoint(x, y)

    def manage_search(self):

        if self.ui.search_widget.isVisible():
            self.ui.tabs.currentWidget().findText("")
            self.ui.search_widget.hide()
            self.ui.search_off_act.setVisible(False)
            self.ui.search_on_act.setVisible(True)

        else:
            self.ui.search_widget.show()
            self.ui.search_widget.move(self.get_search_widget_pos())
            self.ui.search_off_act.setVisible(True)
            self.ui.search_on_act.setVisible(False)

    def searchPage(self, checked, forward):
        textToFind = self.ui.search_widget.getText()
        if textToFind:
            if forward:
                self.ui.tabs.currentWidget().findText(textToFind)
            else:
                self.ui.tabs.currentWidget().findText(textToFind, QWebEnginePage.FindFlag.FindBackward)

    def openExternalPlayer(self):
        page = self.ui.tabs.currentWidget().page()
        page.openInExternalPlayer()

    def manage_autohide(self, checked=False, enabled=None, hide_all=False):

        self.autoHide = not self.autoHide if enabled is None else enabled

        if hide_all:
            self.ui.navtab.hide()
            self.ui.navtab.hide()
            self.ui.tabs.tabBar().hide()
            self.ui.hoverHWidget.hide()
            self.ui.hoverVWidget.hide()

        else:

            self.ui.auto_btn.setText(self.ui.auto_on_char if self.autoHide else self.ui.auto_off_char)
            self.ui.auto_btn.setToolTip("Auto-hide is now " + ("Enabled" if self.autoHide else "Disabled"))

            if self.autoHide:
                self.ui.navtab.hide()
                self.ui.tabs.tabBar().hide()
                if not self.ui.hoverHWidget.isVisible() and not self.ui.hoverHWidget.underMouse():
                    # this... fails sometimes???? WHY?????
                    # Hypothesis: if nav tab is under mouse it will not hide, so trying to show hoverHWidget in the same position fails
                    self.ui.hoverHWidget.show()
                if not self.h_tabbar:
                    self.ui.hoverVWidget.show()
                else:
                    self.ui.hoverVWidget.hide()

            else:
                self.ui.hoverHWidget.hide()
                self.ui.hoverVWidget.hide()
                self.ui.navtab.show()
                self.ui.tabs.tabBar().show()

    @pyqtSlot()
    def enterHHover(self):
        if self.autoHide:
            self.ui.hoverHWidget.hide()
            self.ui.navtab.show()
            if self.h_tabbar:
                self.ui.tabs.tabBar().show()

    @pyqtSlot()
    def leaveHHover(self):
        pass

    @pyqtSlot()
    def enterVHover(self):
        if self.autoHide:
            self.ui.hoverVWidget.hide()
            self.ui.tabs.tabBar().show()

    @pyqtSlot()
    def leaveVHover(self):
        pass

    @pyqtSlot()
    def enterNavBar(self):
        pass

    @pyqtSlot()
    def leaveNavBar(self):
        if self.autoHide:
            if self.h_tabbar:
                if not self.underMouse():
                    self.ui.navtab.hide()
                    self.ui.tabs.tabBar().hide()
                    self.ui.hoverHWidget.show()
            else:
                self.ui.navtab.hide()
                self.ui.hoverHWidget.show()

    @pyqtSlot()
    def enterTabBar(self):
        pass

    @pyqtSlot()
    def leaveTabBar(self):
        if self.autoHide:
            if self.h_tabbar:
                if not self.ui.navtab.rect().contains(self.mapFromGlobal(QCursor.pos())):
                    self.ui.navtab.hide()
                    self.ui.tabs.tabBar().hide()
                    self.ui.hoverHWidget.show()
            else:
                self.ui.tabs.tabBar().hide()
                self.ui.hoverVWidget.show()

    def manage_downloads(self):

        if self.ui.dl_manager.isVisible():
            self.ui.dl_on_act.setVisible(True)
            self.ui.dl_off_act.setVisible(False)
            self.ui.dl_manager.hide()

        else:
            self.ui.dl_on_act.setVisible(False)
            self.ui.dl_off_act.setVisible(True)
            self.show_dl_manager()

    def get_dl_manager_pos(self):

        # getting title bar height (custom or standard)
        gap = self.mapToGlobal(self.ui.navtab.pos()).y() - self.y()

        # calculate position
        x = self.x() + self.width() - self.ui.dl_manager.width()
        y = self.y() + self.ui.navtab.height() + gap
        return QPoint(x, y)

    def show_dl_manager(self):

        self.ui.dl_on_act.setVisible(False)
        self.ui.dl_off_act.setVisible(True)
        self.ui.dl_manager.show()
        self.ui.dl_manager.move(self.get_dl_manager_pos())

    # adding action to download files
    def download_file(self, item: QWebEngineDownloadRequest):
        if self.ui.dl_manager.addDownload(item):
            self.show_dl_manager()

    def manage_cookies(self, clicked):

        if clicked:
            self.cookies = not self.cookies
        self.ui.cookie_btn.setText("🍪" if self.cookies else "⛔")
        self.ui.cookie_btn.setToolTip("Cookies are now %s" % ("enabled" if self.cookies else "disabled"))

    def cookie_filter(self, cookie, origin=None):
        ret = self.cookies and (not cookie.thirdParty or (cookie.thirdParty and DefaultSettings.Cookies.allowThirdParty))
        # print(f"accepted: {ret}, "
        #       f"firstPartyUrl: {cookie.firstPartyUrl.toString()}, "
        #       f"origin: {cookie.origin.toString()}, "
        #       f"thirdParty? {cookie.thirdParty}"
        #       )
        return ret

    def show_clean_dlg(self):
        # Prepare clean all warning dialog
        icon = self.appPix_32
        title = "Warning!"
        message = "This will erase all your history and stored cookies.\n\n" \
                  "Are you sure you want to proceed?"
        theme = self.settings.incognitoTheme if self.isIncognito else self.settings.theme
        self.dialog_manager.createDialog(
            parent=self,
            theme=theme,
            icon=icon,
            title=title,
            message=message,
            getPosFunc=self.targetDlgPos,
            acceptedSlot=self.accept_clean,
            rejectedSlot=self.reject_clean
        )

    def accept_clean(self):

        if not self.isIncognito:
            # activate cache deletion upon closing app (if not incognito which will be auto-deleted)
            self.cache_manager.deleteCache = True

            # set a new cache folder (old ones will be deleted when app is restarted)
            self.cache_manager.lastCache = os.path.join(self.cache_manager.cachePath, str(time.time()).replace(".", ""))

        # fresh-reload all pages
        tabsCount = self.ui.tabs.count()
        currIndex = self.ui.tabs.currentIndex()
        self.ui.tabs.setCurrentIndex(1)

        tabs = []
        for i in range(1, tabsCount - 1):
            browser: QWebEngineView = self.ui.tabs.widget(0)
            page: QWebEnginePage = browser.page()
            tabs.append([page.url(), page.zoomFactor()])
            browser.deleteLater()
            self.ui.tabs.removeTab(0)

        self.ui.tabs.remove(0)

        for item in tabs:
            url, zoom = item
            # new cache storage will be assigned in add_tab() method
            self.add_tab(url, zoom)

        self.add_tab_action()
        self.ui.tabs.setCurrentIndex(currIndex)

    def reject_clean(self):
        pass

    def showMaxRestore(self):

        if self.isMaximized():
            self.showNormal()
            self.ui.max_btn.setText(" ⃞ ")
            self.ui.max_btn.setToolTip("Maximize")

        else:
            self.showMaximized()
            self.ui.max_btn.setText("⧉")
            self.ui.max_btn.setToolTip("Restore")

    def keyReleaseEvent(self, a0):

        if a0.key() == Qt.Key.Key_Escape:
            if self.ui.urlbar.hasFocus():
                text = self.ui.tabs.currentWidget().url().toString()
                self.ui.urlbar.setText(self.ui.tabs.currentWidget().url().toString())
                self.ui.urlbar.setCursorPosition(len(text))

            elif self.isFullScreen():
                if not self.isPageFullscreen:
                    self.manage_fullscr(on=False)

        elif a0.key() == Qt.Key.Key_F:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.manage_search()

        elif a0.key() == Qt.Key.Key_T:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.add_new_tab()

        elif a0.key() == Qt.Key.Key_N:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier:
                self.show_in_new_window(incognito=True)
            elif a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.show_in_new_window()

        elif a0.key() == Qt.Key.Key_W:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.tab_closed(self.ui.tabs.currentIndex())

        elif a0.key() == Qt.Key.Key_F11:
            if not self.isPageFullscreen:
                self.manage_fullscr(on=not self.isFullScreen())

        elif a0.key() == Qt.Key.Key_A:
            self.manage_autohide(enabled=False)

    def targetDlgPos(self):
        return QPoint(self.x() + 100,
                      self.y() + self.ui.navtab.height() + (
                          self.ui.tabs.tabBar().height() if self.h_tabbar else 0))

    # these widgets have a relative position. Must be moved AFTER showing main window
    def moveOtherWidgets(self):

        if hasattr(self, "dl_manager") and self.dl_manager.isVisible():
            # reposition download list
            self.dl_manager.move(self.get_dl_manager_pos())

        if hasattr(self, "search_widget") and self.search_widget.isVisible():
            # reposition search widget
            self.search_widget.move(self.get_search_widget_pos())

        if self.dialog_manager.showingDlg and self.dialog_manager.currentDialog is not None:
            self.dialog_manager.currentDialog.move(self.targetDlgPos())

    def moveEvent(self, a0):

        # also move widgets with relative positions
        self.moveOtherWidgets()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self.settings.isCustomTitleBar:
            # update grip areas
            self.ui.appGrips.updateGrips()

            # adjust to screen edges:
            mousePos = QCursor.pos()
            screenSize = utils.screenSize(self)
            if -5 < mousePos.y() < 5 or screenSize.height() - 5 < mousePos.y() < screenSize.height() + 5:
                self.setGeometry(self.x(), 0, self.width(), screenSize.height())

        # update hover areas (doesn't matter if visible or not)
        self.ui.hoverHWidget.setGeometry(0, 0, self.width(), 20)
        self.ui.hoverVWidget.setGeometry(0, self.action_size, 20, self.height())

        # also move other widgets with relative positions
        self.moveOtherWidgets()

    def deletePreviousCache(self):
        if self.cache_manager.checkDeleteCache():
            self.cache_manager.deleteCache()
            QApplication.quit()
            sys.exit(0)

    def deletePreviousTemp(self):
        if Options.DeletePlayerTemp in sys.argv:
            if os.path.exists(DefaultSettings.Player.streamTempFile):
                try:
                    os.remove(DefaultSettings.Player.streamTempFile)
                except:
                    pass
            if os.path.exists(DefaultSettings.Player.streamTempFile_2):
                try:
                    os.remove(DefaultSettings.Player.streamTempFile_2)
                except:
                    pass
            QApplication.quit()
            sys.exit(0)

    def closeEvent(self, a0):

        # close all other widgets and processes
        self.ui.dl_manager.cancelAllDownloads()
        self.ui.dl_manager.close()
        self.ui.search_widget.close()
        self.ui.hoverHWidget.close()
        self.ui.hoverVWidget.close()
        self.inspector.close()
        # this may not exist (whilst others may be queued)
        try:
            self.dialog_manager.currentDialog.close()
        except:
            pass

        # save open tabs and close external players
        tabs = []
        for i in range(1, self.ui.tabs.count() - 1):
            browser = self.ui.tabs.widget(i)
            page = browser.page()
            page.closeExternalPlayer(False)
            tabs.append([browser.url().toString(), browser.page().zoomFactor(), i == self.ui.tabs.currentIndex()])

        # save other open windows
        # only open windows when main instance is closed will be remembered
        new_wins = []
        for w in self.instances:

            # check if window is still open
            if w.isVisible():

                # saving open tabs for each instance and closing external players
                new_tabs = []
                for i in range(1, w.ui.tabs.count() - 1):
                    browser = w.ui.tabs.widget(i)
                    page = browser.page()
                    page.closeExternalPlayer(False)
                    new_tabs.append([browser.url().toString(), browser.page().zoomFactor(), i == w.ui.tabs.currentIndex()])

                # won't keep any incognito data
                if not w.isIncognito:
                    new_wins.append(new_tabs)

            # closing all other open child windows
            w.close()

        # only main window can save settings
        if not self.isNewWin and not self.isIncognito:
            self.saveSettings(tabs, new_wins)

        args = []
        if self.cache_manager.deleteCache and not self.isNewWin and not self.isIncognito:
            # restart app to wipe all cache folders but the last one (not possible while running since it's locked)
            args += [appconfig.Options.DeleteCache] + [self.cache_manager.lastCache]

        if (os.path.exists(DefaultSettings.Player.streamTempFile) or
                os.path.exists(DefaultSettings.Player.streamTempFile_2)):
            args += [appconfig.Options.DeletePlayerTemp]

        if args:
            status = QProcess.startDetached(sys.executable, sys.argv + args)


def main():

    # Qt is DPI-Aware, so all this is not likely required
    # setDPIAwareness()
    # setSystemDPISettings()
    # setApplicationDPISettings()

    utils.set_widevine_var(os.path.join("externalplayer", "widevine", "widevinecdm.dll"))

    # creating a PyQt5 application and (windows only) force dark mode
    app = QApplication(sys.argv + ['-platform', 'windows:darkmode=1'])

    # setting name to the application
    # app.setApplicationName("Coward")
    # app.setWindowIcon(QIcon(resource_path("res/coward.png")))

    if not utils.is_packaged():
        # change application icon even when running as Python script
        utils.force_icon('kalmat.coward.nav.01')

        # This will allow to show some tracebacks (not all, anyway)
        sys._excepthook = sys.excepthook
        sys.excepthook = utils.exception_hook

    # creating and showing MainWindow object
    window = MainWindow()
    window.show()

    # loop
    app.exec()


if __name__ == "__main__":
    main()
