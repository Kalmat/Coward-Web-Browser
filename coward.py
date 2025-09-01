# based on: https://www.geeksforgeeks.org/python/creating-a-tabbed-browser-using-pyqt5/
import os
import re
import shutil
import subprocess
import sys
import time
import traceback

import psutil
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWebEngineCore import *
from PyQt6.QtWebEngineWidgets import *
from PyQt6.QtWidgets import *


# main window
class MainWindow(QMainWindow):

    _gripSize = 8
    enterHHoverSig = pyqtSignal()
    leaveHHoverSig = pyqtSignal()
    enterVHoverSig = pyqtSignal()
    leaveVHoverSig = pyqtSignal()
    enterNavBarSig = pyqtSignal()
    leaveNavBarSig = pyqtSignal()
    enterTabBarSig = pyqtSignal()
    leaveTabBarSig = pyqtSignal()
    mediaErrorSignal = pyqtSignal(QWebEnginePage)

    # constructor
    def __init__(self, parent=None, new_win=False, init_tabs=None, incognito=None):
        super(MainWindow, self).__init__(parent)

        # prepare cache folders and variables
        self.cachePath = ""
        self.lastCache = ""
        self.storageName = "coward_" + str(qWebEngineChromiumVersion()) + ("_debug" if is_packaged() else "")
        self.deleteCache = False

        # wipe all cache folders except the last one if requested by user (in a new process or it will be locked)
        if "--delete_cache" in sys.argv:
            lastCache = sys.argv[-1]
            lastCacheName = os.path.basename(lastCache)
            cacheFolder = os.path.dirname(lastCache)
            tempCache = os.path.join(os.path.dirname(cacheFolder), lastCacheName)
            shutil.move(lastCache, tempCache)
            shutil.rmtree(cacheFolder)
            shutil.move(tempCache, cacheFolder)
            QApplication.quit()
            sys.exit(0)

        self.isNewWin = new_win
        self.homePage = 'https://start.duckduckgo.com/?kae=d'
        if (self.isNewWin and not init_tabs) or incognito:
            init_tabs = [[self.homePage, 1.0, True]]
        self.init_tabs = init_tabs

        # setting window title and icon
        self.setWindowTitle("Coward")
        self.setWindowIcon(QIcon(resource_path("res/coward.png")))

        # if not setting this, main window loses focus and flickers... ????
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # get styles from qss folder
        with open(resource_path("qss/main.qss"), "r") as f:
            style = f.read()

        self.setStyleSheet(style)
        app.setStyleSheet(style)

        # This is required by sidegrips to make them invisible (hide dots)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Icons
        # as images
        self.web_ico = QIcon(resource_path("res/web.png"))
        # as path for qss files (path separator inverted: "/")
        self.tabsep_ico_inv = resource_path("res/tabsep.png", True)

        # Set tracking mouse ON if needed
        # self.setMouseTracking(True)

        self.screenSize = self.screen().availableGeometry()

        # get settings
        self.settings = QSettings(QSettings.Format.IniFormat,
                                  QSettings.Scope.UserScope,
                                  ".kalmat",
                                  "Coward" + ("_debug" if is_packaged() else "")
                                  )

        self.cachePath = os.path.join(os.path.dirname(self.settings.fileName()), ".cache", self.storageName)

        # custom / standard title bar
        self.custom_titlebar = self.settings.value("Appearance/custom_title", True) in (True, "true")
        self.autoHide = self.settings.value("Appearance/auto_hide", False) in (True, "true")
        self.prevAutoHide = self.autoHide

        # set initial position and size
        pos = self.settings.value("Window/pos", QPoint(100, 100))
        x, y = pos.x(), pos.y()
        size = self.settings.value("Window/size", QSize(min(self.screenSize.width() // 2, 1024), min(self.screenSize.height() - 200, 1024)))
        w, h = size.width(), size.height()
        gap = 0 if self.custom_titlebar else 50
        if self.isNewWin:
            x += 50
            y += 50
            gap += 50
        x = max(0, min(x, self.screenSize.width() - w))
        y = max(gap, min(y, self.screenSize.height() - h))
        w = max(800, min(w, self.screenSize.width() - x))
        h = max(600, min(h, self.screenSize.height() - y))
        self.setGeometry(x, y, w, h)
        self.setMinimumWidth(48*16)
        self.setMinimumHeight(96)

        # draw rounded corners in case border radius is != 0
        self.radius = int(self.settings.value("Appearance/border_radius", 0))

        # set icon size (also affects to tabs and actions sizes)
        # since some "icons" are actually characters, we should also adjust fonts or stick to values between 24 and 32
        self.icon_size = max(24, min(32, int(self.settings.value("Appearance/icon_size", 24))))
        self.action_size = self.icon_size + max(16, self.icon_size // 2)

        # tab bar styles
        with open(resource_path("qss/h_tabs.qss"), "r") as f:
            self.h_tab_style = f.read()
            self.h_tab_style = self.h_tab_style % (self.tabsep_ico_inv, self.action_size, int(self.action_size * 0.75))

        with open(resource_path("qss/v_tabs.qss"), "r") as f:
            self.v_tab_style = f.read()
            self.v_tab_style = self.v_tab_style % (self.action_size, self.action_size)

        # Enable/Disable cookies
        if new_win and incognito is not None:
            self.isIncognito = incognito
            self.cookies = True
        else:
            self.isIncognito = False
            self.cookies = self.settings.value("General/cookies", True) in (True, "true")

        # vertical / horizontal tabbar
        self.h_tabbar = self.settings.value("Appearance/h_tabbar", False) in (True, "true")

        if self.custom_titlebar:
            self.sideGrips = [
                SideGrip(self, Qt.Edge.LeftEdge),
                SideGrip(self, Qt.Edge.TopEdge),
                SideGrip(self, Qt.Edge.RightEdge),
                SideGrip(self, Qt.Edge.BottomEdge),
            ]
            # corner grips should be "on top" of everything, otherwise the side grips
            # will take precedence on mouse events, so we are adding them *after*;
            # alternatively, widget.raise_() can be used
            self.cornerGrips = [QSizeGrip(self) for i in range(4)]

        # creating download manager before custom title bar to allow moving it too
        self.dl_manager = DownloadManager(self)
        self.dl_manager.hide()

        # creating search widget before custom title bar to allow moving it too
        self.search_widget = SearchWidget(self, self.searchPage)
        self.search_widget.hide()

        # creating a toolbar for navigation
        self.navtab = TitleBar(self, self.custom_titlebar, [], None, self.leaveNavBarSig)
        if self.isIncognito:
            with open(resource_path("qss/titlebar_incognito.qss")) as f:
                navStyle = f.read()
        else:
            with open(resource_path("qss/titlebar.qss")) as f:
                navStyle = f.read()
        self.navtab.setStyleSheet(navStyle)

        self.navtab.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.navtab.setMovable(False)
        self.navtab.setFloatable(False)
        self.navtab.setFloatable(False)
        self.addToolBar(self.navtab)

        # adding toggle vertical / horizontal tabbar button
        self.toggleTab_btn = QToolButton(self.navtab)
        self.toggleTab_btn.setObjectName("toggle_tab")
        font = self.toggleTab_btn.font()
        font.setPointSize(font.pointSize() + 2)
        self.toggleTab_btn.setFont(font)
        self.toggleTab_btn.clicked.connect(lambda: self.toggle_tabbar(clicked=True))
        self.navtab.addWidget(self.toggleTab_btn)
        if self.isIncognito:
            self.toggleTab_btn.setDisabled(True)

        self.navtab.addSeparator()

        # creating back action
        self.back_btn = QAction("🡠", self.navtab)
        font = self.back_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.back_btn.setFont(font)
        self.back_btn.setDisabled(True)
        self.back_btn.setToolTip("Back to previous page")
        self.back_btn.triggered.connect(self.goBack)
        self.navtab.addAction(self.back_btn)

        # adding next button
        self.next_btn = QAction("🡢", self.navtab)
        font = self.next_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.next_btn.setFont(font)
        self.next_btn.setDisabled(True)
        self.next_btn.setToolTip("Forward to next page")
        self.next_btn.triggered.connect(self.goForward)
        self.navtab.addAction(self.next_btn)

        # adding reload / stop button
        self.reload_char = "⟳"
        self.stop_char = "⤬"
        self.reload_btn = QAction(self.reload_char, self.navtab)
        font = self.reload_btn.font()
        font.setPointSize(font.pointSize() + 10)
        self.reload_btn.setFont(font)
        self.reload_btn.setToolTip("Reload page")
        self.reload_btn.triggered.connect(self.reloadPage)
        self.navtab.addAction(self.reload_btn)

        # adding a space in between to allow moving the window in all sizes
        spacer = QLabel()
        spacer.setObjectName("spacer")
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        spacer.setMinimumWidth(20)
        spacer.setMaximumWidth(150)
        self.navtab.addWidget(spacer)

        # creating a line edit widget for URL
        self.urlbar = LineEdit()
        self.urlbar.setMaximumHeight(self.action_size - 6)
        self.urlbar.setTextMargins(10, 0, 0, 0)
        self.urlbar.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.urlbar.returnPressed.connect(self.navigate_to_url)
        self.navtab.addWidget(self.urlbar)

        # adding a space in between to allow moving the window in all sizes
        spacer = QLabel()
        spacer.setObjectName("spacer")
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        spacer.setMinimumWidth(0)
        spacer.setMaximumWidth(150)
        self.navtab.addWidget(spacer)

        # adding auto-hide mgt.
        self.auto_on_char = "⇲"
        self.auto_off_char = "⇱"
        self.auto_btn = QAction(self.auto_on_char if self.autoHide else self.auto_off_char, self.navtab)
        font = self.auto_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.auto_btn.setFont(font)
        self.auto_btn.setToolTip("Auto-hide is now " + ("Enabled" if self.autoHide else "Disabled"))
        self.auto_btn.triggered.connect(self.manage_autohide)
        self.navtab.addAction(self.auto_btn)

        # adding search option
        self.search_on_btn = QToolButton(self.navtab)
        self.search_on_btn.setObjectName("search_on")
        font = self.search_on_btn.font()
        font.setPointSize(font.pointSize() + 8)
        self.search_on_btn.setFont(font)
        self.search_on_btn.setText("⌕")
        self.search_on_btn.setToolTip("Search text in this page")
        self.search_on_btn.clicked.connect(self.manage_search)
        self.search_on_act = self.navtab.addWidget(self.search_on_btn)

        self.search_off_btn = QToolButton(self.navtab)
        self.search_off_btn.setObjectName("search_off")
        font = self.search_off_btn.font()
        font.setPointSize(font.pointSize() + 8)
        self.search_off_btn.setFont(font)
        self.search_off_btn.setText("⌕")
        self.search_off_btn.setToolTip("Search text in this page")
        self.search_off_btn.clicked.connect(self.manage_search)
        self.search_off_act = self.navtab.addWidget(self.search_off_btn)
        self.search_off_act.setVisible(False)

        # adding downloads mgt.
        self.dl_on_btn = QToolButton(self.navtab)
        self.dl_on_btn.setObjectName("dl_on")
        font = self.dl_on_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.dl_on_btn.setFont(font)
        self.dl_on_btn.setText("🡣")
        self.dl_on_btn.setToolTip("Show / hide downloads")
        self.dl_on_btn.clicked.connect(self.manage_downloads)
        self.dl_on_act = self.navtab.addWidget(self.dl_on_btn)

        self.dl_off_btn = QToolButton(self.navtab)
        self.dl_off_btn.setObjectName("dl_off")
        font = self.dl_off_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.dl_off_btn.setFont(font)
        self.dl_off_btn.setText("🡣")
        self.dl_off_btn.setToolTip("Show / hide downloads")
        self.dl_off_btn.clicked.connect(self.manage_downloads)
        self.dl_off_act = self.navtab.addWidget(self.dl_off_btn)
        self.dl_off_act.setVisible(False)

        self.navtab.addSeparator()

        # adding cookie mgt.
        self.cookie_btn = QAction("", self.navtab)
        font = self.cookie_btn.font()
        font.setPointSize(font.pointSize() + 4)
        self.cookie_btn.setFont(font)
        self.manage_cookies(clicked=False)
        self.cookie_btn.triggered.connect(lambda: self.manage_cookies(clicked=True))
        self.navtab.addAction(self.cookie_btn)

        # adding cleaning mgt.
        self.clean_btn = QAction("🧹", self.navtab)
        font = self.clean_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.clean_btn.setFont(font)
        self.clean_btn.setToolTip("Erase history and cookies")
        self.clean_btn.triggered.connect(self.show_clean_dlg)
        self.navtab.addAction(self.clean_btn)

        # adding open incognito window 🕶️🕶🥷👻
        self.ninja_btn = QToolButton( self.navtab)
        self.ninja_btn.setObjectName("incognito")
        self.ninja_btn.setText("👻")
        font = self.ninja_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.ninja_btn.setFont(font)
        self.ninja_btn.setToolTip("Open new window in incognito mode")
        self.ninja_btn.clicked.connect(lambda: self.show_in_new_window(incognito=True))
        self.ninja_act = self.navtab.addWidget(self.ninja_btn)
        if self.isNewWin:
            if self.isIncognito:
                self.ninja_act.setDisabled(True)
            else:
                self.ninja_act.setVisible(False)

        if self.custom_titlebar:

            self.navtab.addSeparator()

            self.min_btn = QAction("―", self.navtab)
            self.min_btn.setToolTip("Minimize")
            font = self.min_btn.font()
            font.setPointSize(font.pointSize() + 2)
            self.min_btn.setFont(font)
            self.min_btn.triggered.connect(self.showMinimized)
            self.navtab.addAction(self.min_btn)

            self.max_btn = QAction(" ⃞ ", self.navtab)
            self.max_btn.setToolTip("Maximize")
            font = self.max_btn.font()
            font.setPointSize(font.pointSize() + 4)
            self.max_btn.setFont(font)
            self.max_btn.triggered.connect(self.showMaxRestore)
            self.navtab.addAction(self.max_btn)

            self.closewin_btn = QAction("🕱", self.navtab)
            self.closewin_btn.setToolTip("Quit, coward")
            font = self.closewin_btn.font()
            font.setPointSize(font.pointSize() + 8)
            self.closewin_btn.setFont(font)
            self.closewin_btn.triggered.connect(self.close)
            self.navtab.addAction(self.closewin_btn)

        # creating a tab widget
        self.tabs = QTabWidget(self)
        self.tabBar = TabBar(self.tabs, None, self.leaveTabBarSig)
        self.tabs.setTabBar(self.tabBar)
        self.tabs.setStyleSheet(self.h_tab_style if self.h_tabbar else self.v_tab_style)
        self.tabs.setMovable(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North if self.h_tabbar else QTabWidget.TabPosition.West)
        self.tabs.tabBar().setContentsMargins(0, 0, 0, 0)
        self.tabs.tabBar().setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.tabs.tabBar().setIconSize(QSize(self.icon_size, self.icon_size))
        self.tabs.tabBar().tabMoved.connect(self.tab_moved)

        # creating a context menu to allow closing tabs when close button is hidden
        self.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.showContextMenu)
        self.tabsContextMenu = QMenu()
        self.tabsContextMenu.setMinimumHeight(self.action_size + 6)
        self.tabsContextMenu.setContentsMargins(0, 5, 0, 0)
        self.close_action = QAction()
        self.close_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical))
        self.tabsContextMenu.addAction(self.close_action)

        # creating a context menu to allow closing tabs when close button is hidden
        self.newTabContextMenu = QMenu()
        self.newTabContextMenu.setMinimumHeight(self.action_size + 6)
        self.newTabContextMenu.setContentsMargins(0, 5, 0, 0)
        self.newWindow_action = QAction()
        self.newWindow_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton))
        self.newWindow_action.setText("Open new tab in separate window")
        self.newWindow_action.triggered.connect(self.show_in_new_window)
        self.newTabContextMenu.addAction(self.newWindow_action)

        # set tabbar configuration according to orientation
        self.toggle_tabbar(clicked=False)

        # making document mode true
        self.tabs.setDocumentMode(True)

        # adding action when tab is changed
        self.tabs.currentChanged.connect(self.current_tab_changed)

        # adding action when tab is clicked
        self.tabs.tabBarClicked.connect(self.tab_clicked)

        # adding action when tab close is requested
        self.tabs.tabCloseRequested.connect(self.tab_closed)

        # making tabs as central widget
        self.tabs.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCentralWidget(self.tabs)

        # open all windows and their tabs
        if self.isNewWin or self.isIncognito:
            # get open tabs for child window instance
            tabs = self.init_tabs

            # no child windows allowed for child instances
            new_wins = []

        else:
            # get open tabs for  main instance window
            tabs = self.settings.value("Session/tabs", [[self.homePage, 1.0, True]])

            # get child windows instances and their open tabs
            new_wins = self.settings.value("Session/new_wins", []) or []

        # open all tabs in main / child window
        current = 0
        if tabs:
            for tab in tabs:
                qurl, zoom, active = tab
                i = self.add_tab(QUrl(qurl), zoom)
                if active:
                    current = i
        else:
            self.add_tab()
        self.tabs.setCurrentIndex(current)
        self.update_urlbar(self.tabs.currentWidget().url(), self.tabs.currentWidget())
        # this will load the active tab only, saving time at start
        # self.tabs.currentWidget().reload()

        # open child window instances passing their open tabs
        self.instances = []
        for new_tabs in new_wins:
            self.show_in_new_window(new_tabs)

        # keep track of open popups and assure their persintence
        self.popups = []

        # adding add tab action
        self.add_tab_action()

        # set hover areas for auto-hide mode
        # auto-hide navigation bar
        self.hoverHWidget = HoverWidget(self, self.navtab, self.enterHHoverSig)
        self.navtab.setFixedHeight(self.action_size + 4)
        self.hoverHWidget.setGeometry(self.action_size, self.y(), self.width(), 20)
        self.hoverHWidget.hide()
        # auto-hide tab bar
        self.hoverVWidget = HoverWidget(self, self.tabs.tabBar(), self.enterVHoverSig)
        self.hoverVWidget.setGeometry(self.x(), self.action_size, 20, self.height())
        self.hoverVWidget.hide()

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
        self.mediaErrorSignal.connect(self.show_player_request)

        # class variables
        self.maxNormal = self.isMaximized()

        # finally, add widgets which must be moved together with main window when applying custom title bar
        self.otherWidgetsToMove = [self.dl_manager, self.search_widget]
        self.navtab.setOtherWidgetsToMove(self.otherWidgetsToMove)

    def targetDlgPos(self):
        return QPoint(self.x() + 100,
                      self.y() + self.navtab.height() + (self.tabs.tabBar().height() if self.h_tabbar else 0))

    def show(self):
        super().show()

        # need to show first to have actual geometries
        self.toggleTab_btn.setFixedSize(self.tabs.tabBar().width() - 3, self.navtab.height())

        if self.isIncognito:
            self.tabs.tabBar().hide()
        else:
            self.tabs.tabBar().show()

        if self.autoHide:
            self.navtab.hide()
            self.hoverHWidget.setGeometry(self.action_size, 0, self.width(), 20)
            self.hoverHWidget.show()
            self.tabs.tabBar().hide()
            self.hoverVWidget.setGeometry(0, self.action_size, 20, self.height())
            if not self.h_tabbar:
                if self.isIncognito:
                    self.hoverVWidget.hide()
                else:
                    self.hoverVWidget.show()

        # thanks to Maxim Paperno: https://stackoverflow.com/questions/58145272/qdialog-with-rounded-corners-have-black-corners-instead-of-being-translucent
        if self.radius != 0:

            # prepare painter and mask to draw rounded corners
            rect = QRect(QPoint(0, 0), self.geometry().size())
            b = QBitmap(rect.size())
            b.fill(QColor(Qt.GlobalColor.color0))
            painter = QPainter(b)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(Qt.GlobalColor.color1)
            painter.drawRoundedRect(rect, self.radius, self.radius, Qt.SizeMode.AbsoluteSize)
            painter.end()
            self.setMask(b)

    # method for adding new tab
    def add_new_tab(self, qurl=None):
        self.tabs.removeTab(self.tabs.count() - 1)
        i = self.add_tab(qurl)
        self.add_tab_action()
        self.tabs.setCurrentIndex(i)
        self.update_urlbar(self.tabs.currentWidget().url(), self.tabs.currentWidget())

    def add_tab_action(self):
        self.addtab_btn = QLabel()
        i = self.tabs.addTab(self.addtab_btn, " ✚ ")
        self.tabs.tabBar().setTabButton(i, QTabBar.ButtonPosition.RightSide, None)
        self.tabs.widget(i).setDisabled(True)
        self.tabs.tabBar().setTabToolTip(i, "New tab")
        self.tabs.tabBar().setTabToolTip(i, "New tab")

    # method to update the url when tab is changed
    def add_tab(self, qurl=None, zoom=1.0, label="Loading..."):

        # if url is blank
        if qurl is None:
            # creating a default home url
            qurl = QUrl(self.homePage)

        # creating a QWebEngineView object
        browser = QWebEngineView()

        if not self.isIncognito:

            # The profile and all its settings is needed to keep cookies and cache (PyQt6 only, not in PyQt5)
            profile = QWebEngineProfile(self.storageName, browser)
            # QtWebEngine creates this folder, but we will not use it... deleting it
            shutil.rmtree(os.path.dirname(os.path.dirname(profile.persistentStoragePath())))

            # profile cache settings
            profile.setCachePath(self.cachePath)
            # this can be redundant since it is a custom storage (not off-the-record)
            profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)

            # profile permissions settings
            profile.setPersistentPermissionsPolicy(QWebEngineProfile.PersistentPermissionsPolicy.StoreOnDisk)
            if self.lastCache:
                # apply temporary cache location to delete all previous cache when app is closed, but keeping these
                profile.setPersistentStoragePath(self.lastCache)
            else:
                # apply application cache location
                profile.setPersistentStoragePath(self.cachePath)

            # profile cookies settings
            profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
            profile.defaultProfile().cookieStore().setCookieFilter(self.cookie_filter)

            # (AFAIK) profile must be applied in a new page, not at browser level
            page = WebEnginePage(profile, browser, self.mediaErrorSignal)
            browser.setPage(page)

        else:
            page = browser.page()

        # Enabling fullscreen
        browser.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        page.fullScreenRequested.connect(self.fullscr)

        # Preparing asking for permissions
        page.featurePermissionRequested.connect(lambda origin, feature, p=page, b=browser: self.show_feature_request(origin, feature, p, b))
        # Are these included in previous one?
        # page.fileSystemAccessRequested.connect(lambda request, p=page, b=browser: print("FS ACCESS REQUESTED", request))
        # page.permissionRequested.connect(lambda request, p=page, b=browser: print("PERMISSION REQUESTED", request))

        # Enabling some extra features (allegedly safe ones only)
        # page.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        # browser.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        # browser.settings().setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        browser.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        browser.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        browser.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)

        # setting url to browser
        browser.load(qurl)
        # this saves time if launched with several open tabs (will be reloaded in tab_changed() method)
        # browser.stop()

        # setting page zoom factor
        page.setZoomFactor(zoom)

        # setting tab index and default icon
        i = self.tabs.addTab(browser, label if self.h_tabbar else "")

        # adding action to the browser when url changes
        browser.urlChanged.connect(lambda u, b=browser: self.update_urlbar(u, b))

        # check start/finish loading (e.g. for loading animations)
        browser.loadStarted.connect(lambda b=browser, index=i: self.onLoadStarted(b, index))
        browser.loadFinished.connect(lambda a, b=browser, index=i: self.onLoadFinished(a, b, index))

        # adding action to the browser when title or icon change
        page.titleChanged.connect(lambda title, index=i: self.title_changed(title, index))
        page.iconChanged.connect(lambda icon, index=i: self.icon_changed(icon, index))

        # manage file downloads (including pages and files)
        page.profile().downloadRequested.connect(self.download_file)

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

        return i

    def onLoadStarted(self, browser, index):
        self.tabs.setTabIcon(index, self.web_ico)
        if browser == self.tabs.currentWidget():
            self.reload_btn.setText(self.stop_char)
            self.reload_btn.setToolTip("Stop loading page")

    def onLoadFinished(self, a0, browser, index):
        if browser == self.tabs.currentWidget():
            self.reload_btn.setText(self.reload_char)
            self.reload_btn.setToolTip("Reload page")

    def title_changed(self, title, i):
        self.tabs.tabBar().setTabText(i, (("  " + title[:20]) if len(title) > 20 else title) if self.h_tabbar else "")
        self.tabs.setTabToolTip(i, title + ("" if self.h_tabbar else "\n(Right-click to close)"))

    def icon_changed(self, icon, i):

        # works fine but sometimes it takes too long (0,17sec.)... must find another way
        # icon = self.fixDarkImage(icon, self.icon_size, self.icon_size)

        if self.h_tabbar:
            new_icon = icon
        else:
            # icon rotation is required if not using custom painter in TabBar class
            new_icon = QIcon(icon.pixmap(QSize(self.icon_size, self.icon_size)).transformed(QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation))
        self.tabs.tabBar().setTabIcon(i, new_icon)

    def fixDarkImage(self, image, width, height):

        import imageio
        import numpy as np

        if isinstance(image, QIcon):
            isIcon = True
            pixmap = image.pixmap(QSize(width, height))
        else:
            isIcon = False
            pixmap = image

        pixmap.save("temp", "PNG")
        f = imageio.imread("temp", mode="F")

        def is_dark(img, thrshld):
            return np.mean(img) < thrshld

        def changePixmapBackground(pix, width, height):
            new_pixmap = QPixmap(width, height)
            new_pixmap.fill(Qt.GlobalColor.lightGray)
            painter = QPainter(new_pixmap)
            painter.drawPixmap(0, 0, width, height, pix)
            painter.end()
            return new_pixmap

        if is_dark(f, 127):
            pixmap = changePixmapBackground(pixmap, width, height)

        os.remove("temp")
        if isIcon:
            return QIcon(pixmap)
        else:
            return pixmap

    def navigate_to_url(self):

        # get the line edit text and convert it to QUrl object
        qurl = QUrl(self.urlbar.text())

        # if scheme is blank
        if not qurl.isValid() or "." not in qurl.url() or " " in qurl.url():
            # search in Google
            # qurl.setUrl("https://www.google.es/search?q=%s&safe=off" % self.urlbar.text())
            # search in DuckDuckGo (safer)
            qurl.setUrl("https://duckduckgo.com/?t=h_&hps=1&start=1&q=%s&ia=web&kae=d" % self.urlbar.text().replace(" ", "+"))

        elif qurl.scheme() == "":
            # set scheme
            qurl.setScheme("https")

        # set the url
        self.tabs.currentWidget().load(qurl)

    def update_urlbar(self, qurl, browser: QWidget = None):

        # If this signal is not from the current tab, ignore
        if browser != self.tabs.currentWidget():
            # do nothing
            return

        # set text to the url bar
        self.urlbar.setText(qurl.toString())

        # Enable/Disable navigation arrows according to page history
        self.back_btn.setEnabled(browser.history().canGoBack())
        self.next_btn.setEnabled(browser.history().canGoForward())

    def fullscr(self, request):

        if request.toggleOn():
            self.navtab.setVisible(False)
            self.tabs.tabBar().setVisible(False)
            self.hoverHWidget.setVisible(False)
            self.hoverVWidget.setVisible(False)
            request.accept()
            self.showFullScreen()

        else:
            if self.autoHide:
                self.hoverHWidget.setVisible(True)
                if not self.h_tabbar:
                    self.hoverVWidget.setVisible(False)
            else:
                self.navtab.setVisible(True)
                self.tabs.tabBar().setVisible(True)
            request.accept()
            self.showNormal()

    def show_feature_request(self, origin, feature, page, browser):
        self.feature_dlg = Dialog(self,
                                  message="This site:\n%s\n\n"
                                          "is asking for your permission to %s.\n\n"
                                          "Click 'OK' to accept, or 'Cancel' to deny\n"
                                          % (page.title() or origin.toString(), str(feature).replace("Feature.", "")),
                                  radius=8)
        self.feature_dlg.accepted.connect(lambda o=origin, f=feature, p=page, b=browser: self.accept_feature(o, f, p, b))
        self.feature_dlg.rejected.connect(lambda o=origin, f=feature, p=page, b=browser: self.reject_feature(o, f, p, b))
        self.feature_dlg.move(self.targetDlgPos())
        self.feature_dlg.exec()

    def accept_feature(self, origin, feature, page, browser):
        self.feature_dlg.close()
        page.setFeaturePermission(origin, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser)

    def reject_feature(self, origin, feature, page, browser):
        self.feature_dlg.close()
        page.setFeaturePermission(origin, feature, QWebEnginePage.PermissionPolicy.PermissionDeniedByUser)

    @pyqtSlot(QWebEnginePage)
    def show_player_request(self, page):
        self.feature_dlg = Dialog(self,
                                  message="This site:\n%s\n\n"
                                          "contains non-compatible media.\n"
                                          "Do you want to try to load it using an external player?\n\n"
                                          "Click 'OK' to accept, or 'Cancel' to deny\n"
                                          % (page.title() or page.url().toString()),
                                  radius=8)
        self.feature_dlg.accepted.connect(lambda p=page: self.accept_player(p))
        self.feature_dlg.rejected.connect(lambda p=page: self.reject_player(p))
        self.feature_dlg.move(self.targetDlgPos())
        self.feature_dlg.exec()

    def accept_player(self, page):
        self.feature_dlg.close()
        page.openInExternalPlayer()

    def reject_player(self, page):
        self.feature_dlg.close()

    def current_tab_changed(self, i):

        if i < self.tabs.count() - 1:

            # reload url (saves time at start, while not taking much if already loaded)
            # must find a way to reload the first time only, while keeping icon and title
            # we could even kill browser widget after a given time, recreating it when it is clicked again
            # self.tabs.currentWidget().reload()

            # update the url
            self.update_urlbar(self.tabs.currentWidget().url(), self.tabs.currentWidget())

            if self.tabs.currentWidget().page().isLoading():
                self.reload_btn.setText(self.stop_char)
                self.reload_btn.setToolTip("Stop loading page")
            else:
                self.reload_btn.setText(self.reload_char)
                self.reload_btn.setToolTip("Reload page")

        if self.search_widget.isVisible():
            self.tabs.currentWidget().findText("")
            self.search_widget.hide()

    def tab_clicked(self, i):

        if app.mouseButtons() == Qt.MouseButton.LeftButton:
            if i == self.tabs.count() - 1:
                # this is needed to immediately refresh url bar content (maybe locked by qwebengineview?)
                QTimer.singleShot(1, lambda: self.urlbar.setText(self.homePage))
                self.add_new_tab()

    def tab_moved(self, to_index, from_index):

        # updating index-dependent signals when tab is moved
        # destination tab
        self.update_index_dependent_signals(to_index)

        if to_index == self.tabs.count() - 1:
            # Avoid moving last tab (add new tab) if dragging another tab onto it
            self.tabs.removeTab(from_index)
            self.add_tab_action()

        else:
            # origin tab
            self.update_index_dependent_signals(from_index)

    def tab_closed(self, tabIndex, user_requested=True):

        # if there is only one tab
        if self.tabs.count() == 2 and user_requested:
            if self.isNewWin:
                # close additional window only
                self.close()
            else:
                # close application
                QCoreApplication.quit()

        else:
            # else remove the tab
            self.tabs.widget(tabIndex).deleteLater()
            # just removing the tab doesn't destroy associated widget
            self.tabs.widget(tabIndex).deleteLater()
            self.tabs.removeTab(tabIndex)
            if self.tabs.currentIndex() == self.tabs.count() - 1:
                self.tabs.setCurrentIndex(self.tabs.currentIndex() - 1)

        # updating index-dependent signals when tab is moved
        for i in range(tabIndex, self.tabs.count() - 1):
            self.update_index_dependent_signals(i)

    # method for navigate to url
    def update_index_dependent_signals(self, tabIndex):
        browser = self.tabs.widget(tabIndex)
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
        tabIndex = self.tabs.tabBar().tabAt(point)
        if 0 <= tabIndex < self.tabs.count() - 1:
            self.createContextMenu(tabIndex)
        elif tabIndex == self.tabs.count() - 1:
            self.createNewTabContextMenu(tabIndex)

    def createContextMenu(self, i):
        text = self.tabs.tabBar().tabToolTip(i).replace("\n(Right-click to close)", "")
        self.close_action.setText('Close tab: "' + text + '"')
        self.close_action.triggered.disconnect()
        self.close_action.triggered.connect(lambda: self.tab_closed(i))
        tab_rect = self.tabs.tabBar().tabRect(i)
        tab_width = tab_rect.width()
        tab_height = tab_rect.height()
        pos = QPoint(self.tabs.tabBar().x() + tab_width, self.tabs.tabBar().y() + tab_height * i)
        self.tabsContextMenu.exec(self.tabs.mapToGlobal(pos))

    def createNewTabContextMenu(self, i):
        tab_rect = self.tabs.tabBar().tabRect(i)
        tab_width = tab_rect.width()
        tab_height = tab_rect.height()
        pos = QPoint(self.tabs.tabBar().x() + tab_width, self.tabs.tabBar().y() + tab_height * i)
        self.newTabContextMenu.exec(self.tabs.mapToGlobal(pos))

    def openLinkRequested(self, request):

        if request.destination() == QWebEngineNewWindowRequest.DestinationType.InNewWindow:
            self.show_in_new_window([[request.requestedUrl(), 1.0, True]])

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

            for i in range(self.tabs.count() - 1):
                icon = self.tabs.widget(i).page().icon()
                if not icon.availableSizes():
                    icon = self.web_ico
                if self.h_tabbar:
                    self.title_changed(self.tabs.widget(i).page().title(), i)
                    new_icon = icon
                else:
                    self.tabs.tabBar().setTabText(i, "")
                    new_icon = QIcon(icon.pixmap(QSize(self.icon_size, self.icon_size)).transformed(QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation))
                self.tabs.tabBar().setTabIcon(i, new_icon)

        self.tabs.setStyleSheet(self.h_tab_style if self.h_tabbar else self.v_tab_style)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North if self.h_tabbar else QTabWidget.TabPosition.West)
        self.tabs.setTabsClosable(self.h_tabbar)
        self.tabs.tabBar().setTabButton(self.tabs.count() - 1, QTabBar.ButtonPosition.RightSide, None)
        self.tabs.tabBar().setStyleSheet(self.h_tab_style if self.h_tabbar else self.v_tab_style)
        self.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu if self.h_tabbar else Qt.ContextMenuPolicy.CustomContextMenu)
        self.toggleTab_btn.setText("˅" if self.h_tabbar else "˃")
        self.toggleTab_btn.setToolTip("Set %s tabs" % ("vertical" if self.h_tabbar else "horizontal"))

        if self.autoHide:
            if self.h_tabbar:
                if self.isIncognito:
                    self.tabs.tabBar().hide()
                else:
                    self.tabs.tabBar().show()
            if hasattr(self, "hoverHWidget"):
                self.hoverHWidget.show()
            if hasattr(self, "hoverVWidget"):
                if self.h_tabbar:
                    self.hoverVWidget.hide()
                else:
                    if self.isIncognito:
                        self.hoverVWidget.hide()
                    else:
                        self.hoverVWidget.show()

    def goBack(self):
        self.tabs.currentWidget().back()

    def goForward(self):
        self.tabs.currentWidget().forward()

    def reloadPage(self):
        if self.reload_btn.text() == self.reload_char:
            self.tabs.currentWidget().reload()
        else:
            self.tabs.currentWidget().stop()

    def manage_search(self):

        if self.search_widget.isVisible():
            self.tabs.currentWidget().findText("")
            self.search_widget.hide()
            self.search_off_act.setVisible(False)
            self.search_on_act.setVisible(True)

        else:
            refWidget = self.dl_on_btn if self.dl_on_btn.isVisible() else self.dl_off_btn
            actPos = self.mapToGlobal(refWidget.geometry().topLeft())
            x = actPos.x() - self.search_widget.width()
            y = self.y() + self.navtab.height()
            self.search_widget.move(x, y)
            self.search_widget.show()
            self.search_off_act.setVisible(True)
            self.search_on_act.setVisible(False)

    def searchPage(self, checked, forward):
        textToFind = self.search_widget.getText()
        if textToFind:
            if forward:
                self.tabs.currentWidget().findText(textToFind)
            else:
                self.tabs.currentWidget().findText(textToFind, QWebEnginePage.FindFlag.FindBackward)

    def manage_autohide(self, force_show=False):

        self.autoHide = False if force_show else not self.autoHide
        self.auto_btn.setText(self.auto_on_char if self.autoHide else self.auto_off_char)
        self.auto_btn.setToolTip("Auto-hide is now " + ("Enabled" if self.autoHide else "Disabled"))

        if self.autoHide:
            self.navtab.hide()
            self.tabs.tabBar().hide()
            if not self.hoverHWidget.isVisible() and not self.hoverHWidget.underMouse():
                # this... fails???? WHY?????
                # Hypothesis: if nav tab is under mouse it will not hide, so trying to show hoverHWidget in the same position fails
                self.hoverHWidget.show()
            if not self.h_tabbar and not self.isIncognito:
                self.hoverVWidget.show()
            else:
                self.hoverVWidget.hide()

        else:
            self.hoverHWidget.hide()
            self.hoverVWidget.hide()
            self.navtab.show()
            if self.isIncognito:
                self.tabs.tabBar().hide()
            else:
                self.tabs.tabBar().show()

    @pyqtSlot()
    def enterHHover(self):
        if self.autoHide:
            self.hoverHWidget.hide()
            self.navtab.show()
            if self.h_tabbar:
                if self.isIncognito:
                    self.tabs.tabBar().hide()
                else:
                    self.tabs.tabBar().show()

    @pyqtSlot()
    def leaveHHover(self):
        pass

    @pyqtSlot()
    def enterVHover(self):
        if self.autoHide:
            self.hoverVWidget.hide()
            if self.isIncognito:
                self.tabs.tabBar().hide()
            else:
                self.tabs.tabBar().show()

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
                    self.navtab.hide()
                    self.tabs.tabBar().hide()
                    self.hoverHWidget.show()
            else:
                self.navtab.hide()
                self.hoverHWidget.show()

    @pyqtSlot()
    def enterTabBar(self):
        pass

    @pyqtSlot()
    def leaveTabBar(self):
        if self.autoHide:
            if self.h_tabbar:
                if not self.navtab.rect().contains(self.mapFromGlobal(QCursor.pos())):
                    self.navtab.hide()
                    self.tabs.tabBar().hide()
                    self.hoverHWidget.show()
            else:
                self.tabs.tabBar().hide()
                if self.isIncognito:
                    self.hoverVWidget.hide()
                else:
                    self.hoverVWidget.show()

    def manage_downloads(self):

        if self.dl_manager.isVisible():
            self.dl_on_act.setVisible(True)
            self.dl_off_act.setVisible(False)
            self.dl_manager.hide()

        else:
            self.dl_on_act.setVisible(False)
            self.dl_off_act.setVisible(True)
            self.show_dl_manager()

    def show_dl_manager(self):

        self.dl_on_act.setVisible(False)
        self.dl_off_act.setVisible(True)
        self.dl_manager.show()
        x = self.x() + self.width() - self.dl_manager.width()
        y = self.y() + self.navtab.height()
        self.dl_manager.move(x, y)

    # adding action to download files
    def download_file(self, item: QWebEngineDownloadRequest):
        if self.dl_manager.addDownload(item):
            self.show_dl_manager()

    def manage_cookies(self, clicked):

        if clicked:
            self.cookies = not self.cookies
        self.cookie_btn.setText("🍪" if self.cookies else "⛔")
        self.cookie_btn.setToolTip("Cookies are now %s" % ("enabled" if self.cookies else "disabled"))

    def cookie_filter(self, cookie, origin=None):
        # print(f"firstPartyUrl: {cookie.firstPartyUrl.toString()}, "
        # f"origin: {cookie.origin.toString()}, "
        # f"thirdParty? {cookie.thirdParty}"
        # )
        return self.cookies

    def show_clean_dlg(self):
        # Prepare clean all warning dialog
        self.clean_dlg = Dialog(self,
                                message="This will erase all your history and stored cookies.\n\n"
                                        "Are you sure you want to proceed?\n",
                                radius=8)
        self.clean_dlg.accepted.connect(self.accept_clean)
        self.clean_dlg.rejected.connect(self.reject_clean)
        self.clean_dlg.move(self.targetDlgPos())
        self.clean_dlg.exec()

    def accept_clean(self):

        self.clean_dlg.close()

        # activate cache deletion upon closing app
        self.deleteCache = True

        # set a new cache folder (old ones will be deleted when app is restarted)
        self.lastCache = os.path.join(self.cachePath, str(time.time()).replace(".", ""))

        tabsCount = self.tabs.count()
        currIndex = self.tabs.currentIndex()
        self.tabs.setCurrentIndex(0)

        tabs = []
        for i in range(tabsCount - 1):
            browser: QWebEngineView = self.tabs.widget(0)
            page: QWebEnginePage = browser.page()
            tabs.append([page.url(), page.zoomFactor()])
            browser.deleteLater()
            self.tab_closed(0, False)

        self.tab_closed(0, False)

        for item in tabs:
            url, zoom = item
            # new cache storage will be assigned in add_tab() method
            self.add_tab(url, zoom)

        self.add_tab_action()
        self.tabs.setCurrentIndex(currIndex)

    def reject_clean(self):
        self.clean_dlg.close()

    @property
    def gripSize(self):
        return self._gripSize

    def setGripSize(self, size):
        if size == self._gripSize:
            return
        self._gripSize = max(2, size)
        self.updateGrips()

    def updateGrips(self):
        # self.setContentsMargins(*[self.gripSize] * 4)

        outRect = self.rect()
        # an "inner" rect used for reference to set the geometries of size grips
        inRect = outRect.adjusted(self.gripSize, self.gripSize,
                                  -self.gripSize, -self.gripSize)

        # top left
        self.cornerGrips[0].setGeometry(
            QRect(outRect.topLeft(), inRect.topLeft()))
        # top right
        self.cornerGrips[1].setGeometry(
            QRect(outRect.topRight(), inRect.topRight()).normalized())
        # bottom right
        self.cornerGrips[2].setGeometry(
            QRect(inRect.bottomRight(), outRect.bottomRight()))
        # bottom left
        self.cornerGrips[3].setGeometry(
            QRect(outRect.bottomLeft(), inRect.bottomLeft()).normalized())

        # left edge
        self.sideGrips[0].setGeometry(
            0, inRect.top(), self.gripSize, inRect.height())
        # top edge
        self.sideGrips[1].setGeometry(
            inRect.left(), 0, inRect.width(), self.gripSize)
        # right edge
        self.sideGrips[2].setGeometry(
            inRect.left() + inRect.width(),
            inRect.top(), self.gripSize, inRect.height())
        # bottom edge
        self.sideGrips[3].setGeometry(
            self.gripSize, inRect.top() + inRect.height(),
            inRect.width(), self.gripSize)

        for grip in self.sideGrips + self.cornerGrips:
            grip.setStyleSheet("background-color: transparent;")
            grip.raise_()

    def showMaxRestore(self):

        if self.maxNormal:
            self.showNormal()
            self.maxNormal = False
            self.max_btn.setText(" ⃞ ")
            self.max_btn.setToolTip("Maximize")

        else:
            self.showMaximized()
            self.maxNormal = True
            self.max_btn.setText("⧉")
            self.max_btn.setToolTip("Restore")

    def resizeEvent(self, event):

        if self.custom_titlebar:
            # update grip areas
            self.updateGrips()

            # adjust to screen edges:
            mousePos = QCursor.pos()
            if -5 < mousePos.y() < 5 or self.screenSize.height() - 5 < mousePos.y() < self.screenSize.height() + 5:
                self.setGeometry(self.x(), 0, self.width(), self.screenSize.height())

        # update hover areas (doesn't matter if visible or not)
        self.hoverHWidget.setGeometry(self.action_size, 0, self.width(), 20)
        self.hoverVWidget.setGeometry(0, self.action_size, 20, self.height())

        if self.dl_manager.isVisible():
            # reposition download list
            x = self.x() + self.width() - self.dl_manager.width()
            y = self.y() + self.navtab.height()
            self.dl_manager.move(x, y)

        if self.search_widget.isVisible():
            # reposition search widget
            actRect = self.search_off_btn.geometry()
            actPos = self.mapToGlobal(self.search_off_btn.geometry().topLeft())
            x = actPos.x() + actRect.width() - self.search_widget.width()
            y = self.y() + self.navtab.height()
            self.search_widget.move(x, y)

    def keyReleaseEvent(self, a0):

        if a0.key() == Qt.Key.Key_Escape:
            if self.urlbar.hasFocus():
                text = self.tabs.currentWidget().url().toString()
                self.urlbar.setText(self.tabs.currentWidget().url().toString())
                self.urlbar.setCursorPosition(len(text))

            elif self.isFullScreen():
                if not self.prevAutoHide:
                    self.manage_autohide()
                self.showNormal()

        elif a0.key() == Qt.Key.Key_F:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.manage_search()

        elif a0.key() == Qt.Key.Key_T:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                if not self.isIncognito:
                    self.add_new_tab()

        elif a0.key() == Qt.Key.Key_N:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier:
                if not self.isIncognito:
                    self.show_in_new_window(incognito=True)
            elif a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                if not self.isIncognito:
                    self.show_in_new_window()

        elif a0.key() == Qt.Key.Key_W:
            if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.tab_closed(self.tabs.currentIndex())

        elif a0.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                if not self.prevAutoHide:
                    self.manage_autohide()
                self.showNormal()
            else:
                self.prevAutoHide = self.autoHide
                if not self.autoHide:
                    self.manage_autohide()
                self.showFullScreen()

        elif a0.key() == Qt.Key.Key_A:
            self.manage_autohide(force_show=True)

    def closeEvent(self, a0):

        # close all other widgets and processes
        self.dl_manager.cancelAllDownloads()
        self.dl_manager.close()
        self.search_widget.close()
        self.hoverHWidget.close()
        self.hoverVWidget.close()
        # these may not exist
        try:
            self.feature_dlg.close()
        except:
            pass
        try:
            self.clean_dlg.close()
        except:
            pass

        # Save current browser contents and settings
        if not self.isNewWin:
            # only main instance may save settings
            self.settings.setValue("General/cookies", self.cookies)
            self.settings.setValue("Appearance/custom_title", self.custom_titlebar)
            self.settings.setValue("Appearance/h_tabbar", self.h_tabbar)
            self.settings.setValue("Appearance/auto_hide", self.autoHide)
            self.settings.setValue("Appearance/icon_size", self.icon_size)
            self.settings.setValue("Appearance/border_radius", self.radius)
            self.settings.setValue("Window/pos", self.pos())
            self.settings.setValue("Window/size", self.size())

            # save open tabs
            tabs = []
            for i in range(self.tabs.count() - 1):
                browser = self.tabs.widget(i)
                tabs.append([browser.url().toString(), browser.page().zoomFactor(), i == self.tabs.currentIndex()])
            self.settings.setValue("Session/tabs",  tabs)

            # save other open windows
            # only open windows when main instance is closed will be remembered
            new_wins = []
            for w in self.instances:

                # won't keep any incognito data
                if not w.isIncognito:

                    # check if window is still open
                    if w.isVisible():

                        # saving open tabs for each instance
                        new_tabs = []
                        for i in range(w.tabs.count() - 1):
                            browser = w.tabs.widget(i)
                            new_tabs.append([browser.url().toString(), browser.page().zoomFactor(), i == w.tabs.currentIndex()])
                        new_wins.append(new_tabs)

                # closing all other open child windows
                w.close()

            self.settings.setValue("Session/new_wins", new_wins)

            # restart app to wipe all cache folders but the last one (not possible while running since it's locked)
            if self.deleteCache:
                QCoreApplication.quit()
                status = QProcess.startDetached(sys.executable, sys.argv + ["--delete_cache"] + [self.lastCache])


