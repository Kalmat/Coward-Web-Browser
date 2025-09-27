# based on: https://www.geeksforgeeks.org/python/creating-a-tabbed-browser-using-pyqt5/
import hashlib
import os
import shutil
import sys
import time

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWebEngineCore import *
from PyQt6.QtWebEngineWidgets import *
from PyQt6.QtWidgets import *

import appconfig
import utils
from appconfig import OPTIONS
from cachemanager import CacheManager
from dialog import DialogsManager
from downloadmanager import DownloadManager
from historymanager import History, HistoryWidget
from logger import LOGGER, LoggerSettings
from mediaplayer import HttpManager
from searchwidget import SearchWidget
from settings import Settings, DefaultSettings
from themes import Themes
from ui import Ui_MainWindow
from webpage import WebPage
from webprofile import WebProfile, RequestInterceptor
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

    # load history url
    loadHistoryUrlSig = pyqtSignal(QUrl)

    # constructor
    def __init__(self, new_win=False, init_tabs=None, incognito=None):
        super(MainWindow, self).__init__()

        # get Settings
        self.loadSettings(new_win, incognito)

        # create and initialize independent widgets and variables
        self.commonSetup()

        # apply main window settings
        self.configureMainWindow()

        # create UI
        self.setupUI()

        # open previous tabs and child windows
        self.createTabs(init_tabs)

        # connect all signals
        self.connectSignalSlots()

        LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Finished initialization")

    def loadSettings(self, new_win, incognito):

        # get settings
        self.settings = Settings(self)

        # custom storage for browser profile aimed to persist cookies, cache, etc.
        self.appStorageFolder = self.settings.settingsFolder

        # prepare new wins config, with or without initial tabs
        self.isNewWin = new_win

        # Enable/Disable cookies and prepare incognito environment
        if (new_win and incognito is not None) or OPTIONS.incognitoMode:
            self.cookies = True
            self.isIncognito = OPTIONS.incognitoMode if OPTIONS.incognitoMode is not None else incognito
        else:
            self.cookies = self.settings.allowCookies
            self.isIncognito = False

        # Enable/disabling froce dark mode in pages
        self.dark_mode = self.settings.forceDark

        # set icon size (also affects to tabs and actions sizes)
        # since most "icons" are actually characters, we should also adjust fonts or stick to values between 24 and 32
        self.icon_size = int(max(24, min(32, self.settings.iconSize)))
        self.action_size = self.settings.iconSize + max(16, self.settings.iconSize // 2)
        self.h_tab_size = self.icon_size + 8
        self.small_action_size = self.action_size - 16

        # set auto-hide
        self.autoHide = self.settings.autoHide
        self.isPageFullscreen = False
        self.prevFullScreen = False

        # set tabbar orientation
        self.h_tabbar = self.settings.isTabBarHorizontal

        LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Settings loaded")

    def saveSettings(self, tabs, new_wins):

        # backup .ini file
        self.settings.backupSettings()

        # save all values (even those which are internal by the moment, in case .ini file didn't exist)
        self.settings.setAllowCookies(self.cookies, True)
        self.settings.setTheme(self.settings.theme, True)
        self.settings.setForceDark(self.dark_mode, True)
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

        LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Settings saved")

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

        LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Main Window configured")

    def commonSetup(self):

        # configure cache
        self.cache_manager = CacheManager(self.appStorageFolder)

        # check if relaunched to delete cache (when using "clean all" option) or temp files
        self.deletePreviousCacheAndTemp()

        # webpage common profile to keep session logins, cookies, etc.
        self._profile = None

        # Request interceptor for blocking URLs and ad-blocking
        self.requestInterceptor = RequestInterceptor(DefaultSettings.AdBlocker.urlBlackList,
                                                     os.path.join(self.appStorageFolder, DefaultSettings.AdBlocker.filterlistsFolder))

        # creating download manager before custom title bar to allow moving it too
        self.dl_manager = DownloadManager(self)
        self.dl_manager.hide()

        # creating search widget before custom title bar to allow moving it too
        self.search_widget = SearchWidget(self, self.searchPage)
        self.search_widget.hide()

        # use a dialog manager to enqueue dialogs and avoid showing all at once
        self.dialog_manager = DialogsManager(self,
                                             DefaultSettings.Theme.deafultIncognitoTheme if self.isIncognito else DefaultSettings.Theme.defaultTheme,
                                             self.icon_size,
                                             self.targetDlgPos)

        # history manager to store / retrieve previous history (if enabled)
        history_folder = os.path.normpath(os.path.join(DefaultSettings.Storage.App.storageFolder,
                                                       DefaultSettings.Storage.Cache.cacheFolder,
                                                       DefaultSettings.Storage.Cache.cacheFile,
                                                       DefaultSettings.Storage.History.historyFolder))
        full_history_folder = os.path.normpath(os.path.join(self.cache_manager.cachePath, DefaultSettings.Storage.History.historyFolder))
        if not os.path.exists(full_history_folder):
            os.makedirs(full_history_folder)
        self.history_manager = History(history_folder, DefaultSettings.Storage.History.historyFile)

        # creating history widget
        if self.isIncognito:
            self.settings.setEnableHistory(False)
        self.history_widget = HistoryWidget(self, self.settings, self.history_manager, self.dialog_manager, self.loadHistoryUrlSig)
        if self.isIncognito:
            self.history_widget.toggle_chk.hide()
            self.history_widget.eraseHistory_btn.hide()
        if not self.settings.enableHistory:
            self.history_widget.content_widget.hide()

        # create http server
        self.http_manager = None
        if DefaultSettings.Player.externalPlayerType == DefaultSettings.Player.PlayerTypes.http:
            self.http_manager = HttpManager()

        # keep track of open popups and assure their persistence (anyway, we are not allowing popups by now)
        self.popups = []

        # pre-load icons
        self.appIcon = QIcon(DefaultSettings.Icons.appIcon)
        self.appIcon_32 = QIcon(DefaultSettings.Icons.appIcon_32)
        self.appPix = QPixmap(DefaultSettings.Icons.appIcon)
        self.appPix_32 = QPixmap(DefaultSettings.Icons.appIcon_32)
        self.web_pix = QPixmap(DefaultSettings.Icons.loading)
        self.web_ico = QIcon(DefaultSettings.Icons.loading)
        self.web_ico_rotated = QIcon(QPixmap(DefaultSettings.Icons.loading).transformed(QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation))

        LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Pre-initialization finished")

    def setupUI(self):

        # create UI
        self.ui = Ui_MainWindow(self, self.settings, self.isNewWin, self.isIncognito)

        # apply styles to independent widgets
        self.applyStyles()

        # set cookies configuration according to settings
        self.manage_cookies(clicked=False)

        # set tabbar configuration according to orientation
        self.toggle_tabbar(clicked=False)
        self.prevTabIndex = 1

        # connect all UI slots to handle requested actions
        self.connectUiSlots()

        LOGGER.write(LoggerSettings.LogLevels.info, "Main", "UI configured")

    def applyStyles(self):

        # select normal or incognito theme
        if self.isIncognito:
            theme = self.settings.incognitoTheme
        else:
            theme = self.settings.theme

        # navigation bar styles
        self.h_navtab_style = Themes.styleSheet(theme, Themes.Section.horizontalTitleBar)
        self.v_navtab_style = Themes.styleSheet(theme, Themes.Section.verticalTitleBar)

        # tab bar styles
        self.h_tab_style = Themes.styleSheet(theme, Themes.Section.horizontalTabs)
        # inject variable parameters: tab separator image (to make it shorter), min-width and height
        self.h_tab_style = self.h_tab_style % (DefaultSettings.Icons.tabSeparator, self.h_tab_size, self.h_tab_size)
        self.v_tab_style = Themes.styleSheet(theme, Themes.Section.verticalTabs)
        # inject variable parameters: fixed width and height
        self.v_tab_style = self.v_tab_style % (self.action_size, self.action_size)
        self.ui.tabs.setStyleSheet(self.h_tab_style if self.h_tabbar else self.v_tab_style)

        # apply styles to independent widgets
        self.dl_manager.setStyleSheet(Themes.styleSheet(theme, Themes.Section.downloadManager))
        self.search_widget.setStyleSheet(Themes.styleSheet(theme, Themes.Section.searchWidget))
        self.history_widget.setStyleSheet(Themes.styleSheet(self.settings.theme, Themes.Section.historyWidget))

        # context menu styles
        self.ui.tabsContextMenu.setStyleSheet(Themes.styleSheet(theme, Themes.Section.contextmenu))
        self.ui.newTabContextMenu.setStyleSheet(Themes.styleSheet(theme, Themes.Section.contextmenu))

        LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Styles applied")

    def connectUiSlots(self):

        # navigation bar buttons
        self.ui.back_btn.triggered.connect(self.goBack)
        self.ui.next_btn.triggered.connect(self.goForward)
        self.ui.urlbar.returnPressed.connect(self.navigate_to_url)
        self.ui.reload_btn.triggered.connect(self.reloadPage)
        self.ui.ext_player_btn.clicked.connect(self.openExternalPlayer)
        self.ui.auto_btn.clicked.connect(self.manage_autohide)
        self.ui.search_off_btn.clicked.connect(self.manage_search)
        self.ui.search_on_btn.clicked.connect(self.manage_search)
        self.ui.dl_on_btn.clicked.connect(self.manage_downloads)
        self.ui.dl_off_btn.clicked.connect(self.manage_downloads)
        self.ui.hist_on_btn.clicked.connect(self.manage_history)
        self.ui.hist_off_btn.clicked.connect(self.manage_history)
        self.ui.dark_on_btn.clicked.connect(self.manage_dark_mode)
        self.ui.dark_off_btn.clicked.connect(self.manage_dark_mode)
        self.ui.cookie_btn.triggered.connect(lambda: self.manage_cookies(clicked=True))
        self.ui.clean_btn.triggered.connect(self.handleCleanAllRequest)
        self.ui.ninja_btn.clicked.connect(lambda: self.show_in_new_window(incognito=True))

        # window buttons if custom title bar
        if self.settings.isCustomTitleBar:
            self.ui.min_btn.triggered.connect(self.showMinimized)
            self.ui.max_btn.triggered.connect(self.showMaxRestore)
            self.ui.closewin_btn.clicked.connect(self.close)

        # tab bar events management
        self.ui.tabs.currentChanged.connect(self.current_tab_changed)
        self.ui.tabs.tabBarClicked.connect(self.tab_clicked)
        # this will be managed in script
        # self.ui.tabs.tabCloseRequested.connect(self.tab_closed)
        self.ui.tabs.tabBar().tabMoved.connect(self.tab_moved)
        self.ui.tabs.customContextMenuRequested.connect(self.showContextMenu)
        self.ui.newWindow_action.triggered.connect(self.show_in_new_window)

        LOGGER.write(LoggerSettings.LogLevels.info, "Main", "UI signals connected")

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

        # signal to load page when clicked in history
        self.loadHistoryUrlSig.connect(self.add_new_tab)

        LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Signals connected")

    def show(self):
        super().show()

        # apply minimum size to main window according to actual sizes (after show)
        self.setMinimumWidth((self.ui.ninja_btn.width() * len(self.ui.navtab.findChildren(QToolButton))) - (5 * self.small_action_size))
        self.setMinimumHeight(self.ui.navtab.height()+1)

        # setup autohide if enabled
        self.manage_autohide(enabled=self.autoHide)

        # adjust button width to tabbar width
        self.ui.auto_btn.setFixedSize(self.ui.tabs.tabBar().height() if self.h_tabbar else self.ui.tabs.tabBar().width(),
                                      self.ui.ninja_btn.height())

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

            LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Show")

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

        # add the new tab action ("+") in tab bar
        self.add_tab_action()

        # set current index AFTER creating all tabs
        self.ui.tabs.setCurrentIndex(current)

        self.instances = []
        for new_tabs in new_wins:
            self.show_in_new_window(new_tabs)

        LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Tabs created")

    def add_tab(self, qurl, zoom=1.0, label="Loading...", tabIndex=None):

        # create webengineview as tab widget
        browser = self.getBrowser(qurl, zoom)

        # setting tab index and default icon
        if tabIndex is None:
            # add tab at the end
            tabIndex = self.ui.tabs.addTab(browser, label if self.h_tabbar else "")

        else:
            # add tab in given position (e.g. when requested from page context menu)
            self.ui.tabs.insertTab(tabIndex, browser, label if self.h_tabbar else "")

        # connect browser and page signals (once we have the tab index)
        self.connectBrowserSlots(browser)
        self.connectPageSlots(browser.page())

        # set close buttons according to tabs orientation
        if self.h_tabbar:
            self.ui.tabs.tabBar().tabButton(tabIndex, QTabBar.ButtonPosition.RightSide).clicked.disconnect()
            self.ui.tabs.tabBar().tabButton(tabIndex, QTabBar.ButtonPosition.RightSide).clicked.connect(lambda checked, b=browser: self.tab_closed(b))
        else:
            self.ui.tabs.tabBar().setTabButton(tabIndex, QTabBar.ButtonPosition.RightSide, None)

        return tabIndex

    def getBrowser(self, qurl, zoom):

        # this will create the browser and apply profile settings
        browser = WebView()
        self._profile = self.getProfile(browser)
        page = self.getPage(self._profile, browser, zoom)
        browser.setPage(page)

        # most settings must be applied AFTER setting page and profile
        browser.applySettings(DefaultSettings.Security.securityLevel, self.dark_mode)

        # setting url to browser. Using a timer (thread) it seems to load faster
        QTimer.singleShot(0, lambda u=qurl: browser.load(u))

        return browser

    def connectBrowserSlots(self, browser):

        # adding action to the browser when url changes
        browser.urlChanged.connect(lambda u, b=browser: self.update_urlbar(u, b))

        # check start/finish loading (e.g. for loading animations)
        browser.loadStarted.connect(lambda b=browser: self.onLoadStarted(b))
        browser.loadFinished.connect(lambda a, b=browser: self.onLoadFinished(a, b))

    def onLoadStarted(self, browser):
        tabIndex = self.ui.tabs.indexOf(browser)
        self.ui.tabs.setTabIcon(tabIndex, self.web_ico if self.h_tabbar else self.web_ico_rotated)
        if browser == self.ui.tabs.currentWidget():
            self.ui.reload_btn.setText(self.ui.stop_char)
            self.ui.reload_btn.setToolTip("Stop loading page")

    def onLoadFinished(self, loadedOk, browser):
        if browser == self.ui.tabs.currentWidget():
            self.ui.reload_btn.setText(self.ui.reload_char)
            self.ui.reload_btn.setToolTip("Reload page")
        # TODO: find a reliable way to check if there is a media playback error (most likely, there isn't)
        # browser.page().checkCanPlayMedia()

    def getProfile(self, browser=None):

        if self._profile is None or self.cache_manager.deleteCacheRequested:

            if self.isIncognito:
                # apply no persistent cache
                cache_path = None
            elif self.cache_manager.deleteCacheRequested:
                # apply temporary cache location to delete all previous cache when app is closed, but keeping these last
                cache_path = self.cache_manager.lastCache
            else:
                # apply application cache location
                cache_path = self.cache_manager.cachePath

            self._profile = WebProfile(cache_path, browser, self.cookie_filter,
                                       DefaultSettings.AdBlocker.enableAdBlocker, self.requestInterceptor)

        return self._profile

    def getPage(self, profile, browser, zoom):

        # this will create the page and apply all selected settings
        page = WebPage(profile, browser, self.dialog_manager, self.http_manager)

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

    def connectPageSlots(self, page):

        # manage fullscreen requests (enabled at browser level)
        page.fullScreenRequested.connect(self.page_fullscr)

        # Preparing asking for permissions
        page.featurePermissionRequested.connect(lambda origin, feature, p=page: p.handleFeatureRequested(origin, feature))
        # Are these included in previous one? or the opposite? or none?
        # page.permissionRequested.connect(lambda request, p=page: self.show_permission_request(request, p))
        page.fileSystemAccessRequested.connect(lambda request, p=page: print("FS ACCESS REQUESTED", request))
        page.desktopMediaRequested.connect(lambda request, p=page: print("MEDIA REQUESTED", request))

        # adding action to the browser when title or icon change
        page.titleChanged.connect(lambda title, b=page.parent(): self.title_changed(title, b))
        page.iconChanged.connect(lambda icon, b=page.parent(): self.icon_changed(icon, b))

        # manage file downloads (including pages and files)
        page.profile().downloadRequested.connect(self.download_file)

    def page_fullscr(self, request):
        self.manage_fullscr(request.toggleOn(), page_fullscr=True)
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

    def title_changed(self, title, browser, internalCall=False):

        tabIndex = self.ui.tabs.indexOf(browser)

        self.ui.tabs.tabBar().setTabText(tabIndex, (title + " " * 30)[:29] if self.h_tabbar else "")
        self.ui.tabs.setTabToolTip(tabIndex, title + ("" if self.h_tabbar else "\n(Right-click to close)"))

        if not internalCall and self.settings.enableHistory and self.history_manager is not None:
            hash_object = hashlib.sha256(self.ui.tabs.widget(tabIndex).url().toString().encode())
            filename = str(hash_object.hexdigest())
            full_filename = os.path.join(self.history_manager.historyFolder, filename)
            item = [str(time.time()), title, self.ui.tabs.widget(tabIndex).url().toString(), full_filename]
            added = self.history_manager.addHistoryEntry(item)
            if added:
                self.history_widget.addHistoryEntry(item)
            else:
                self.history_widget.updateHistoryEntry(item)

    def icon_changed(self, icon, browser):

        tabIndex = self.ui.tabs.indexOf(browser)

        pixmap = icon.pixmap(QSize(self.icon_size, self.icon_size))
        pixmap = utils.fixDarkImage(pixmap)

        if not self.h_tabbar:
            pixmapRotated = pixmap.transformed(QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation)
        else:
            pixmapRotated = pixmap
        self.ui.tabs.tabBar().setTabIcon(tabIndex, QIcon(pixmapRotated))

        if self.settings.enableHistory:
            hash_object = hashlib.sha256(self.ui.tabs.widget(tabIndex).url().toString().encode())
            filename = str(hash_object.hexdigest())
            full_filename = os.path.join(self.history_manager.historyFolder, filename)
            if not os.path.exists(full_filename):
                (pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                       .save(full_filename, "PNG"))
                self.history_widget.updateEntryIcon(full_filename)

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
    def add_new_tab(self, qurl=None, setFocus=True):
        self.ui.tabs.removeTab(self.ui.tabs.count() - 1)
        qurl = qurl or QUrl(DefaultSettings.Browser.defaultPage)
        if setFocus:
            i = self.add_tab(qurl)
        else:
            i = self.add_tab(qurl, tabIndex=self.ui.tabs.currentIndex() + 1)
        self.update_urlbar(self.ui.tabs.currentWidget().url(), self.ui.tabs.currentWidget())
        self.add_tab_action()
        if setFocus:
            self.ui.tabs.setCurrentIndex(i)

    # method to update the url when tab is changed
    def navigate_to_url(self):

        # get the line edit text and convert it to QUrl object
        qurl = QUrl(self.ui.urlbar.text())

        # if scheme is blank
        if not qurl.isValid() or ((" " in qurl.url() or "." not in qurl.url()) and qurl.scheme() not in ("chrome", "file")):
            # search in Google
            # qurl.setUrl("https://www.google.es/search?q=%s&safe=off" % self.urlbar.text())
            # search in DuckDuckGo (safer)
            qurl.setUrl("https://duckduckgo.com/?t=h_&hps=1&start=1&q=%s&ia=web&kae=d" % self.ui.urlbar.text().replace(" ", "+"))

        if qurl.scheme() == "":
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

        if self.search_widget.isVisible():
            self.ui.tabs.currentWidget().findText("")
            self.search_widget.hide()

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

        if to_index == self.ui.tabs.count() - 1:
            # Avoid moving last tab (add new tab) if dragging another tab onto it
            self.ui.tabs.removeTab(from_index)
            self.add_tab_action()

        elif to_index == 0:
            # Avoid moving first tab (toggle tab orientation) if dragging another tab onto it
            self.ui.tabs.removeTab(from_index)
            self.add_toggletab_action()

    def tab_closed(self, browser):

        tabIndex = self.ui.tabs.indexOf(browser)

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

            # just removing the tab doesn't destroy associated widget.
            self.widgetToDelete = self.ui.tabs.widget(tabIndex)
            # remove the tab
            self.ui.tabs.removeTab(tabIndex)

            # adjust target tab index according to new tabs number (but not tab 0, the toggle button)
            if targetIndex >= self.ui.tabs.count() - 1:
                targetIndex = self.ui.tabs.count() - 2
            elif targetIndex <= 0:
                targetIndex = 1
            self.ui.tabs.setCurrentIndex(targetIndex)

        # delete tab widget safely
        self.widgetToDelete.deleteLater()

    def showContextMenu(self, point):

        tabIndex = self.ui.tabs.tabBar().tabAt(point)

        if 1 <= tabIndex < self.ui.tabs.count() - 1:
            # set buttons before running context menu (it blocks)
            self.ui.close_action.triggered.disconnect()
            self.ui.close_action.triggered.connect(lambda checked, b=self.ui.tabs.widget(tabIndex): self.tab_closed(b))
            # create and run context menu
            self.ui.createCloseTabContextMenu(tabIndex)

        elif tabIndex == self.ui.tabs.count() - 1:
            self.ui.createNewTabContextMenu(tabIndex)

    def openLinkRequested(self, request):

        if request.destination() == QWebEngineNewWindowRequest.DestinationType.InNewWindow:
            self.show_in_new_window([[request.requestedUrl().toString(), 1.0, True]])

        elif request.destination() == QWebEngineNewWindowRequest.DestinationType.InNewTab:
            self.add_new_tab(request.requestedUrl(), setFocus=False)

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
        self.inspector.setWindowTitle("DevTools - " + p.title())
        self.inspector.show()

    def toggle_tabbar(self, clicked=True):

        if clicked:
            self.h_tabbar = not self.h_tabbar

        # enable buttons first (only if horizontal tabbar)
        self.ui.tabs.setTabsClosable(self.h_tabbar)

        # reorganize tabs
        for i in range(1, self.ui.tabs.count() - 1):
            icon = self.ui.tabs.widget(i).page().icon()
            if not icon.availableSizes():
                icon = self.web_ico if self.h_tabbar else self.web_ico_rotated
            if self.h_tabbar:
                new_icon = icon
                self.title_changed(self.ui.tabs.widget(i).page().title(), self.ui.tabs.widget(i), True)
                self.ui.tabs.tabBar().tabButton(i, QTabBar.ButtonPosition.RightSide).clicked.connect(lambda checked, b=self.ui.tabs.widget(i): self.tab_closed(b))
            else:
                new_icon = QIcon(icon.pixmap(QSize(self.icon_size, self.icon_size)).transformed(QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation))
                self.ui.tabs.tabBar().setTabText(i, "")
            self.ui.tabs.tabBar().setTabIcon(i, new_icon)

        if self.isIncognito:
            theme = self.settings.incognitoTheme
        else:
            theme = self.settings.theme

        self.ui.tabs.setStyleSheet(Themes.styleSheet(theme, Themes.Section.horizontalTabs) if self.h_tabbar else Themes.styleSheet(theme, Themes.Section.verticalTabs))
        self.ui.tabs.setTabPosition(QTabWidget.TabPosition.North if self.h_tabbar else QTabWidget.TabPosition.West)
        self.ui.tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self.ui.tabs.tabBar().setTabButton(self.ui.tabs.count() - 1, QTabBar.ButtonPosition.RightSide, None)
        self.ui.tabs.tabBar().setStyleSheet(self.h_tab_style if self.h_tabbar else self.v_tab_style)
        self.ui.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu if self.h_tabbar else Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.tabs.setTabToolTip(0, "Set %s tabs" % ("vertical" if self.h_tabbar else "horizontal"))

        self.ui.navtab.setStyleSheet(self.h_navtab_style if self.h_tabbar else self.v_navtab_style)

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
        x = actPos.x() + actRect.width() - self.search_widget.width()
        y = self.y() + self.ui.navtab.height() + gap
        return QPoint(x, y)

    def manage_search(self):
        if self.search_widget.isVisible():
            self.ui.tabs.currentWidget().findText("")
            self.search_widget.hide()
            self.ui.search_off_act.setVisible(False)
            self.ui.search_on_act.setVisible(True)

        else:
            self.search_widget.show()
            self.search_widget.move(self.get_search_widget_pos())
            self.ui.search_off_act.setVisible(True)
            self.ui.search_on_act.setVisible(False)

    def searchPage(self, checked, forward):
        textToFind = self.search_widget.getText()
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

        if self.dl_manager.isVisible():
            self.ui.dl_on_act.setVisible(True)
            self.ui.dl_off_act.setVisible(False)
            self.dl_manager.hide()

        else:
            self.ui.dl_on_act.setVisible(False)
            self.ui.dl_off_act.setVisible(True)
            self.show_dl_manager()

    def get_dl_manager_pos(self):

        # getting title bar height (custom or standard)
        gap = self.mapToGlobal(self.ui.navtab.pos()).y() - self.y()

        # calculate position
        x = self.x() + self.width() - self.dl_manager.width()
        y = self.y() + self.ui.navtab.height() + gap
        return QPoint(x, y)

    def show_dl_manager(self):

        self.ui.dl_on_act.setVisible(False)
        self.ui.dl_off_act.setVisible(True)
        self.dl_manager.show()
        self.dl_manager.move(self.get_dl_manager_pos())

    def manage_history(self):

        if self.history_widget.isVisible():
            self.ui.hist_on_act.setVisible(True)
            self.ui.hist_off_act.setVisible(False)
            self.history_widget.hide()

        else:
            self.ui.hist_on_act.setVisible(False)
            self.ui.hist_off_act.setVisible(True)
            self.show_history_widget()

    def get_history_widget_geom(self):

        # getting title bar height (custom or standard)
        gap = self.mapToGlobal(self.ui.navtab.pos()).y() - self.y()

        # calculate position
        x = self.x() + self.width() - self.history_widget.width()
        y = self.y() + self.ui.navtab.height() + gap
        w = 300
        h = self.height() - (self.ui.navtab.height() + (self.ui.tabs.tabBar().height() if self.h_tabbar else 0))
        return QRect(x, y, w, h)

    def show_history_widget(self):
        self.history_widget.show()
        self.history_widget.setGeometry(self.get_history_widget_geom())

    def manage_dark_mode(self):

        self.dark_mode = not self.dark_mode

        self.ui.dark_on_act.setVisible(not self.dark_mode)
        self.ui.dark_off_act.setVisible(self.dark_mode)

        for i in range(1, self.ui.tabs.count() - 2):
            self.ui.tabs.widget(i).settings().setAttribute(QWebEngineSettings.WebAttribute.ForceDarkMode, self.dark_mode)
            self.ui.tabs.widget(i).reload()

    def manage_tabs(self, index):
        if index <= 0:
            index = self.ui.tabs.count() - 2
        elif index >= self.ui.tabs.count() - 1:
            index = 1
        self.ui.tabs.setCurrentIndex(index)

    # adding action to download files
    def download_file(self, item: QWebEngineDownloadRequest):
        if self.dl_manager.addDownload(item):
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

    def handleCleanAllRequest(self):
        self.dialog_manager.createDialog(
            title="Warning!",
            message=DefaultSettings.DialogMessages.cleanAllRequest,
            acceptedSlot=self.accept_clean)

    def accept_clean(self):

        if not self.isIncognito:
            # activate cache deletion upon closing app (if not incognito which will be auto-deleted)
            self.cache_manager.deleteCacheRequested = True

            # set a new cache folder (old ones will be deleted when app is restarted)
            self.cache_manager.lastCache = os.path.join(self.cache_manager.cachePath, str(time.time()).replace(".", ""))

        # fresh-reload all pages
        tabsCount = self.ui.tabs.count()
        currIndex = self.ui.tabs.currentIndex()
        self.ui.tabs.setCurrentIndex(1)

        tabs = []
        for i in range(1, tabsCount - 1):
            browser = self.ui.tabs.widget(1)
            page = browser.page()
            tabs.append([page.url(), page.zoomFactor()])
            browser.deleteLater()
            self.ui.tabs.removeTab(1)

        self.ui.tabs.removeTab(1)

        for item in tabs:
            url, zoom = item
            # new cache storage will be assigned in add_tab() method
            self.add_tab(url, zoom)
        self.add_tab_action()
        self.ui.tabs.setCurrentIndex(currIndex)

    def showMaxRestore(self):

        if self.isMaximized():
            self.showNormal()
            self.ui.max_btn.setText(self.ui.max_chr)
            self.ui.max_btn.setToolTip("Maximize")

        else:
            self.showMaximized()
            self.ui.max_btn.setText(self.ui.rest_chr)
            self.ui.max_btn.setToolTip("Restore")

    def keyReleaseEvent(self, a0):

        if a0.key() == Qt.Key.Key_Escape:
            if self.ui.urlbar.hasFocus():
                text = self.ui.tabs.currentWidget().url().toString()
                self.ui.urlbar.setText(self.ui.tabs.currentWidget().url().toString())
                self.ui.urlbar.setCursorPosition(len(text))

            elif self.search_widget.hasFocus():
                self.manage_search()

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
                self.tab_closed(self.ui.tabs.currentWidget())

        elif a0.key() == Qt.Key.Key_F11:
            if not self.isPageFullscreen:
                self.manage_fullscr(on=not self.isFullScreen())

        elif a0.key() == Qt.Key.Key_A:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.manage_autohide(enabled=False)

        elif a0.key() == Qt.Key.Key_H:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.manage_history()

        elif a0.key() == Qt.Key.Key_Backtab:
            if a0.modifiers() == Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier:
                index = self.ui.tabs.currentIndex() - 1
                self.manage_tabs(index)

        elif a0.key() == Qt.Key.Key_Tab:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                index = self.ui.tabs.currentIndex() + 1
                self.manage_tabs(index)

        elif Qt.Key.Key_1 <= a0.key() <= Qt.Key.Key_9:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                index = int(chr(a0.key()))
                self.manage_tabs(index)

    def targetDlgPos(self):
        return QPoint(self.x() + 100,
                      self.y() + self.ui.navtab.height() + (self.ui.tabs.tabBar().height() if self.h_tabbar else 0))

    # these widgets have a relative position. Must be moved AFTER showing main window
    def moveOtherWidgets(self):

        if hasattr(self, "dl_manager") and self.dl_manager.isVisible():
            # reposition download list
            self.dl_manager.move(self.get_dl_manager_pos())

        if hasattr(self, "search_widget") and self.search_widget.isVisible():
            # reposition search widget
            self.search_widget.move(self.get_search_widget_pos())

        if hasattr(self, "history_widget") and self.history_widget.isVisible():
            # reposition search widget
            self.history_widget.setGeometry(self.get_history_widget_geom())

        if self.dialog_manager.showingDlg and self.dialog_manager.currentDialog is not None:
            # reposition any open dialog
            self.dialog_manager.currentDialog.move(self.targetDlgPos())

    def moveEvent(self, a0):
        super().moveEvent(a0)

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

    def deletePreviousCacheAndTemp(self):
        if OPTIONS.deleteCache:
            self.cache_manager.deleteCache(OPTIONS.lastCache)
            LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Previous cache deleted")
        if OPTIONS.deletePlayerTemp:
            if os.path.exists(DefaultSettings.App.tempFolder):
                try:
                    shutil.rmtree(DefaultSettings.App.tempFolder)
                except:
                    LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Temp folder not found")
            LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Previous temp files deleted")
        if OPTIONS.deleteCache or OPTIONS.deletePlayerTemp:
            # relaunched only to delete cache and / or temp files. Exiting...
            QApplication.quit()
            sys.exit(0)

    def closeEvent(self, a0):

        # close all other widgets and processes
        self.dl_manager.cancelAllDownloads()
        self.dl_manager.close()
        self.search_widget.close()
        self.history_widget.close()
        self.ui.hoverHWidget.close()
        self.ui.hoverVWidget.close()
        self.inspector.close()
        # this dialog may not exist (whilst others may be queued)
        try:
            self.dialog_manager.currentDialog.close()
        except:
            pass
        if self.http_manager is not None:
            try:
                self.http_manager.stop()
            except:
                pass

        # save open tabs and close external players
        tabs = []
        for i in range(1, self.ui.tabs.count() - 1):
            browser = self.ui.tabs.widget(i)
            page = browser.page()
            page.closeExternalPlayer(False, page.url().toString())
            tabs.append([browser.url().toString(), page.zoomFactor(), i == self.ui.tabs.currentIndex()])

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

        if not self.isIncognito:
            self.history_manager.saveHistory()

        args = []
        if self.cache_manager.deleteCacheRequested and not self.isNewWin and not self.isIncognito:
            # restart app to wipe all cache folders but the last one (not possible while running since it's locked)
            args += [appconfig.Options.deleteCache] + [self.cache_manager.lastCache]

        if os.path.exists(DefaultSettings.App.tempFolder):
            args += [appconfig.Options.deletePlayerTemp]

        if args:
            LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Restart application to delete cache and/or temp files")
            status = QProcess.startDetached(sys.executable, sys.argv + args)


def main():

    appconfig.preInitializeApp(OPTIONS)

    # creating a PyQt5 application and (windows only) force dark mode
    app = QApplication(sys.argv + ['-platform', 'windows:darkmode=1'])

    # creating and showing MainWindow object
    window = MainWindow()
    window.show()

    # loop
    app.exec()


if __name__ == "__main__":
    main()
