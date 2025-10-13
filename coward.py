# based on: https://www.geeksforgeeks.org/python/creating-a-tabbed-browser-using-pyqt5/
import hashlib
import os
import shutil
import sys
import time

from PyQt6 import sip
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWebEngineCore import *
from PyQt6.QtWebEngineWidgets import *
from PyQt6.QtWidgets import *

import appconfig
import utils
from appconfig import OPTIONS
from appconfig import Splash
from cachemanager import CacheManager
from dialog import DialogsManager
from downloadmanager import DownloadManager
from historymanager import History, HistoryWidget
from logger import LoggerSettings, LOGGER
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

    # check activity
    checkTabsActivitySig = pyqtSignal()

    # check if page is playing media to avoid suspending it
    pageIsPlayingMediaSig = pyqtSignal(QWebEnginePage, bool)

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

        # close on relaunch (delete cache and temp and exit) or keep main window open
        self.dontCloseOnRelaunch = OPTIONS.dontCloseOnRelaunch

        # prepare new wins config, with or without initial tabs
        self.isNewWin = new_win

        # Enable/Disable adblocker
        self.adblock = self.settings.enableAdblocker if OPTIONS.enableAdblocker is None else OPTIONS.enableAdblocker

        # Enable/Disable cookies and prepare incognito environment
        if (new_win and incognito is not None) or OPTIONS.incognitoMode:
            self.cookies = True
            self.isIncognito = incognito if OPTIONS.incognitoMode is None else OPTIONS.incognitoMode
        else:
            self.cookies = self.settings.allowCookies if OPTIONS.cookies is None else OPTIONS.cookies
            self.isIncognito = False

        # Enable/disabling force dark mode in pages
        self.dark_mode = self.settings.forceDark

        # set icon size (also affects to tabs and actions sizes)
        # since most "icons" are actually characters, we should also adjust fonts or stick to values between 24 and 32
        self.icon_size = int(max(24, min(32, self.settings.iconSize)))
        self.h_tab_size = self.icon_size + 8
        self.action_size = self.settings.iconSize + max(16, self.settings.iconSize // 2)
        self.medium_action_size = self.action_size - 8
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
        self.settings.setEnableAdblocker(self.adblock, True)
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

        # configure tabs
        self.tabIconsFolder = os.path.normpath(os.path.join(self.cache_manager.cachePath, DefaultSettings.Storage.Tabs.tabsFolder))
        if not os.path.exists(self.tabIconsFolder):
            os.makedirs(self.tabIconsFolder)

        # webpage common profile to keep session logins, cookies, etc.
        self._profile = None

        # Request interceptor for blocking URLs and ad-blocking
        self.requestInterceptor = RequestInterceptor(os.path.join(self.appStorageFolder,
                                                                  DefaultSettings.AdBlocker.filterlistsFolder))
        self.requestInterceptor.setEnabled(self.adblock)

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

        # set check activity to free memory if enabled
        self.checkActivityEnabled = DefaultSettings.Tabs.checkActivity
        if self.checkActivityEnabled:
            self.activityTimer = QTimer()
            self.activityTimer.timeout.connect(self.checkTabsActivityTrigger)
            self.activityTimer.start(60000)

        # create http server
        self.http_manager = None
        if DefaultSettings.Player.externalPlayerType == DefaultSettings.Player.PlayerTypes.http:
            self.http_manager = HttpManager()

        # create clipboard object
        self.clipboard = QApplication.clipboard()

        # trying to control which URLs have being already checked for non-compatible media
        self.checkedURL = []

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

        # set cookies and adblocker configuration according to settings
        self.manage_adblock(clicked=False)
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
        # horizontal tabs
        self.h_tab_style = Themes.styleSheet(theme, Themes.Section.horizontalTabs)
        # inject variable parameters: tab separator image (to make it shorter), min-width and height
        self.h_tab_style = self.h_tab_style % (DefaultSettings.Icons.tabSeparator, self.h_tab_size,
                                               DefaultSettings.Tabs.maxWidth, self.h_tab_size,
                                               DefaultSettings.Icons.closeButton, DefaultSettings.Icons.closeButtonHover)
        # vertical tabs
        self.v_tab_style = Themes.styleSheet(theme, Themes.Section.verticalTabs)
        # inject variable parameters: fixed width and height
        self.v_tab_style = self.v_tab_style % (self.action_size, self.action_size)
        # style for tabs will be applied within toggle_tabbar() method

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
        self.ui.auto_btn.clicked.connect(self.manage_autohide)
        self.ui.back_btn.triggered.connect(self.goBack)
        self.ui.next_btn.triggered.connect(self.goForward)
        self.ui.reload_btn.triggered.connect(self.reloadPage)
        self.ui.urlbar.returnPressed.connect(self.navigate_to_url)
        self.ui.ext_player_btn.clicked.connect(self.openExternalPlayer)
        self.ui.search_off_btn.clicked.connect(self.manage_search)
        self.ui.search_on_btn.clicked.connect(self.manage_search)
        self.ui.dl_on_btn.clicked.connect(self.manage_downloads)
        self.ui.dl_off_btn.clicked.connect(self.manage_downloads)
        self.ui.hist_on_btn.clicked.connect(self.manage_history)
        self.ui.hist_off_btn.clicked.connect(self.manage_history)
        self.ui.dark_on_btn.clicked.connect(self.manage_dark_mode)
        self.ui.dark_off_btn.clicked.connect(self.manage_dark_mode)
        self.ui.adblock_btn.clicked.connect(lambda: self.manage_adblock(clicked=True))
        self.ui.cookie_btn.clicked.connect(lambda: self.manage_cookies(clicked=True))
        self.ui.clean_btn.clicked.connect(self.handleCleanAllRequest)
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

        # signal to replace browser widget when suspended / re-enabled
        self.checkTabsActivitySig.connect(self.checkTabsActivity)

        # signal to update if page is playing media (avoiding to suspend it)
        self.pageIsPlayingMediaSig.connect(self.updatePageIsPlayingMedia)

        LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Signals connected")

    def show(self):
        super().show()

        # apply minimum size to main window according to actual sizes (after show)
        self.setMinimumWidth((self.action_size * len(self.ui.navtab.findChildren(QToolButton))) - (5 * self.small_action_size))
        self.setMinimumHeight(self.ui.navtab.height()+1)

        # setup autohide if enabled
        self.manage_autohide(enabled=self.autoHide)

        # adjust button width to tabbar width
        targetRect = self.ui.tabs.tabBar().tabRect(0)
        self.ui.auto_btn.setFixedSize(targetRect.height() if self.h_tabbar else targetRect.width(), self.ui.closewin_btn.height())

        # thanks to Maxim Paperno: https://stackoverflow.com/questions/58145272/qdialog-with-rounded-corners-have-black-corners-instead-of-being-translucent
        if self.settings.radius > 0:
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
        tabIcons = []
        self.tabsActivity = {}
        if tabs:
            for i, tab in enumerate(tabs):
                url, zoom, title, active, frozen, icon = tab
                if active:
                    current = i + 1
                    QTimer.singleShot(0, lambda u=url: self.ui.urlbar.setText(u))
                self.add_tab(QUrl(url), zoom, title, active and not self.checkActivityEnabled, icon)
                tabIcons.append(icon)
            for file in os.listdir(self.tabIconsFolder):
                filepath = os.path.join(self.tabIconsFolder, file)
                if os.path.exists(filepath) and file not in tabIcons:
                    os.remove(filepath)

        else:
            self.add_tab(QUrl(DefaultSettings.Browser.defaultPage))

        # add the new tab action ("+") in tab bar
        self.add_tab_action()

        # set current index AFTER creating all tabs (this will also generate a view for active tab)
        self.ui.tabs.setCurrentIndex(current)

        # force resize event to adjust tabs text size according to tabs number
        self.ui.tabs.resize(self.ui.tabs.size())

        self.instances = []
        for new_tabs in new_wins:
            self.show_in_new_window(new_tabs)

        LOGGER.write(LoggerSettings.LogLevels.info, "Main", f"All tabs created: {len(tabs)}")

    def add_tab(self, qurl, zoom=1.0, label="Loading...", loadUrl=True, icon="", tabIndex=None):

        # create webengineview as tab widget
        if loadUrl:
            browser = self.getBrowser(qurl, zoom, loadUrl)

            # connect browser and page signals (once we have the tab index)
            self.connectBrowserSlots(browser)
            self.connectPageSlots(browser.page())
            tab_type = "STANDARD"

        else:
            browser = QLabel()
            tab_type = "DUMMY"

        self.tabsActivity[browser] = [qurl.toString(), label, zoom, time.time(), not loadUrl, False]

        # add / insert tab and set title tooltip and icon
        if tabIndex is None:
            # add tab at the end
            tabIndex = self.ui.tabs.addTab(browser, label, self.h_tabbar)

        else:
            # add tab in given position (e.g. when requested from page context menu)
            self.ui.tabs.insertTab(tabIndex, browser, label, self.h_tabbar)
        self.ui.tabs.setTabToolTip(tabIndex, label + ("" if self.h_tabbar else "\n(Right-click to close)"))
        self.ui.tabs.setTabIcon(tabIndex, self._getTabIcon(icon, tab_type == "STANDARD"))

        # set close buttons according to tabs orientation
        if self.h_tabbar:
            self.ui.tabs.tabBar().tabButton(tabIndex, QTabBar.ButtonPosition.RightSide).clicked.disconnect()
            self.ui.tabs.tabBar().tabButton(tabIndex, QTabBar.ButtonPosition.RightSide).clicked.connect(
                lambda checked, b=browser: self.tab_closed(b))
        else:
            self.ui.tabs.tabBar().setTabButton(tabIndex, QTabBar.ButtonPosition.RightSide, None)

        LOGGER.write(LoggerSettings.LogLevels.info, "Main", f"{tab_type} Tab created: {qurl.toString()}")

        return tabIndex

    def _getTabIcon(self, icon, enabled):
        qicon = None
        if icon:
            iconFile = os.path.join(self.tabIconsFolder, icon)
            if os.path.exists(iconFile):
                pixmap = QPixmap(iconFile)
                if not enabled:
                    qimage = pixmap.toImage()
                    grayscale_image = self.convert_to_grayscale_with_alpha(qimage)
                    pixmap = QPixmap.fromImage(grayscale_image)
                if not self.h_tabbar:
                    pixmap = pixmap.transformed(QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation)
                qicon = QIcon(pixmap)
        if qicon is None:
            qicon = self.web_ico if self.h_tabbar else self.web_ico_rotated
        return qicon

    def convert_to_grayscale_with_alpha(self, image):
        # this is faster, but doesn't keep the alpha (transparency) channel
        # grayscale_image = qimage.convertToFormat(QImage.Format.Format_Grayscale8, Qt.ImageConversionFlag.AutoColor)
        argb_image = image.convertToFormat(QImage.Format.Format_ARGB32)
        width = argb_image.width()
        height = argb_image.height()
        bpl = argb_image.bytesPerLine()

        for y in range(height):
            scan_line = argb_image.scanLine(y)
            scan_line.setsize(bpl)  # Set size to access as buffer
            for x in range(width):
                # Access 4-byte pixel manually
                i = x * 4
                # Extract RGBA components
                r, g, b = scan_line[i], scan_line[i + 1], scan_line[i + 2]
                gray = qGray(int.from_bytes(r), int.from_bytes(g), int.from_bytes(b))
                # Write back grayscale with original alpha
                scan_line[i] = gray.to_bytes()
                scan_line[i + 1] = gray.to_bytes()
                scan_line[i + 2] = gray.to_bytes()
                # scan_line[i+3] = a  # Alpha already preserved

        return argb_image

    def getBrowser(self, qurl, zoom, loadUrl):

        # this will create the browser and apply profile settings
        browser = WebView()
        self._profile = self.getProfile(browser)
        page = self.getPage(self._profile, browser, zoom)
        browser.setPage(page)

        # most settings must be applied AFTER setting page and profile
        browser.applySettings(DefaultSettings.Security.securityLevel, self.dark_mode)

        if loadUrl:
            # setting url to browser. Using a timer (thread) it seems to load faster
            QTimer.singleShot(0, lambda u=qurl: browser.load(u))

        return browser

    def connectBrowserSlots(self, browser, connect=True):

        if connect:

            # adding action to the browser when url changes
            browser.urlChanged.connect(lambda qurl, b=browser: self.url_changed(qurl, b))

            # check start/finish loading (e.g. for loading animations)
            browser.loadStarted.connect(lambda b=browser: self.onLoadStarted(b))
            browser.loadFinished.connect(lambda a, b=browser: self.onLoadFinished(a, b))

        elif isinstance(browser, QWebEngineView):
            browser.urlChanged.disconnect()
            browser.loadStarted.disconnect()
            browser.loadFinished.disconnect()

    def onLoadStarted(self, browser):

        self.ui.tabs.setTabIcon(self.ui.tabs.indexOf(browser), self.web_ico if self.h_tabbar else self.web_ico_rotated)

        if browser == self.ui.tabs.currentWidget():
            self.ui.reload_btn.setText(self.ui.stop_char)
            self.ui.reload_btn.setToolTip("Stop loading page")

    def onLoadFinished(self, loadedOk, browser):
        # This signal is not triggered in many sites when clicking "inner" links!!!
        # Things like history must be handled in title_changed() (not the ideal place, but...)
        if browser == self.ui.tabs.currentWidget():
            self.ui.reload_btn.setText(self.ui.reload_char)
            self.ui.reload_btn.setToolTip("Reload page")

    def getProfile(self, browser=None):

        if self._profile is None or self.cache_manager.deleteCacheRequested:

            if self.isIncognito:
                # apply no persistent cache
                cache_path = None
            else:
                # apply application cache location
                cache_path = self.cache_manager.cachePath

            self._profile = WebProfile(cache_path, browser, self.cookie_filter, self.requestInterceptor)

            # manage file downloads (including pages and files)
            self._profile.downloadRequested.connect(self.download_file)

        return self._profile

    def getPage(self, profile, browser, zoom):

        # this will create the page and apply all selected settings
        page = WebPage(profile, browser, self.pageIsPlayingMediaSig, self.dialog_manager, self.http_manager)

        # set page zoom factor
        page.setZoomFactor(zoom)

        # customize browser context menu
        self.setPageContextMenu(page)

        return page

    @pyqtSlot(QWebEnginePage, bool)
    def updatePageIsPlayingMedia(self, page, isPlaying):
        try:
            browser = page.parent()
        except:
            browser = None
        if browser is not None and browser in self.tabsActivity.keys():
            url, title, zoom, lastTimeLoaded, frozen, _ = self.tabsActivity[browser]
            self.tabsActivity[browser] = [url, title, zoom, lastTimeLoaded, frozen, isPlaying]

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

    def connectPageSlots(self, page, connect=True):

        if connect:
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

        elif isinstance(page, QWebEnginePage):
            page.fullScreenRequested.disconnect()
            page.featurePermissionRequested.disconnect()
            page.fileSystemAccessRequested.disconnect()
            page.desktopMediaRequested.disconnect()
            page.titleChanged.disconnect()
            page.iconChanged.disconnect()

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

    def url_changed(self, qurl, browser):
        # All this has to be done here since loadfinished() is not triggered, titleChanged() is triggered twice, etc...

        self.update_urlbar(qurl, browser)

        tabData = self.tabsActivity.get(browser, None)
        if tabData:
            _, title, zoom, lastAccessed, frozen, isPlayingMedia = tabData
            url = qurl.toString()
            self.tabsActivity[browser] = [url, title, zoom, lastAccessed, frozen, isPlayingMedia]

            if DefaultSettings.Media.checkPageCanPlayMedia and url and url not in self.checkedURL:
                self.checkedURL.append(qurl.toString())
                browser.page().mediaCheck.checkCanPlayMedia(url)

    def title_changed(self, title, browser):
        # sometimes this is called twice for the same page, passing an obsolete title (though URL is ok... weird)

        tabIndex = self.ui.tabs.indexOf(browser)
        self.ui.tabs.setTabText(tabIndex, title if self.h_tabbar else "")
        self.ui.tabs.setTabToolTip(tabIndex, title + ("" if self.h_tabbar else "\n(Right-click to close)"))

        tabData = self.tabsActivity.get(browser, None)
        if tabData:
            url, _, zoom, lastAccessed, frozen, isPlayingMedia = tabData
            self.tabsActivity[browser] = [url, title, zoom, lastAccessed, frozen, isPlayingMedia]

            if self.settings.enableHistory:
                # create history once the title is available
                item = [str(time.time()), title, url, self._getIconFileName(QUrl(url))]
                self.history_widget.addHistoryEntry(item)

    def icon_changed(self, icon, browser):

        pixmap = icon.pixmap(QSize(self.icon_size, self.icon_size))
        pixmap = utils.fixDarkImage(pixmap)

        if self.h_tabbar:
            pixmapRotated = pixmap
        else:
            pixmapRotated = pixmap.transformed(QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation)

        tabIndex = self.ui.tabs.indexOf(browser)
        self.ui.tabs.tabBar().setTabIcon(tabIndex, QIcon(pixmapRotated))

        filename = self._getIconFileName(browser.url())
        iconFile = os.path.join(self.tabIconsFolder, filename)
        if not os.path.exists(iconFile):
            pixmap.save(iconFile, "PNG")

        if self.settings.enableHistory:
            # update icon since it is asynchronous once the url changes (the icon file name was set when entry added)
            iconFile = os.path.join(self.history_manager.historyFolder, filename)
            self.history_widget.updateEntryIcon(icon, iconFile)

    def _getIconFileName(self, qurl):
        filename = DefaultSettings.Icons.loading
        if qurl.isValid():
            host = qurl.host()
            if host:
                hash_object = hashlib.sha256(host.encode())
                filename = str(hash_object.hexdigest())
        return filename

    def add_toggletab_action(self):
        self.toggletab_btn = QLabel()
        self.ui.tabs.insertTab(0, self.toggletab_btn, " ▼ ", True) #🢃⯯⛛▼🞃▼⮟⬎
        self.ui.tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self.ui.tabs.widget(0).setDisabled(True)

    def add_tab_action(self):
        self.addtab_btn = QLabel()
        tabIndex = self.ui.tabs.addTab(self.addtab_btn, " ✚ ", True)
        self.ui.tabs.tabBar().setTabButton(tabIndex, QTabBar.ButtonPosition.RightSide, None)
        self.ui.tabs.widget(tabIndex).setDisabled(True)
        self.ui.tabs.tabBar().setTabToolTip(tabIndex, "New tab")

    # method for adding new tab when requested by user
    def add_new_tab(self, qurl=None, setFocus=True):
        self.ui.tabs.removeTab(self.ui.tabs.count() - 1)
        qurl = qurl or QUrl(DefaultSettings.Browser.defaultPage)
        if setFocus:
            tabIndex = self.add_tab(qurl)
        else:
            tabIndex = self.add_tab(qurl, tabIndex=self.ui.tabs.currentIndex() + 1)
        self.update_urlbar(self.ui.tabs.currentWidget().url(), self.ui.tabs.currentWidget())
        self.add_tab_action()
        if setFocus:
            self.ui.tabs.setCurrentIndex(tabIndex)

    # method to update the url when tab is changed
    def navigate_to_url(self):

        # get the line edit text and convert it to QUrl object
        qurl = QUrl(self.ui.urlbar.text())

        # search url bar content if it is not a valid url
        if not qurl.isValid() or ((" " in qurl.toString() or "." not in qurl.toString()) and qurl.scheme() not in ("chrome", "file")):
            # search in Google
            # qurl.setUrl("https://www.google.es/search?q=%s&safe=off" % self.urlbar.text())
            # search in DuckDuckGo (safer)
            qurl.setUrl("https://duckduckgo.com/?t=h_&hps=1&start=1&q=%s&ia=web&kae=d" % self.ui.urlbar.text().replace(" ", "+"))

        # if scheme is blank
        if qurl.scheme() == "":
            # set scheme
            qurl.setScheme("https")
            qurl = QUrl(qurl.toString().replace("https:", "https://"))

        browser = self.ui.tabs.currentWidget()
        url = qurl.toString()
        self.tabsActivity[browser] = [url, "", 1.0, time.time(), False, False]

        # set the url
        QTimer.singleShot(0, lambda u=qurl: self.ui.tabs.currentWidget().load(u))

    def checkTabsActivityTrigger(self):
        self.checkTabsActivitySig.emit()

    @pyqtSlot()
    def checkTabsActivity(self):
        tabKeys = list(self.tabsActivity.keys())
        currTime = time.time()
        for browser in tabKeys:
            url, title, zoom, lastTimeLoaded, frozen, isPlayingMedia = self.tabsActivity[browser]
            if browser == self.ui.tabs.currentWidget() or isPlayingMedia:
                lastTimeLoaded = currTime
            if not frozen and currTime - lastTimeLoaded > DefaultSettings.Tabs.suspendTime:
                if isinstance(browser, QWebEngineView):
                    # destroy qwebengineview to free resources and create a dummy qlabel widget
                    zoom = browser.page().zoomFactor()
                    browser = self._replaceInactiveBrowser(browser, self.ui.tabs.indexOf(browser), QUrl(url), title, zoom)
                frozen = True
                LOGGER.write(LoggerSettings.LogLevels.info, "Main", f"Tab suspended: {self.ui.tabs.indexOf(browser)}, {title}")
            self.tabsActivity[browser] = [url, title, zoom, lastTimeLoaded, frozen, isPlayingMedia]

    def current_tab_changed(self, tabIndex):

        if tabIndex <= 0:
            self.ui.tabs.setCurrentIndex(self.prevTabIndex or 1)

        elif tabIndex >= self.ui.tabs.count() - 1:
            self.ui.tabs.setCurrentIndex(self.ui.tabs.count() - 2)

        else:

            browser = self.ui.tabs.widget(tabIndex)
            tabData = self.tabsActivity.get(browser, None)
            if tabData:

                url, title, zoom, _, frozen, isPlayingMedia = tabData
                qurl = QUrl(url)
                # update the url
                QTimer.singleShot(0, lambda q=qurl, b=browser: self.update_urlbar(q, b))

                if isinstance(browser, QLabel):
                    # create qwebengineview if page was suspended and load url
                    browser = self._replaceInactiveBrowser(browser, tabIndex, qurl, title, zoom)
                self.tabsActivity[browser] = [url, title, zoom, time.time(), False, isPlayingMedia]

                if DefaultSettings.Media.checkPageCanPlayMedia and url and url not in self.checkedURL:
                    self.checkedURL.append(url)
                    browser.page().mediaCheck.checkCanPlayMedia(url)

            # manage stop/reload button
            if isinstance(browser, QWebEngineView):
                page = browser.page()
                if page.isLoading():
                    self.ui.reload_btn.setText(self.ui.stop_char)
                    self.ui.reload_btn.setToolTip("Stop loading page")
                else:
                    self.ui.reload_btn.setText(self.ui.reload_char)
                    self.ui.reload_btn.setToolTip("Reload page")

    def _replaceInactiveBrowser(self, browser, tabIndex, qurl, title, zoom):

        # disconnect signal to avoid repeatedly calling current_tab_changed() when removing and adding tabs
        self.ui.tabs.currentChanged.disconnect()

        # close previous widget and tab
        del self.tabsActivity[browser]
        self.ui.tabs.removeTab(tabIndex)
        isView = isinstance(browser, QWebEngineView)
        if isView:
            self.connectPageSlots(browser.page(), False)
            # sip.delete(browser.page())
            self.connectBrowserSlots(browser, False)
        # sip.delete(browser)
        browser.close()

        # create new widget in add_tab() method (QWebEngineView if it was QLabel and vice versa)
        icon = self._getIconFileName(qurl)
        tabIndex = self.add_tab(qurl, zoom, title, not isView, icon, tabIndex)
        # self.ui.tabs.setTabIcon(tabIndex, self._getTabIcon(self._getIconFileName(qurl), not isView))
        if not isView:
            self.ui.tabs.setCurrentIndex(tabIndex)

        # reconnect signal for current index changed
        self.ui.tabs.currentChanged.connect(self.current_tab_changed)

        return self.ui.tabs.widget(tabIndex)

    def tab_clicked(self, tabIndex):

        if QApplication.mouseButtons() == Qt.MouseButton.LeftButton:
            if tabIndex == 0:
                self.prevTabIndex = self.ui.tabs.currentIndex()
                self.toggle_tabbar(clicked=True)

            elif tabIndex == self.ui.tabs.count() - 1:
                # this is needed to immediately refresh url bar content (maybe locked by qwebengineview?)
                QTimer.singleShot(0, lambda p=DefaultSettings.Browser.defaultPage: self.ui.urlbar.setText(p))
                self.add_new_tab()

    def tab_moved(self, to_index, from_index):

        if to_index >= self.ui.tabs.count() - 1:
            # Avoid moving last tab (add new tab) if dragging another tab onto it
            # self.ui.tabs.removeTab(from_index)
            # self.add_tab_action()
            self.ui.tabs.tabBar().moveTab(from_index, self.ui.tabs.count() - 1)

        elif to_index <= 0:
            # Avoid moving first tab (toggle tab orientation) if dragging another tab onto it
            # self.ui.tabs.removeTab(from_index)
            # self.add_toggletab_action()
            self.ui.tabs.tabBar().moveTab(from_index, 0)

    def tab_closed(self, browser):

        tabIndex = self.ui.tabs.indexOf(browser)

        # if there is only one tab
        if self.ui.tabs.count() <= 3:
            if self.isNewWin:
                # close additional window only
                self.close()
            else:
                # close application
                QCoreApplication.quit()

        else:
            # calculate next tab position
            targetIndex = self.ui.tabs.currentIndex() if tabIndex != self.ui.tabs.currentIndex() else self.ui.tabs.currentIndex() + 1

            tabData = self.tabsActivity.get(browser, None)
            title = ""
            if tabData is not None:
                _, title, _, _, _, _ = tabData
                del self.tabsActivity[browser]

            # remove tab and delete tab widget safely
            self.ui.tabs.removeTab(tabIndex)
            if isinstance(browser, QWebEngineView):
                self.connectPageSlots(browser.page(), False)
                # sip.delete(browser.page())
                self.connectBrowserSlots(browser, False)
            # sip.delete(browser)
            browser.close()

            # adjust target tab index according to new tabs number (but not tab 0, the toggle button)
            if targetIndex >= self.ui.tabs.count() - 1:
                targetIndex = self.ui.tabs.count() - 2
            elif targetIndex <= 0:
                targetIndex = 1
            self.ui.tabs.setCurrentIndex(targetIndex)

            LOGGER.write(LoggerSettings.LogLevels.info, "Main", f"Tab closed: {title}")

    def toggle_tabbar(self, clicked=True):

        if clicked:
            self.h_tabbar = not self.h_tabbar

        # set tabs properties first
        self.ui.tabs.setStyleSheet(self.h_tab_style if self.h_tabbar else self.v_tab_style)
        self.ui.tabs.tabBar().setStyleSheet(self.h_tab_style if self.h_tabbar else self.v_tab_style)
        self.ui.tabs.setTabPosition(QTabWidget.TabPosition.North if self.h_tabbar else QTabWidget.TabPosition.West)
        self.ui.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu if self.h_tabbar else Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.tabs.setTabToolTip(0, "Set %s tabs" % ("vertical" if self.h_tabbar else "horizontal"))

        # second, enable buttons (only if horizontal tabbar), and disable for custom control tabs
        self.ui.tabs.setTabsClosable(self.h_tabbar)
        self.ui.tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self.ui.tabs.tabBar().setTabButton(self.ui.tabs.count() - 1, QTabBar.ButtonPosition.RightSide, None)

        # reorganize tabs
        for i in range(1, self.ui.tabs.count() - 1):
            browser = self.ui.tabs.widget(i)
            icon = self.ui.tabs.tabIcon(i)
            if self.h_tabbar:
                new_icon = QIcon(icon.pixmap(QSize(self.icon_size, self.icon_size)).transformed(QTransform().rotate(-90), Qt.TransformationMode.SmoothTransformation))
                tabData = self.tabsActivity.get(browser, None)
                title = ""
                if tabData is not None:
                    _, title, _, _, _, _ = tabData
                self.ui.tabs.setTabText(i, title if self.h_tabbar else "")
                self.ui.tabs.setTabToolTip(i, title + ("" if self.h_tabbar else "\n(Right-click to close)"))
                self.ui.tabs.tabBar().tabButton(i, QTabBar.ButtonPosition.RightSide).clicked.connect(lambda checked, b=browser: self.tab_closed(b))
            else:
                new_icon = QIcon(icon.pixmap(QSize(self.icon_size, self.icon_size)).transformed(QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation))
                self.ui.tabs.setTabText(i, "")
            self.ui.tabs.tabBar().setTabIcon(i, new_icon)

        targetRect = self.ui.tabs.tabBar().tabRect(0)
        self.ui.auto_btn.setFixedSize(targetRect.height() if self.h_tabbar else targetRect.width(), self.ui.closewin_btn.height())
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
                # if not self.ui.hoverHWidget.isVisible() and not self.ui.hoverHWidget.underMouse():
                # this... fails sometimes???? WHY?????
                # hypothesis: if nav tab is under mouse it will not hide, so trying to show hoverHWidget in the same position fails
                # solution: moving the mouse out of the nav bar
                curPos = QCursor.pos(self.screen())
                x = (self.x() + self.ui.tabs.tabBar().width()) if not self.h_tabbar else curPos.x()
                y = self.y() + self.ui.navtab.height()
                QCursor.setPos(x, y)
                self.ui.navtab.hide()
                self.ui.tabs.tabBar().hide()
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

    def goBack(self):
        self.ui.tabs.currentWidget().back()

    def goForward(self):
        self.ui.tabs.currentWidget().forward()

    def reloadPage(self):
        if self.ui.reload_btn.text() == self.ui.reload_char:
            QTimer.singleShot(0, lambda: self.ui.tabs.currentWidget().reload())
        else:
            self.ui.tabs.currentWidget().stop()

    def update_urlbar(self, qurl, browser = None):

        # If this signal is not from the current tab, ignore
        if browser != self.ui.tabs.currentWidget():
            # do nothing
            return

        # set text to the url bar
        self.ui.urlbar.setText(qurl.toString())

        # Enable/Disable navigation arrows according to page history
        if not sip.isdeleted(browser) and isinstance(browser, QWebEngineView):
            self.ui.back_btn.setEnabled(browser.history().canGoBack())
            self.ui.next_btn.setEnabled(browser.history().canGoForward())

    def openExternalPlayer(self):
        page = self.ui.tabs.currentWidget().page()
        page.externalPlayer.openInExternalPlayer(page.url().toString())
        LOGGER.write(LoggerSettings.LogLevels.info, "Main", f"Opening external player: {DefaultSettings.Player.externalPlayerType.value} for page: {page.title()}")

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

    def manage_search(self, forceHide=False):
        if self.search_widget.isVisible() or forceHide:
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

    def get_dl_manager_pos(self):

        # getting title bar height (custom or standard)
        gap = self.mapToGlobal(self.ui.navtab.pos()).y() - self.y()

        # take the visible action as reference to calculate position
        refWidget = self.ui.dl_off_btn if self.ui.dl_off_btn.isVisible() else self.ui.dl_on_btn

        # calculate position
        actRect = refWidget.geometry()
        actPos = self.mapToGlobal(actRect.topLeft())
        x = actPos.x()
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
            browser = self.ui.tabs.widget(i)
            if isinstance(browser, QWebEngineView):
                browser.settings().setAttribute(QWebEngineSettings.WebAttribute.ForceDarkMode, self.dark_mode)
                browser.reload()

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

    def manage_adblock(self, clicked):

        if clicked:
            self.adblock = not self.adblock
        self.requestInterceptor.setEnabled(self.adblock)
        self.ui.adblock_btn.setText("🛑" if self.adblock else "📢")
        self.ui.adblock_btn.setToolTip("Adblocker is now %s (ads are %s)"
                                       % (("enabled", "blocked") if self.adblock else ("disabled", "allowed")))

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

        if self.isIncognito:
            # this works quite well, it's quicker and less aggressive (in incognito mode, all will be deleted anyway)
            for i in range(1, self.ui.tabs.count() - 1):
                browser = self.ui.tabs.widget(i)
                if isinstance(browser, QWebEngineView):
                    page = browser.page()
                    profile = page.profile()
                    profile.clearHttpCache()
                    profile.clearAllVisitedLinks()
                    cookieStore = profile.cookieStore()
                    cookieStore.deleteSessionCookies()
                    cookieStore.deleteAllCookies()
                    browser.reload()

        else:
            # this is more aggressive and slower, but guarantees everything is completely and immediately wiped!!
            # activate cache deletion upon closing app (if not incognito which will be auto-deleted)
            self.cache_manager.deleteCacheRequested = True

            # set a new cache folder (old ones will be deleted when app is restarted)
            self.dontCloseOnRelaunch = True
            self.close()

    def showMaxRestore(self):

        if self.isMaximized():
            self.showNormal()
            self.ui.max_btn.setText(self.ui.max_chr)
            self.ui.max_btn.setToolTip("Maximize")

        else:
            self.showMaximized()
            self.ui.max_btn.setText(self.ui.rest_chr)
            self.ui.max_btn.setToolTip("Restore")

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

        url = request.requestedUrl().toString()
        if request.destination() == QWebEngineNewWindowRequest.DestinationType.InNewWindow:
            self.show_in_new_window([[url, 1.0, True, False, ""]])
            LOGGER.write(LoggerSettings.LogLevels.info, "Main", f"New window open: {url}")

        elif request.destination() == QWebEngineNewWindowRequest.DestinationType.InNewTab:
            self.add_new_tab(QUrl(url), setFocus=False)
            LOGGER.write(LoggerSettings.LogLevels.info, "Main", f"New tab open: {url}")

        elif request.destination() == QWebEngineNewWindowRequest.DestinationType.InNewDialog:
            if request.isUserInitiated():
                self.show_in_new_dialog(request)
                LOGGER.write(LoggerSettings.LogLevels.info, "Main", f"New dialog open: {url}")
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

        elif a0.key() == Qt.Key.Key_E:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.manage_autohide()

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

        elif a0.key() == Qt.Key.Key_C:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                if not self.ui.tabs.currentWidget().hasSelection():
                    self.clipboard.setText(self.ui.urlbar.text(), QClipboard.Mode.Clipboard)

        elif a0.key() == Qt.Key.Key_U:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                url = self.clipboard.text(QClipboard.Mode.Clipboard)
                if url:
                    self.update_urlbar(QUrl(url), self.ui.tabs.currentWidget())
                    self.navigate_to_url()

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
            self.cache_manager.deleteCache()
            LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Previous cache deleted")
        if OPTIONS.deletePlayerTemp:
            if os.path.exists(DefaultSettings.Storage.App.tempFolder):
                try:
                    shutil.rmtree(DefaultSettings.Storage.App.tempFolder)
                except:
                    LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Temp folder not found")
            LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Previous temp files deleted")

        if (OPTIONS.deleteCache or OPTIONS.deletePlayerTemp) and not OPTIONS.dontCloseOnRelaunch:
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
            url, title, zoom, _, frozen, _ = self.tabsActivity[browser]
            if isinstance(browser, QWebEngineView):
                url = browser.url().toString()
                page = browser.page()
                page.externalPlayer.closeExternalPlayer(False, url)
                zoom = page.zoomFactor()
            iconFile = self._getIconFileName(QUrl(url))
            tabs.append([url, zoom, title, i == self.ui.tabs.currentIndex(), frozen, iconFile])
        LOGGER.write(LoggerSettings.LogLevels.info, "Main", f"Current tabs saved: {len(tabs)}")

        # save other open windows
        # only open windows when main instance is closed will be remembered
        total_new_tabs = 0
        new_wins = []
        for w in self.instances:

            # check if window is still open
            if w.isVisible():

                # saving open tabs for each instance and closing external players
                new_tabs = []
                for i in range(1, w.ui.tabs.count() - 1):
                    browser = w.ui.tabs.widget(i)
                    url, title, zoom, _, frozen, _ = self.tabsActivity[browser]
                    if isinstance(browser, QWebEngineView):
                        url = browser.url().toString()
                        page = browser.page()
                        page.externalPlayer.closeExternalPlayer(False, url)
                        zoom = page.zoomFactor()
                    iconFile = self._getIconFileName(QUrl(url))
                    new_tabs.append([url, zoom, title, i == self.ui.tabs.currentIndex(), frozen, iconFile])
                    total_new_tabs += 1

                # won't keep any incognito data
                if not w.isIncognito:
                    new_wins.append(new_tabs)

            # closing all other open child windows
            w.close()
        LOGGER.write(LoggerSettings.LogLevels.info, "Main", f"New windows saved: {len(new_wins)} / tabs: {total_new_tabs}")

        # only main window can save settings
        if not self.isNewWin and not self.isIncognito:
            self.saveSettings(tabs, new_wins)

        if not self.isIncognito:
            self.history_manager.saveHistory()

        args = []
        if self.cache_manager.deleteCacheRequested and not self.isNewWin and not self.isIncognito:
            # restart app to wipe all cache folders but the last one (not possible while running since it's locked)
            args += [appconfig.Options.deleteCache]
            if self.dontCloseOnRelaunch:
                args += [appconfig.Options.dontCloseOnRelaunch]
            LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Restart application to delete cache")

        if os.path.exists(DefaultSettings.Storage.App.tempFolder):
            args += [appconfig.Options.deletePlayerTemp]
            LOGGER.write(LoggerSettings.LogLevels.info, "Main", "Restart application to delete temp files")

        if args:
            status = QProcess.startDetached(sys.executable, sys.argv + args, os.getcwd())


def main():

    # app-independent settings (some must be done BEFORE creating app)
    appconfig.preInitializeApp(OPTIONS)

    # create app
    app = QApplication(sys.argv + ['-platform', 'windows:darkmode=1'])

    # launch splash screen, though main app usually starts very quick...
    # ... check in other systems to decide if needed or just for aesthetics
    if DefaultSettings.Splash.enableSplash and not OPTIONS.dontCloseOnRelaunch:
        splash = Splash()
        splash.start(app)

    # create and show main window
    window = MainWindow()
    window.show()

    # hide splash and sync with main window
    if DefaultSettings.Splash.enableSplash and not OPTIONS.dontCloseOnRelaunch:
        splash.stop(window)

    # run app
    app.exec()


if __name__ == "__main__":
    main()