class SearchWidget(QWidget):

    _width = 300
    _height = 54

    def __init__(self, parent, searchCallback):
        super(SearchWidget, self).__init__(parent)

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)

        with open(resource_path("qss/search_widget.qss")) as f:
            self.setStyleSheet(f.read())
        self.setFixedSize(self._width, self._height)
        self.setContentsMargins(10, 0, 0, 0)

        self.searchCallback = searchCallback

        # create a horizontal layout
        self.mainLayout = QHBoxLayout()
        self.mainLayout.setContentsMargins(5, 5, 5, 5)
        self.mainLayout.setSpacing(10)
        self.setLayout(self.mainLayout)

        # text box to fill in target search
        self.search_box = QLineEdit()
        self.search_box.setFixedSize(self._width - 100, self._height - 30)
        self.search_box.returnPressed.connect(lambda checked=False, forward=True: self.searchCallback(checked, forward))
        self.mainLayout.addWidget(self.search_box)

        # adding a separator
        separator = QLabel()
        separator.setObjectName("sep")
        separator.setPixmap(QPixmap(resource_path("res/tabsep.png")))
        self.mainLayout.addWidget(separator)

        # search forward button
        self.search_forward = QPushButton("▼")
        font = self.search_forward.font()
        font.setPointSize(font.pointSize() + 10)
        self.search_forward.setFont(font)
        self.search_forward.clicked.connect(lambda checked, forward=True: self.searchCallback(checked, forward))
        self.mainLayout.addWidget(self.search_forward)

        # search backward button
        self.search_backward = QPushButton("▲")
        font = self.search_backward.font()
        font.setPointSize(font.pointSize() + 10)
        font.setPointSize(font.pointSize() + 10)
        self.search_backward.setFont(font)
        self.search_backward.clicked.connect(lambda checked, forward=False: self.searchCallback(checked, forward))
        self.mainLayout.addWidget(self.search_backward)

    def show(self):
        super().show()
        self.activateWindow()
        self.search_box.setFocus()

    def hide(self):
        super().hide()
        self.search_box.setText("")

    def getText(self):
        return self.search_box.text()


