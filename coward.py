# based on: https://www.geeksforgeeks.org/python/creating-a-tabbed-browser-using-pyqt5/
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWebEngineCore import *
from PyQt6.QtWebEngineWidgets import *
from PyQt6.QtWidgets import *

# Using a local copy of this code since it is not in PyPi
# The library available in PyPi, which is a fork from this one, unfortunately supports PyQt5 only
# Thanks to z3ntu for sharing (https://github.com/z3ntu/QtWaitingSpinner)
from _waitingspinnerwidget import QtWaitingSpinner


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

    # constructor
    def __init__(self, parent=None, new_win=False, init_tabs=None):
        super(MainWindow, self).__init__(parent)

        # prepare cache folders and variables
        self.cachePath = ""
        self.lastCache = ""
        self.storageName = "coward_" + str(qWebEngineChromiumVersion()) + ("_debug" if "python" in sys.executable else "")
        self.deleteCache = False

        # wipe all cache folders except the last one if requested by user
        if "--delete_cache" in sys.argv:
            lastCache = sys.argv[-1]
            cacheName = os.path.basename(lastCache)
            cacheFolder = os.path.dirname(lastCache)
            parentFolder = os.path.dirname(cacheFolder)
            tempCache = os.path.join(parentFolder, cacheName)
            shutil.move(lastCache, tempCache)
            shutil.rmtree(cacheFolder)
            os.rename(tempCache, os.path.join(parentFolder, self.storageName))
            sys.exit(0)

        self.isNewWin = new_win
        self.homePage = 'https://start.duckduckgo.com/?kae=d'
        if self.isNewWin and not init_tabs:
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
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Icons
        # as images
        self.web_ico = QIcon(resource_path("res/web.png"))
        # as path for qss files (path separator inverted: "/")
        self.tabsep_ico_inv = resource_path("res/tabsep.png", True)

        # tab bar styles
        with open(resource_path("qss/h_tabs.qss"), "r") as f:
            self.h_tab_style = f.read()
            self.h_tab_style = self.h_tab_style % self.tabsep_ico_inv

        with open(resource_path("qss/v_tabs.qss"), "r") as f:
            self.v_tab_style = f.read()

        # Set tracking mouse ON if needed
        # self.setMouseTracking(True)

        # get or create settings
        self.screenSize = self.screen().availableGeometry()
        try:
            # open settings file
            with open("coward.json", "r") as f:
                self.config = json.loads(f.read())

            # check settings structure
            _ = self.config["tabs"]
            _ = self.config["pos"]
            _ = self.config["size"]
            _ = self.config["cookies"]
            _ = self.config["h_tabbar"]
            _ = self.config["custom_title"]
            _ = self.config["auto_hide"]
            _ = self.config["new_wins"]

        except:
            # create a default settings file in case of error
            self.config = {"tabs": [[self.homePage, 1.0, True]],
                           "pos": (100, 100),
                           "size": (min(self.screenSize.width() // 2, 1024), min(self.screenSize.height() - 200, 1024)),
                           "cookies": True,
                           "h_tabbar": False,
                           "custom_title": True,
                           "auto_hide": False,
                           "new_wins": []
                           }

        # custom / standard title bar
        self.custom_titlebar = self.config["custom_title"]
        self.autoHide = self.config["auto_hide"]

        # set initial position and size
        x, y = self.config["pos"]
        w, h = self.config["size"]
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

        # Enable/Disable cookies
        self.cookies = self.config["cookies"]

        # This is needed to keep cookies and cache (PyQt6 only, not in PyQt5)
        # Not sure if profile can be unique or new for every tab
        # Not sure either if profile must have a browser as parent or it is enough using 'self'
        # Will try to keep session cookies only... we will see!
        self.pageProfile = QWebEngineProfile(self.storageName, self)
        # self.pageProfile.setCachePath(self.cachePath)
        # self.pageProfile.setPersistentStoragePath(self.cachePath)
        # self.pageProfile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        # TODO: check if allow is enough or must use force
        self.pageProfile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        self.pageProfile.setPersistentPermissionsPolicy(QWebEngineProfile.PersistentPermissionsPolicy.StoreOnDisk)
        self.pageProfile.defaultProfile().cookieStore().setCookieFilter(self.cookie_filter)

        # vertical / horizontal tabbar
        self.h_tabbar = self.config["h_tabbar"]

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
        self.navtb = TitleBar(self, self.custom_titlebar, [self.dl_manager, self.search_widget], None, self.leaveNavBarSig)
        with open(resource_path("qss/titlebar.qss")) as f:
            navStyle = f.read()
        self.navtb.setStyleSheet(navStyle)

        self.navtb.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.navtb.setMovable(False)
        self.navtb.setFloatable(False)
        self.navtb.setFloatable(False)
        self.addToolBar(self.navtb)

        # adding toggle vertical / horizontal tabbar button
        self.toggleTab_btn = QAction("", self)
        font = self.toggleTab_btn.font()
        font.setPointSize(font.pointSize() + 2)
        self.toggleTab_btn.setFont(font)
        self.toggleTab_btn.triggered.connect(lambda: self.toggle_tabbar(toggle=True))
        self.navtb.addAction(self.toggleTab_btn)

        # creating back action
        self.back_btn = QAction("🡠", self)
        font = self.back_btn.font()
        font.setPointSize(font.pointSize() + 8)
        self.back_btn.setFont(font)
        self.back_btn.setDisabled(True)
        self.back_btn.setToolTip("Back to previous page")
        self.back_btn.triggered.connect(lambda: self.tabs.currentWidget().back())
        self.navtb.addAction(self.back_btn)

        # adding next button
        self.next_btn = QAction("🡢", self)
        font = self.next_btn.font()
        font.setPointSize(font.pointSize() + 8)
        self.next_btn.setFont(font)
        self.next_btn.setDisabled(True)
        self.next_btn.setToolTip("Forward to next page")
        self.next_btn.triggered.connect(lambda: self.tabs.currentWidget().forward())
        self.navtb.addAction(self.next_btn)

        # adding reload button
        self.reload_btn = QAction("⟳", self)
        font = self.reload_btn.font()
        font.setPointSize(font.pointSize() + 14)
        self.reload_btn.setFont(font)
        self.reload_btn.setToolTip("Reload page")
        self.reload_btn.triggered.connect(lambda: self.tabs.currentWidget().reload())
        self.navtb.addAction(self.reload_btn)

        # creating home action
        # self.home_btn = QAction("⌂", self)
        # font = self.home_btn.font()
        # font.setPointSize(font.pointSize() + 16)
        # self.home_btn.setFont(font)
        # self.home_btn.setToolTip("Home page")
        # self.home_btn.triggered.connect(self.navigate_home)
        # self.navtb.addAction(self.home_btn)

        # adding a separator
        # self.navtb.addSeparator()

        spacer = QLabel()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        spacer.setMinimumWidth(20)
        spacer.setMaximumWidth(200)
        self.navtb.addWidget(spacer)

        # creating a line edit widget for URL
        self.urlbar = LineEdit()
        self.urlbar.setTextMargins(10, 0, 0, 0)
        self.urlbar.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.urlbar.returnPressed.connect(self.navigate_to_url)
        self.navtb.addWidget(self.urlbar)

        # similarly adding stop action
        # self.stop_btn = QAction("⤫", self)
        # font = self.stop_btn.font()
        # font.setPointSize(font.pointSize() + 8)
        # self.stop_btn.setFont(font)
        # self.stop_btn.setToolTip("Stop loading current page")
        # self.stop_btn.triggered.connect(lambda: self.tabs.currentWidget().stop())
        # self.navtb.addAction(self.stop_btn)
        # self.navtb.addAction(self.stop_btn)

        self.spinContainer = QWidget()
        self.spinContainer.setFixedSize(48, 48)
        self.spinner = QtWaitingSpinner(self.spinContainer)
        self.spinner.setInnerRadius(5)
        self.spinner.setColor(QColor(128, 128, 128))
        self.navtb.addWidget(self.spinContainer)

        spacer = QLabel()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        spacer.setMinimumWidth(0)
        spacer.setMaximumWidth(200 - self.spinContainer.width())
        self.navtb.addWidget(spacer)

        # adding search option
        self.search_btn = QAction("⌕", self)
        font = self.search_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.search_btn.setFont(font)
        self.search_btn.setToolTip("Search text in this page")
        self.search_btn.triggered.connect(self.manage_search)
        self.navtb.addAction(self.search_btn)

        # adding auto-hide mgt.
        self.auto_btn = QAction("⇱" if self.autoHide else "⇲", self)
        font = self.auto_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.auto_btn.setFont(font)
        self.auto_btn.setToolTip("Auto-hide is now " + ("Enabled" if self.autoHide else "Disabled"))
        self.auto_btn.triggered.connect(self.manage_autohide)
        self.navtb.addAction(self.auto_btn)

        # adding downloads mgt.
        self.dl_btn = QAction("🡣", self)
        font = self.dl_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.dl_btn.setFont(font)
        self.dl_btn.setToolTip("Show / hide downloads")
        self.dl_btn.triggered.connect(self.manage_downloads)
        self.navtb.addAction(self.dl_btn)

        # adding cookie mgt.
        self.cookie_btn = QAction("", self)
        font = self.cookie_btn.font()
        font.setPointSize(font.pointSize() + 4)
        self.cookie_btn.setFont(font)
        self.manage_cookies(clicked=False)
        self.cookie_btn.triggered.connect(lambda: self.manage_cookies(clicked=True))
        self.navtb.addAction(self.cookie_btn)

        # adding cleaning mgt.
        self.clean_btn = QAction("🧹", self)
        font = self.clean_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.clean_btn.setFont(font)
        self.clean_btn.setToolTip("Erase history and cookies")
        self.clean_btn.triggered.connect(lambda: self.clean_dlg.exec())
        self.navtb.addAction(self.clean_btn)

        if self.custom_titlebar:

            self.navtb.addSeparator()

            self.min_btn = QAction("―", self)
            self.min_btn.setToolTip("Minimize")
            font = self.min_btn.font()
            font.setPointSize(font.pointSize() + 2)
            self.min_btn.setFont(font)
            self.min_btn.triggered.connect(self.showMinimized)
            self.navtb.addAction(self.min_btn)

            self.max_btn = QAction(" ⃞ ", self)
            self.max_btn.setToolTip("Maximize")
            font = self.max_btn.font()
            font.setPointSize(font.pointSize() + 4)
            self.max_btn.setFont(font)
            self.max_btn.triggered.connect(self.showMaxRestore)
            self.navtb.addAction(self.max_btn)

            self.closewin_btn = QAction("🕱", self)
            self.closewin_btn.setToolTip("Quit, coward")
            font = self.closewin_btn.font()
            font.setPointSize(font.pointSize() + 8)
            self.closewin_btn.setFont(font)
            self.closewin_btn.triggered.connect(self.close)
            self.navtb.addAction(self.closewin_btn)

        # creating a tab widget
        self.tabs = QTabWidget(self)
        self.tabBar = TabBar(self.tabs, None, self.leaveTabBarSig)
        self.tabs.setTabBar(self.tabBar)
        self.tabs.setStyleSheet(self.h_tab_style if self.h_tabbar else self.v_tab_style)
        self.tabs.setMovable(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North if self.h_tabbar else QTabWidget.TabPosition.West)
        self.tabs.tabBar().setContentsMargins(0, 0, 0, 0)
        self.tabs.tabBar().setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.tabs.tabBar().setIconSize(QSize(32, 32))
        self.tabs.tabBar().tabMoved.connect(self.tab_moved)

        # creating a context menu to allow closing tabs when close button is hidden
        self.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.showContextMenu)
        self.tabsContextMenu = QMenu()
        self.tabsContextMenu.setMinimumHeight(54)
        self.tabsContextMenu.setContentsMargins(0, 5, 0, 0)
        self.close_action = QAction()
        self.close_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical))
        self.tabsContextMenu.addAction(self.close_action)

        # creating a context menu to allow closing tabs when close button is hidden
        self.newTabContextMenu = QMenu()
        self.newTabContextMenu.setMinimumHeight(54)
        self.newTabContextMenu.setContentsMargins(0, 5, 0, 0)
        self.newWindow_action = QAction()
        self.newWindow_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton))
        self.newWindow_action.setText("Open new tab in separate window")
        self.newWindow_action.triggered.connect(self.show_in_new_window)
        self.newTabContextMenu.addAction(self.newWindow_action)

        # set tabbar configuration according to orientation
        self.toggle_tabbar(toggle=False)

        # making document mode true
        self.tabs.setDocumentMode(True)

        # adding action when tab is changed
        self.tabs.currentChanged.connect(self.current_tab_changed)

        # adding action when tab is clicked
        self.tabs.tabBarClicked.connect(self.tab_clicked)

        # adding action when tab close is requested
        self.tabs.tabCloseRequested.connect(self.close_current_tab)

        # making tabs as central widget
        self.tabs.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCentralWidget(self.tabs)

        # open all windows and their tabs
        if self.isNewWin:
            # get open tabs for child window instance
            tabs = self.init_tabs

            # no child windows allowed for child instances
            new_wins = []

        else:
            # get open tabs for  main instance window
            tabs = self.config["tabs"]

            # get child windows instances and their open tabs
            new_wins = self.config["new_wins"]

        # open all tabs in main / child window
        self.spinner.start()
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
        self.cachePath = self.tabs.currentWidget().page().profile().persistentStoragePath()

        self.update_urlbar(self.tabs.currentWidget().url(), self.tabs.currentWidget())
        # this will load the active tab only, saving time at start
        # self.tabs.currentWidget().reload()

        # open child window instances passing their open tabs
        self.instances = []
        for new_tabs in new_wins:
            self.show_in_new_window(new_tabs)

        # adding add tab action
        self.add_tab_action()

        # class variables
        self.maxNormal = self.isMaximized()

        # creating a statusbar
        # self.status = QStatusBar(self)
        # self.dl_progress = QProgressBar()
        # self.dl_progress.setMinimum(0)
        # self.dl_progress.setMaximum(100)
        # self.status.addPermanentWidget(self.dl_progress)
        # self.dl_stop = QPushButton()
        # self.dl_stop.setStyleSheet(open(resource_path("qss/small_button.qss")).read())
        # self.dl_stop.setIcon(QIcon(self.close_ico))
        # self.dl_stop.setText("Cancel Download")
        # self.dl_stop.clicked.connect(self.stop_download)
        # self.status.addPermanentWidget(self.dl_stop)
        # self.setStatusBar(self.status)
        # self.statusBar().setVisible(False)

        # Prepare clean all warning dialog
        self.clean_dlg = Dialog(self, message="This will erase all your history and stored cookies.\n\n"
                                              "Are you sure you want to proceed?\n")
        self.clean_dlg.accepted.connect(self.clean_all)
        self.clean_dlg.rejected.connect(self.clean_dlg.close)

        # set hover areas for auto-hide mode
        # auto-hide navigation bar
        self.hoverHWidget = HoverWidget(self, self.navtb, self.enterHHoverSig)
        self.navtb.setFixedHeight(52)
        self.hoverHWidget.setGeometry(48, 0, self.width(), 20)
        self.hoverHWidget.hide()
        # auto-hide tab bar
        self.hoverVWidget = HoverWidget(self, self.tabs.tabBar(), self.enterVHoverSig)
        self.hoverVWidget.setGeometry(0, 48, 20, self.height())
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

    @pyqtSlot()
    def enterHHover(self):
        if self.autoHide:
            self.hoverHWidget.hide()
            self.navtb.show()
            if self.h_tabbar:
                self.tabs.tabBar().show()

    @pyqtSlot()
    def leaveHHover(self):
        pass

    @pyqtSlot()
    def enterVHover(self):
        if self.autoHide:
            self.hoverVWidget.hide()
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
                    self.navtb.hide()
                    self.tabs.tabBar().hide()
                    self.hoverHWidget.show()
            else:
                self.navtb.hide()
                self.hoverHWidget.show()

    @pyqtSlot()
    def enterTabBar(self):
        pass

    @pyqtSlot()
    def leaveTabBar(self):
        if self.autoHide:
            if self.h_tabbar:
                if not self.navtb.rect().contains(self.mapFromGlobal(QCursor.pos())):
                    self.navtb.hide()
                    self.tabs.tabBar().hide()
                    self.hoverHWidget.show()
            else:
                self.tabs.tabBar().hide()
                self.hoverVWidget.show()

    def show(self):
        super().show()
        if self.autoHide:
            self.navtb.hide()
            self.hoverHWidget.setGeometry(48, 0, self.width(), 20)
            self.hoverHWidget.show()
            self.tabs.tabBar().hide()
            self.hoverVWidget.setGeometry(0, 48, 20, self.height())
            if not self.h_tabbar:
                self.hoverVWidget.show()

    # method for adding new tab
    def add_tab(self, qurl=None, zoom=1.0, label="Loading..."):

        # if url is blank
        if qurl is None:
            # creating a google url
            qurl = QUrl(self.homePage)

        # creating a QWebEngineView object
        browser = QWebEngineView(self.pageProfile)
        page = browser.page()

        # Enabling fullscreen in YouTube and other sites
        browser.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        page.fullScreenRequested.connect(self.fullscr)

        # Enabling some extra features
        # page.featurePermissionRequested.connect(lambda u, f, p=page, b=browser: p.setFeaturePermission(u, f, QWebEnginePage.PermissionGrantedByUser))
        page.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
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

    def add_tab_action(self):

        self.addtab_btn = QLabel()
        i = self.tabs.addTab(self.addtab_btn, " ✚ ")
        self.tabs.tabBar().setTabButton(i, QTabBar.ButtonPosition.RightSide, None)
        self.tabs.widget(i).setDisabled(True)
        self.tabs.tabBar().setTabToolTip(i, "New tab")

    def add_new_tab(self, qurl=None):

        self.tabs.removeTab(self.tabs.count() - 1)
        self.tabs.setCurrentIndex(self.add_tab(qurl))
        self.add_tab_action()

    def show_in_new_window(self, tabs=None):

        if not self.isNewWin:
            w = MainWindow(new_win=True, init_tabs=tabs)
            self.instances.append(w)
            w.show()

    def toggle_tabbar(self, toggle=True):

        if toggle:
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
                    new_icon = QIcon(icon.pixmap(QSize(32, 32)).transformed(QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation))
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
                self.tabs.tabBar().show()
            if hasattr(self, "hoverHWidget"):
                self.hoverHWidget.show()
            if hasattr(self, "hoverVWidget"):
                if self.h_tabbar:
                    self.hoverVWidget.hide()
                else:
                    self.hoverVWidget.show()

    def cookie_filter(self, cookie, origin=None):
        # print(f"firstPartyUrl: {cookie.firstPartyUrl.toString()}, "
        # f"origin: {cookie.origin.toString()}, "
        # f"thirdParty? {cookie.thirdParty}"
        # )
        return self.cookies

    def onLoadStarted(self, browser, index):
        self.tabs.setTabIcon(index, self.web_ico)
        if browser == self.tabs.currentWidget():
            if not self.spinner.isSpinning:
                self.spinner.start()

    def onLoadFinished(self, a0, browser, index):
        if browser == self.tabs.currentWidget():
            if self.spinner.isSpinning:
                self.spinner.stop()

    def title_changed(self, title, i):
        self.tabs.tabBar().setTabText(i, (("  " + title[:20]) if len(title) > 20 else title) if self.h_tabbar else "")
        self.tabs.setTabToolTip(i, title + ("" if self.h_tabbar else "\n(Right-click to close)"))

    def icon_changed(self, icon: QIcon, i):

        if self.h_tabbar:
            new_icon = icon
        else:
            # icon rotation is required if not using custom painter in TabBar class
            new_icon = QIcon(icon.pixmap(QSize(32, 32)).transformed(QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation))
        self.tabs.tabBar().setTabIcon(i, new_icon)

    @pyqtSlot("QWidget*", "QWidget*")
    def on_focusChanged(self, old, now):
        if self.urlbar == now:
            QTimer.singleShot(100, self.urlbar.selectAll)

    # method to update the url when tab is changed
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

    def current_tab_changed(self, i):

        if i < self.tabs.count() - 1:
            # get the url
            qurl = self.tabs.currentWidget().url()

            # update the url
            self.update_urlbar(qurl, self.tabs.currentWidget())

            # reload url (saves time at start, while not taking much if already loaded)
            # self.tabs.currentWidget().reload()

            browser: QWebEngineView = self.tabs.currentWidget()
            page: QWebEnginePage = browser.page()
            if page.isLoading():
                if not self.spinner.isSpinning:
                    self.spinner.start()
            else:
                if self.spinner.isSpinning:
                    self.spinner.stop()

        if self.search_widget.isVisible():
            self.search_widget.hide()

    def tab_clicked(self, i):

        if app.mouseButtons() == Qt.MouseButton.LeftButton:
            if i == self.tabs.count() - 1:
                self.urlbar.setText("")
                self.urlbar.repaint()
                self.add_new_tab()

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
        self.close_action.triggered.connect(lambda: self.close_current_tab(i))
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

    def tab_moved(self, to_index, from_index):

        # updating index-dependent signals when tab is moved
        # destination tab
        page = self.tabs.widget(to_index).page()
        page.titleChanged.disconnect()
        page.titleChanged.connect(lambda title, index=to_index: self.title_changed(title, index))
        page.iconChanged.disconnect()
        page.iconChanged.connect(lambda icon, index=to_index: self.icon_changed(icon, index))

        if to_index == self.tabs.count() - 1:
            # Avoid moving last tab (add new tab) if dragging another tab onto it
            self.tabs.removeTab(from_index)
            self.add_tab_action()

        else:
            # origin tab
            page = self.tabs.widget(from_index).page()
            page.titleChanged.disconnect()
            page.titleChanged.connect(lambda title, index=from_index: self.title_changed(title, index))
            page.iconChanged.disconnect()
            page.iconChanged.connect(lambda icon, index=from_index: self.icon_changed(icon, index))

    def close_current_tab(self, i):
        # if there is only one tab
        if self.tabs.count() < 2:
            # close application
            QCoreApplication.quit()

        else:
            # else remove the tab
            self.tabs.widget(i).deleteLater()
            self.tabs.removeTab(i)
            if self.tabs.currentIndex() == self.tabs.count() - 1:
                self.tabs.setCurrentIndex(self.tabs.currentIndex() - 1)

        # updating index-dependent signals when tab is moved
        for j in range(i, self.tabs.count() - 1):
            page = self.tabs.widget(j).page()
            page.titleChanged.disconnect()
            page.titleChanged.connect(lambda title, index=j: self.title_changed(title, index))
            page.iconChanged.disconnect()
            page.iconChanged.connect(lambda icon, index=j: self.icon_changed(icon, index))

    # action to load the home page
    def navigate_home(self):
        # go to google
        self.tabs.currentWidget().load(QUrl(self.homePage))

    # method for navigate to url
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

    def manage_search(self):

        if self.search_widget.isVisible():
            self.search_widget.hide()

        else:
            x = self.x() + self.width() - 660
            y = self.y() + self.navtb.height()
            self.search_widget.move(x, y)
            self.search_widget.show()

    def searchPage(self, button, forward):
        textToFind = self.search_widget.getText()
        if textToFind:
            if forward:
                self.tabs.currentWidget().findText(textToFind)
            else:
                self.tabs.currentWidget().findText(textToFind, QWebEnginePage.FindFlag.FindBackward)

    def manage_cookies(self, clicked):

        if clicked:
            self.cookies = not self.cookies
        self.cookie_btn.setText("🍪" if self.cookies else "⛔")
        self.cookie_btn.setToolTip("Cookies are now %s" % ("enabled" if self.cookies else "disabled"))

    def clean_all(self):

        self.clean_dlg.close()

        for i in range(self.tabs.count() - 1):
            browser: QWebEngineView = self.tabs.widget(i)
            browser.history().clear()
            page: QWebEnginePage = browser.page()
            page.history().clear()
            page.profile().clearAllVisitedLinks()
            page.profile().defaultProfile().clearAllVisitedLinks()
            page.profile().clearHttpCache()
            page.profile().defaultProfile().clearHttpCache()
            page.profile().defaultProfile().cookieStore().deleteAllCookies()
            page.profile().setPersistentStoragePath(self.lastCache)
            # page.profile().setCachePath(self.lastCache)
            browser.reload()

        # activate cache deletion upon closing app
        self.deleteCache = True

        # set a new cache folder (old ones will be deleted when app is restarted)
        self.lastCache = os.path.join(self.cachePath, str(time.time()))

    def fullscr(self, request):

        if request.toggleOn():
            self.navtb.setVisible(False)
            self.tabs.tabBar().setVisible(False)
            request.accept()
            self.showFullScreen()

        else:
            self.navtb.setVisible(True)
            self.tabs.tabBar().setVisible(True)
            request.accept()
            self.showNormal()

    def inspect_page(self, p):

        self.inspector.page().setInspectedPage(p)
        self.inspector.setWindowTitle("Web Inspector - " + p.title())
        self.inspector.show()

    def openLinkRequested(self, request):

        if request.destination() == QWebEngineNewWindowRequest.DestinationType.InNewWindow:
            self.show_in_new_window([[request.requestedUrl(), 1.0, True]])

        elif request.destination() == QWebEngineNewWindowRequest.DestinationType.InNewTab:
            self.add_new_tab(request.requestedUrl())

    def manage_autohide(self):

        self.autoHide = not self.autoHide
        self.auto_btn.setText("⇱" if self.autoHide else "⇲")
        self.auto_btn.setToolTip("Auto-hide is now " + ("Enabled" if self.autoHide else "Disabled"))

        if self.autoHide:
            self.navtb.hide()
            self.hoverHWidget.show()
            self.tabs.tabBar().hide()
            if not self.h_tabbar:
                self.hoverVWidget.show()

        else:
            self.navtb.show()
            self.hoverHWidget.hide()
            self.tabs.tabBar().show()
            self.hoverVWidget.hide()

    def manage_downloads(self):

        if self.dl_manager.isVisible():
            self.dl_manager.hide()
            self.dl_btn.setText("🡣")

        else:
            self.show_dl_manager()

    def show_dl_manager(self):

        self.dl_manager.show()
        x = self.x() + self.width() - self.dl_manager.width()
        y = self.y() + self.navtb.height()
        self.dl_manager.move(x, y)
        self.dl_btn.setText("🡡")

    # adding action to download files
    def download_file(self, item: QWebEngineDownloadRequest):
        if self.dl_manager.addDownload(item):
            self.show_dl_manager()

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
        # propagate event
        QMainWindow.resizeEvent(self, event)

        if self.custom_titlebar:
            # update grip areas
            self.updateGrips()

            # adjust to screen edges:
            mousePos = QCursor.pos()
            if -5 < mousePos.y() < 5 or self.screenSize.height() - 5 < mousePos.y() < self.screenSize.height() + 5:
                self.setGeometry(self.x(), 0, self.width(), self.screenSize.height())

        if self.autoHide:
            # update hover areas
            self.hoverHWidget.setGeometry(48, 0, self.width(), 20)
            self.hoverVWidget.setGeometry(0, 48, 20, self.height())

        if self.dl_manager.isVisible():
            # reposition download list
            x = self.x() + self.width() - self.dl_manager.width()
            y = self.y() + self.navtb.height()
            self.dl_manager.move(x, y)

        if self.search_widget.isVisible():
            # reposition search widget
            x = self.x() + self.width() - 660
            y = self.y() + self.navtb.height()
            self.search_widget.move(x, y)

    def closeEvent(self, a0, QMouseEvent=None):

        # stop animations
        self.spinner.stop()
        self.spinner.close()

        # stop existing downloads:
        self.dl_manager.close()
        self.dl_manager.cancelAllDownloads()

        # Save current browser contents and settings
        if not self.isNewWin:
            # only main instance may save settings
            tabs = []
            for i in range(self.tabs.count() - 1):
                browser = self.tabs.widget(i)
                tabs.append([browser.url().toString(), browser.page().zoomFactor(), i == self.tabs.currentIndex()])
            self.config["tabs"] = tabs
            self.config["pos"] = [self.pos().x(), self.pos().y()]
            self.config["size"] = [self.size().width(), self.size().height()]
            self.config["cookies"] = self.cookies
            self.config["h_tabbar"] = self.h_tabbar
            self.config["auto_hide"] = self.autoHide

            # save other open windows
            # only open windows when main instance is closed will be remembered
            new_wins = []
            for w in self.instances:
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

            self.config["new_wins"] = new_wins

            with open("coward.json", "w") as f:
                f.write(json.dumps(self.config, indent=4))

            # restart app to wipe all cache folders but the last one
            if self.deleteCache:
                QCoreApplication.quit()
                status = QProcess.startDetached(sys.executable, sys.argv + ["--delete_cache"] + [self.lastCache])