class DownloadManager(QWidget):

    _item_width = 356
    _item_height = 54

    def __init__(self, parent=None):
        super(DownloadManager, self).__init__(parent)

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        effect = QGraphicsDropShadowEffect()
        effect.setColor(QApplication.palette().color(QPalette.ColorRole.Shadow))
        effect.setBlurRadius(50)
        effect.setOffset(5)
        self.setGraphicsEffect(effect)

        self.setWindowTitle("Coward - Downloads")
        with open(resource_path("qss/download_manager.qss")) as f:
            self.setStyleSheet(f.read())
        self.mainLayout = QVBoxLayout()
        self.mainLayout.setContentsMargins(0, 0, 5, 5)
        self.mainLayout.setSpacing(10)
        self.setLayout(self.mainLayout)

        self.init_label = QLabel("No Donwloads active yet...")
        self.init_label.setContentsMargins(10, 0, 0, 0)
        self.init_label.setFixedSize(self._item_width, self._item_height)
        self.mainLayout.addWidget(self.init_label)

        self.downloads = {}

        self.pause_char = "||"
        self.cancel_char = "ℵ"
        self.resume_char = "⟳"
        self.folder_char = "🗀"

        # to avoid garbage, downloads will be stored in system Temp folder, then moved to selected location
        self.tempFolder = os.path.join(os.getenv("SystemDrive"), os.path.sep, "Windows", "Temp", "Coward")
        try:
            shutil.rmtree(self.tempFolder)
        except:
            pass

    def addDownload(self, item):

        accept = True
        added = False
        filename = ""
        tempfile = ""
        if item and item.state() == QWebEngineDownloadRequest.DownloadState.DownloadRequested:

            if item.isSavePageDownload():
                # download the whole page content (html file + folder)
                item.setSavePageFormat(QWebEngineDownloadRequest.SavePageFormat.CompleteHtmlSaveFormat)

            norm_name = get_valid_filename(item.downloadFileName())
            filename, _ = QFileDialog.getSaveFileName(self, "Save File As", QDir(item.downloadDirectory()).filePath(norm_name))
            if filename:
                filename = os.path.normpath(filename)
                tempfile = os.path.join(self.tempFolder, str(item.id()), os.path.basename(filename))
                item.setDownloadDirectory(os.path.dirname(tempfile))
                item.setDownloadFileName(os.path.basename(filename))
                item.receivedBytesChanged.connect(lambda i=item.id(): self.updateDownload(i))
                item.isFinishedChanged.connect(lambda i=item.id(): self.downloadFinished(i))
                item.stateChanged.connect(lambda s, i=item.id(): self.onStateChanged(s, i))
                added = True

            else:
                accept = False

        if accept:
            item.accept()
            if added:
                # request is triggered several times. Only the first time will be added to the UI
                self._add(item, os.path.basename(filename), filename, tempfile)

        else:
            item.cancel()
            del item

        return accept

    def _add(self, item, title, location, tempfile):

        self.init_label.hide()

        widget = QWidget()
        widget.setObjectName("dl_item")
        widget.setFixedSize(self._item_width, self._item_height)
        layout = QGridLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        name = QLabel()
        name.setObjectName("name")
        name.setText(title)
        name.setToolTip(location)
        layout.addWidget(name, 0, 0)

        prog = QProgressBar()
        prog.setObjectName("prog")
        prog.setTextVisible(False)
        prog.setFixedHeight(10)
        prog.setMinimum(0)
        prog.setMaximum(100)
        layout.addWidget(prog, 1, 0)

        pause = QPushButton()
        pause.setObjectName("pause")
        pause.setText(self.pause_char)
        pause.setToolTip("Pause download")
        pause.clicked.connect(lambda checked, b=pause, i=item, l=location: self.pause(checked, b, i, l))
        layout.addWidget(pause, 0, 1)

        close_loc = QPushButton()
        close_loc.setText(self.cancel_char)
        close_loc.setObjectName("close_loc")
        close_loc.setToolTip("Cancel download")
        close_loc.clicked.connect(lambda checked, b=close_loc, i=item, l=location: self.close_loc(checked, b, i, l))
        layout.addWidget(close_loc, 0, 2)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 0)

        widget.setLayout(layout)
        self.mainLayout.insertWidget(0, widget)
        self.downloads[str(item.id())] = [item, title, location, tempfile, widget]

    def updateDownload(self, dl_id):

        dl_data = self.downloads.get(str(dl_id), [])
        if dl_data:
            item, _, _, _, widget = dl_data

            prog = widget.findChild(QProgressBar, "prog")
            value = int(item.receivedBytes() / (item.totalBytes() or 1) * 100)
            prog.setValue(value)

    def downloadFinished(self, dl_id):

        dl_data = self.downloads.get(str(dl_id), [])
        if dl_data:
            item, _, location, tempfile, widget = dl_data

            pause = widget.findChild(QPushButton, "pause")
            pause.hide()
            close_loc = widget.findChild(QPushButton, "close_loc")
            close_loc.setText(self.folder_char)
            close_loc.setToolTip("Open file location")
            prog = widget.findChild(QProgressBar, "prog")
            prog.hide()
            if item.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                try:
                    shutil.move(tempfile, location)
                    if item.isSavePageDownload():
                        shutil.move(tempfile.rsplit(".", 1)[0] + "_files", os.path.dirname(location))
                except:
                    pass

    def onStateChanged(self, state, dl_id):

        dl_data = self.downloads.get(str(dl_id), [])
        if dl_data:
            item, _, location, tempfile, widget = dl_data

            if state not in (QWebEngineDownloadRequest.DownloadState.DownloadInProgress,
                             QWebEngineDownloadRequest.DownloadState.DownloadCompleted):
                name = widget.findChild(QLabel, "name")
                font = name.font()
                font.setStrikeOut(True)
                name.setFont(font)
                prog = widget.findChild(QProgressBar, "prog")
                prog.hide()
                pause = widget.findChild(QPushButton, "pause")
                pause.hide()
                close_loc = widget.findChild(QPushButton, "close_loc")
                close_loc.hide()

    def pause(self, checked, button, item, location):

        if button.text() == self.pause_char:
            try:
                item.pause()
            except:
                pass
            button.setText(self.resume_char)

        elif button.text() == self.resume_char:
            dl_data = self.downloads.get(str(item.id()), [])
            if dl_data:
                _, _, _, _, widget = dl_data

                item.resume()
                button.setText(self.pause_char)
                name = widget.findChild(QLabel, "name")
                font = name.font()
                font.setStrikeOut(False)
                name.setFont(font)
                prog = widget.findChild(QProgressBar, "prog")
                prog.show()
                close_loc = widget.findChild(QPushButton, "close_loc")
                close_loc.setText(self.cancel_char)

    def close_loc(self, checked, button, item, location):

        if button.text() == self.folder_char:
            if os.path.isfile(location):
                subprocess.Popen(r'explorer /select, "%s"' % location)
            else:
                button.hide()
                dl_data = self.downloads.get(str(item.id()), [])
                if dl_data:
                    _, _, _, _, widget = dl_data

                    name = widget.findChild(QLabel, "name")
                    font = name.font()
                    font.setStrikeOut(True)
                    name.setFont(font)

        elif button.text() == self.cancel_char:
            try:
                item.cancel()
            except:
                pass
            dl_data = self.downloads.get(str(item.id()), [])
            if dl_data:
                _, _, _, tempfile, widget = dl_data

                name = widget.findChild(QLabel, "name")
                font = name.font()
                font.setStrikeOut(True)
                name.setFont(font)
                prog = widget.findChild(QProgressBar, "prog")
                prog.hide()
                pause = widget.findChild(QPushButton, "pause")
                pause.hide()
                close_loc = widget.findChild(QPushButton, "close_loc")
                close_loc.hide()

    def cancelAllDownloads(self):
        for dl_id in self.downloads.keys():
            item, _, location, tempfile, _ = self.downloads[dl_id]
            try:
                item.cancel()
            except:
                pass
        try:
            shutil.rmtree(self.tempFolder)
        except:
            pass


class WebEnginePage(QWebEnginePage):

    def __init__(self, profile, parent, mediaErrorSignal=None):
        super(WebEnginePage, self).__init__(profile, parent)

        self.playerProcess = None
        self.mediaError = mediaErrorSignal

    def javaScriptConsoleMessage(self, level, message="", lineNumber=0, sourceID=""):

        if level == WebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            # this is totally empirical and based in just one use case... can it be more "scientific"?
            if "Player" in message and "ErrorNotSupported" in message:
                self.mediaError.emit(self)

    def _kill_process(self, proc_pid):
        # Thanks to Jovik: https://stackoverflow.com/questions/4789837/how-to-terminate-a-python-subprocess-launched-with-shell-true
        process = psutil.Process(proc_pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()

    def openInExternalPlayer(self):
        # Thanks to pullmyteeth: https://stackoverflow.com/questions/404744/determining-application-path-in-a-python-exe-generated-by-pyinstaller
        if is_packaged():
            app_location = os.path.dirname(sys.executable)
        else:
            app_location = os.path.join(os.path.dirname(sys.modules["__main__"].__file__), 'dist')
        s_path = os.path.join(app_location, 'externalplayer', 'streamlink', 'bin', 'streamlink.exe')
        p_path = os.path.join(app_location, 'externalplayer', 'mpv', 'mpv.exe')

        if os.path.exists(s_path) and os.path.exists(p_path):
            cmd = s_path + ' --player ' + p_path + ' %s 720p,480p,best' % self.url().toString()
            if self.playerProcess is not None and self.playerProcess.poll() is None:
                self._kill_process(self.playerProcess.pid)
            self.playerProcess = subprocess.Popen(cmd, shell=True)
        # ISSUE: how to pack it all? within pyinstaller (is it allowed by authors)? Downloaded by user?
        # Solution: use streamlink python module, but don't know how to run it and launch MPV player
        # session = Streamlink()
        # session.set_option("player", p_path)
        # plugin_name, plugin_class, resolved_url = session.resolve_url(self.url().toString())
        # plugin = plugin_class(session, resolved_url, options={"plugin-option": 123})
        # streams = plugin.streams()
        # # fd = streams["best"].open()

    def closeEvent(self, event):
        if self.playerProcess is not None and self.playerProcess.poll() is None:
            self._kill_process(self.playerProcess.pid)


class LineEdit(QLineEdit):

    def __init__(self, parent=None):
        super(LineEdit, self).__init__(parent)

    def focusInEvent(self, event):
        # this delay is needed to avoid other mouse events to interfere with selectAll() command
        super(LineEdit, self).focusInEvent(event)
        QTimer.singleShot(200, self.selectAll)


class Dialog(QDialog):

    def __init__(self, parent, title="", message="", buttons=None, pos_offset=None, radius=0):
        super().__init__(parent)

        self.pos_offset = QPoint(pos_offset.x(), pos_offset.y() - radius * 2) if pos_offset is not None else None
        self.radius = radius

        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(resource_path("res/coward.png")))

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint | Qt.WindowType.FramelessWindowHint)

        with open(resource_path("qss/dialog.qss")) as f:
            self.setStyleSheet(f.read())

        self.setContentsMargins(0, 0, 0, 0)

        self.widget = QWidget(self)
        self.widget.setContentsMargins(30, 30, 30, 10)

        self.init_message = message
        self.message = QLabel(message or "Lorem ipsum consectetuer adipisci est")

        self.buttonBox = QDialogButtonBox(buttons or (QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel))
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.setContentsMargins(0, 20, 0, 0)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 5, 5)
        layout.setSpacing(0)
        layout.addWidget(self.message)
        layout.addWidget(self.buttonBox)
        self.widget.setLayout(layout)

        self.mainLayout = QHBoxLayout()
        self.mainLayout.addWidget(self.widget)
        self.setLayout(self.mainLayout)

    def move(self, position, y=None):
        if y is not None:
            position = QPoint(position, y)
        super().move(QPoint(position.x(), position.y() - self.radius - 4))

    def setMessage(self, new_message):
        self.message.setText(new_message)

    def getInitMessage(self):
        return self.init_message

    def getCurrentMessage(self):
        return self.message.text()