class SearchWidget(QWidget):

    def __init__(self, parent, searchCallback):
        super(SearchWidget, self).__init__(parent)

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setStyleSheet("background: #323232; color: white; border: 1px solid lightgrey;")
        self.setFixedSize(300, 54)

        self.searchCallback = searchCallback
        with open(resource_path("qss/small_button.qss")) as f:
            self.buttonStyle = f.read()

        # create a horizontal layout
        self.mainLayout = QHBoxLayout()
        self.mainLayout.setContentsMargins(5, 5, 5, 5)
        self.mainLayout.setSpacing(10)
        self.setLayout(self.mainLayout)

        # text box to fill in target search
        self.search_box = QLineEdit()
        self.search_box.setStyleSheet("background: #161616; color: white; border: none; border-radius:4px;")
        self.search_box.setFixedSize(200, 24)
        self.search_box.returnPressed.connect(lambda button=None, forward=True: self.searchCallback(button, forward))
        self.mainLayout.addWidget(self.search_box)

        # adding a separator
        separator = QLabel()
        separator.setFixedSize(1, 32)
        separator.setPixmap(QPixmap(resource_path("res/tabsep.png")))
        self.mainLayout.addWidget(separator)

        # search forward button
        self.search_forward = QPushButton("▼")
        self.search_forward.setStyleSheet(self.buttonStyle)
        font = self.search_forward.font()
        font.setPointSize(font.pointSize() + 10)
        self.search_forward.setFont(font)
        self.search_forward.clicked.connect(lambda button, forward=True: self.searchCallback(button, forward))
        self.mainLayout.addWidget(self.search_forward)

        # search backward button
        self.search_backward = QPushButton("▲")
        self.search_backward.setStyleSheet(open(resource_path("qss/small_button.qss")).read())
        font = self.search_backward.font()
        font.setPointSize(font.pointSize() + 10)
        self.search_backward.setFont(font)
        self.search_forward.clicked.connect(lambda button, forward=False: self.searchCallback(button, forward))
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

    def __init__(self, parent=None):
        super(DownloadManager, self).__init__(parent)

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)

        self.setWindowTitle("Coward - Downloads")
        self.setStyleSheet("background: #323232; color: white;")
        self.mainLayout = QVBoxLayout()
        self.mainLayout.setContentsMargins(5, 5, 5, 5)
        self.mainLayout.setSpacing(10)
        self.setLayout(self.mainLayout)

        self.init_label = QLabel("No Donwloads active yet...")
        # self.init_label.setStyleSheet("background: #323232; color: white; border: none;")
        self.init_label.setContentsMargins(10, 0, 0, 0)
        self.init_label.setFixedWidth(460)
        self.init_label.setFixedHeight(60)
        self.mainLayout.addWidget(self.init_label)

        self.downloads = {}

        self.pause_ico = "||"
        self.cancel_ico = "ℵ"
        self.resume_ico = "⟳"
        self.folder_ico = "🗀"

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

        self.init_label.setText("Downloads")

        widget = QWidget()
        widget.setStyleSheet("background: #646464; color: white;")
        layout = QGridLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        name = QLabel()
        name.setFixedWidth(400)
        name.setFixedHeight(30)
        name.setText(title)
        name.setObjectName("name")
        name.setToolTip(location)
        layout.addWidget(name, 0, 0)

        prog = QProgressBar()
        prog.setTextVisible(False)
        prog.setFixedWidth(400)
        prog.setFixedHeight(6)
        prog.setMinimum(0)
        prog.setMaximum(100)
        prog.setObjectName("prog")
        layout.addWidget(prog, 1, 0)

        with open(resource_path("qss/small_button.qss")) as f:
            buttonStyle = f.read()

        pause = QPushButton()
        pause.setStyleSheet(buttonStyle)
        pause.setText(self.pause_ico)
        pause.setObjectName("pause")
        pause.setToolTip("Pause Download")
        pause.clicked.connect(lambda checked, b=pause, i=item, l=location: self.pause(checked, b, i, l))
        layout.addWidget(pause, 0, 1)

        close_loc = QPushButton()
        close_loc.setStyleSheet(buttonStyle)
        close_loc.setText(self.cancel_ico)
        close_loc.setObjectName("close_loc")
        close_loc.setToolTip("Cancel Download")
        close_loc.clicked.connect(lambda checked, b=close_loc, i=item, l=location: self.close_loc(checked, b, i, l))
        layout.addWidget(close_loc, 0, 2)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 0)

        widget.setLayout(layout)
        self.mainLayout.insertWidget(1, widget)
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
            close_loc.setText(self.folder_ico)
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

        if button.text() == self.pause_ico:
            try:
                item.pause()
            except:
                pass
            button.setText(self.resume_ico)

        elif button.text() == self.resume_ico:
            dl_data = self.downloads.get(str(item.id()), [])
            if dl_data:
                _, _, _, _, widget = dl_data

                item.resume()
                button.setText(self.pause_ico)
                name = widget.findChild(QLabel, "name")
                font = name.font()
                font.setStrikeOut(False)
                name.setFont(font)
                prog = widget.findChild(QProgressBar, "prog")
                prog.show()
                close_loc = widget.findChild(QPushButton, "close_loc")
                close_loc.setText(self.cancel_ico)

    def close_loc(self, checked, button, item, location):

        if button.text() == self.folder_ico:
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

        elif button.text() == self.cancel_ico:
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