class HoverWidget(QWidget):

    def __init__(self, parent, obj_to_show, enter_signal=None, leave_signal=None):
        super(HoverWidget, self).__init__(parent)

        self.obj_to_show = obj_to_show
        self.enter_signal = enter_signal
        self.leave_signal = leave_signal

        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodTransparent)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)

    def enterEvent(self, a0):
        if self.enter_signal is not None:
            self.enter_signal.emit()

    def leaveEvent(self, a0):
        if self.leave_signal is not None:
            self.leave_signal.emit()


class TitleBar(QToolBar):

    def __init__(self, parent, isCustom, other_widgets_to_move=None, enter_signal=None, leave_signal=None):
        super(TitleBar, self).__init__(parent)

        self.isCustom = isCustom
        self.other_move = other_widgets_to_move or []
        self.enter_signal = enter_signal
        self.leave_signal = leave_signal

        self.setMouseTracking(True)
        self.moving = False
        self.offset = parent.pos()
        self.other_offsets = []

        if isCustom:
            self.parent().setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            self.setAutoFillBackground(True)
            self.setBackgroundRole(QPalette.ColorRole.Highlight)

    def setOtherWidgetsToMove(self, other_widgets_to_move):
        self.other_move = other_widgets_to_move

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isCustom:
            self.moving = True
            self.offset = event.pos()
            self.other_offsets = []
            for w in self.other_move:
                self.other_offsets.append([w, w.pos() - self.parent().pos()])

    def mouseMoveEvent(self, event):
        if self.moving:
            # in PyQt6 globalPos() has been replaced by globalPosition(), which returns a QPointF() object
            self.parent().move(event.globalPosition().toPoint() - self.offset)
            for item in self.other_offsets:
                w, offset = item
                w.move(event.globalPosition().toPoint() - self.offset + offset)

    def mouseReleaseEvent(self, event):
        self.moving = False

    def enterEvent(self, event):
        if self.enter_signal is not None:
            self.enter_signal.emit()

    def leaveEvent(self, event):
        if self.leave_signal is not None:
            self.leave_signal.emit()


class TabBar(QTabBar):

    def __init__(self, parent, enter_signal=None, leave_signal=None):
        super(TabBar, self).__init__(parent)

        self.enter_signal = enter_signal
        self.leave_signal = leave_signal

    # this will align tab titles to left (maybe a "little bit" excessive, but fun...)
    # WARNING: moving tabs produces weird behavior
    # def paintEvent(self, event):
    #     # thanks to Oleg Palamarchuk: https://stackoverflow.com/questions/77257766/left-alignment-of-tab-names
    #     painter = QStylePainter(self)
    #     opt = QStyleOptionTab()
    #
    #     for i in range(self.count()):
    #         self.initStyleOption(opt, i)
    #
    #         painter.drawControl(QStyle.ControlElement.CE_TabBarTabShape, opt)
    #         painter.save()
    #
    #         r = self.tabRect(i)
    #         opt.rect = r
    #
    #         textGap = 8
    #         if i < self.count() - 1:
    #             painter.drawImage(QRect(r.x() + 8, r.y() + ((r.height() - 32) // 2), self.icon_size, self.icon_size), QImage(opt.icon.pixmap(QSize(self.icon_size, self.icon_size))))
    #             textGap = self.action_size
    #
    #         if self.parent().tabPosition() == QTabWidget.TabPosition.North or i == self.count() - 1:
    #             painter.drawText(QRect(r.x() + textGap, r.y(), r.width(), r.height()), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, opt.text)
    #
    #         painter.restore()

    def enterEvent(self, event):
        if self.enter_signal is not None:
            self.enter_signal.emit()

    def leaveEvent(self, event):
        if self.leave_signal is not None:
            self.leave_signal.emit()