class LineEdit(QLineEdit):

    def __init__(self, parent=None):
        super(LineEdit, self).__init__(parent)

    def focusInEvent(self, event):
        # this delay is needed to avoid other mouse events to interfere with selectAll() command
        QTimer.singleShot(200, self.selectAll)
        super(LineEdit, self).focusInEvent(event)


class Dialog(QDialog):

    def __init__(self, parent, title="", message="", buttons=None):
        super().__init__(parent)

        self.setWindowTitle(title or "Warning!")
        self.setWindowIcon(QIcon(resource_path("res/coward.png")))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.buttonBox = QDialogButtonBox(buttons or (QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel))
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.message = QLabel(message or "Lorem ipsum consectetuer adipisci est")

        layout = QVBoxLayout()
        layout.addWidget(self.message)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)


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
                if w.isVisible():
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
    #             painter.drawImage(QRect(r.x() + 8, r.y() + ((r.height() - 32) // 2), 32, 32), QImage(opt.icon.pixmap(QSize(32, 32))))
    #             textGap = 48
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

# creating a PyQt5 application and (windows only) force dark mode
app = QApplication(sys.argv + ['-platform', 'windows:darkmode=1'])

# setting name to the application
app.setApplicationName("Coward")
app.setWindowIcon(QIcon(resource_path("res/coward.png")))

if not hasattr(sys, "_MEIPASS"):
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