class SideGrip(QWidget):
    # thanks to musicamante. Just impressive...
    # https://stackoverflow.com/questions/62807295/how-to-resize-a-window-from-the-edges-after-adding-the-property-qtcore-qt-framel

    def __init__(self, parent, edge):
        QWidget.__init__(self, parent)
        if edge == Qt.Edge.LeftEdge:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            self.resizeFunc = self.resizeLeft
        elif edge == Qt.Edge.TopEdge:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
            self.resizeFunc = self.resizeTop
        elif edge == Qt.Edge.RightEdge:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            self.resizeFunc = self.resizeRight
        else:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
            self.resizeFunc = self.resizeBottom
        self.mousePos = None

    def resizeLeft(self, delta):
        window = self.window()
        width = max(window.minimumWidth(), window.width() - delta.x())
        geo = window.geometry()
        geo.setLeft(geo.right() - width)
        window.setGeometry(geo)

    def resizeTop(self, delta):
        window = self.window()
        height = max(window.minimumHeight(), window.height() - delta.y())
        geo = window.geometry()
        geo.setTop(geo.bottom() - height)
        window.setGeometry(geo)

    def resizeRight(self, delta):
        window = self.window()
        width = max(window.minimumWidth(), window.width() + delta.x())
        window.resize(width, window.height())

    def resizeBottom(self, delta):
        window = self.window()
        height = max(window.minimumHeight(), window.height() + delta.y())
        window.resize(window.width(), height)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mousePos = event.pos()

    def mouseMoveEvent(self, event):
        if self.mousePos is not None:
            delta = event.pos() - self.mousePos
            self.resizeFunc(delta)

    def mouseReleaseEvent(self, event):
        self.mousePos = None


def is_packaged():
    return getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")


def app_location():
    if is_packaged():
        location = os.path.dirname(sys.executable)
    else:
        location = os.path.dirname(sys.modules["__main__"].__file__)
    return location


def resource_path(relative_path, inverted=False):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    ret = os.path.normpath(os.path.join(base_path, relative_path))
    if inverted:
        ret = ret.replace("\\", "/")
    return ret


def get_valid_filename(name):
    s = str(name).strip().replace(" ", "_")
    s = re.sub(r"(?u)[^-\w.]", "", s)
    if s in {"", ".", ".."}:
        return ""
    return s


def setDPIAwareness():
    if sys.platform == "win32":
        import ctypes
        try:
            dpiAware = ctypes.windll.user32.GetAwarenessFromDpiAwarenessContext(ctypes.windll.user32.GetThreadDpiAwarenessContext())
        except AttributeError:  # Windows server does not implement GetAwarenessFromDpiAwarenessContext
            dpiAware = 0

        if dpiAware == 0:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)


def setSystemDPISettings():
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_SCALE_FACTOR"] = "1"


def setApplicationDPISettings():
    # These attributes are always enabled in PyQt6
    if hasattr(QStyleFactory, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(QStyleFactory, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)


def force_icon(appid):
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)


def exception_hook(exctype, value, tb):
    # https://stackoverflow.com/questions/56991627/how-does-the-sys-excepthook-function-work-with-pyqt5
    traceback_formated = traceback.format_exception(exctype, value, tb)
    traceback_string = "".join(traceback_formated)
    print(traceback_string, file=sys.stderr)
    sys.exit(1)


# Qt is DPI-Aware, so all this is not likely required
# setDPIAwareness()
# setSystemDPISettings()
# setApplicationDPISettings()

# to play some media which uses non-built-in codecs, QtWebEngine must be built with option -webengine-proprietary-codecs
# https://doc.qt.io/qt-6/qtwebengine-features.html#audio-and-video-codecs
# in addition to that, for some sites using widevine (DRM protection), this variable must also be set before creating app:
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = '--widevine-path="%s"' % os.path.join(app_location(), "externalplayer", "widevine", "widevinecdm.dll")

# creating a PyQt5 application and (windows only) force dark mode
app = QApplication(sys.argv + ['-platform', 'windows:darkmode=1'])

# setting name to the application
app.setApplicationName("Coward")
app.setWindowIcon(QIcon(resource_path("res/coward.png")))

if not is_packaged():
    # change application icon even when running as Python script
    force_icon('kalmat.coward.nav.01')

    # This will allow to show some tracebacks (not all, anyway)
    sys._excepthook = sys.excepthook
    sys.excepthook = exception_hook

# creating and showing MainWindow object
window = MainWindow()
window.show()

# loop
app.exec()
