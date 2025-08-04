# importing required libraries
import json
import os
import re
import sys
import traceback

from PyQt5.QtCore import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


# main window
class MainWindow(QMainWindow):

    _gripSize = 8

    # constructor
    def __init__(self, parent=None, new_win=False, init_tabs=None):
        super(MainWindow, self).__init__(parent)

        self.new_win = new_win
        self.init_tabs = init_tabs

        # setting window title and icon
        self.setWindowTitle("Coward")
        self.setWindowIcon(QIcon(resource_path("res/coward.png")))

        # get styles from qss folder
        with open(resource_path("qss/main.qss"), "r") as f:
            style = f.read()

        self.setStyleSheet(style)
        app.setStyleSheet(style)

        with open(resource_path("qss/h_tabs.qss"), "r") as f:
            self.h_tab_style = f.read()
            self.close_ico = resource_path("res/close.png", True)
            self.close_sel_ico = resource_path("res/close_sel.png", True)
            self.h_tab_style = self.h_tab_style % (self.close_ico, self.close_sel_ico, self.close_sel_ico)

        with open(resource_path("qss/v_tabs.qss"), "r") as f:
            self.v_tab_style = f.read()

        # Set tracking mouse ON if needed
        # self.setMouseTracking(True)

        # get or create settings
        self.screenSize = self.screen().size()
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
            _ = self.config["new_wins"]

        except:
            # create a default settings file in case of error
            self.config = {"tabs": [["https://www.google.es", 1.0, True]],
                           "pos": (100, 100),
                           "size": (min(self.screenSize.width() // 2, 1024), min(self.screenSize.height() - 200, 1024)),
                           "cookies": True,
                           "h_tabbar": False,
                           "custom_title": True,
                           "new_wins": []
                           }

        # custom / standard title bar
        self.custom_titlebar = self.config["custom_title"]

        # set initial position and size
        x, y = self.config["pos"]
        w, h = self.config["size"]
        if self.new_win:
            x += 50
            y += 50
        x = max(0, min(x, self.screenSize.width() - w))
        gap = 0 if self.custom_titlebar else 50  # standard title bar height
        y = max(gap, min(y, self.screenSize.height() - h))
        w = max(800, min(x + w, self.screenSize.width()))
        h = max(600, min(y + h, self.screenSize.height()))
        self.setGeometry(x, y, w, h)

        # Enable/Disable cookies
        self.cookies = self.config["cookies"]

        # vertical / horizontal tabbar
        self.h_tabbar = self.config["h_tabbar"]

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

        # creating a toolbar for navigation
        if self.custom_titlebar:
            self.navtb = TitleBar(self, open(resource_path("qss/titlebar.qss")).read())
        else:
            self.navtb = QToolBar(self)
            self.navtb.setStyleSheet(open(resource_path("qss/titlebar.qss")).read())
        self.navtb.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.navtb.setFloatable(False)
        self.navtb.setMovable(False)
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

        # similarly adding next button
        self.next_btn = QAction("🡢", self)
        font = self.next_btn.font()
        font.setPointSize(font.pointSize() + 8)
        self.next_btn.setFont(font)
        self.next_btn.setDisabled(True)
        self.next_btn.setToolTip("Forward to next page")
        self.next_btn.triggered.connect(lambda: self.tabs.currentWidget().forward())
        self.navtb.addAction(self.next_btn)

        # similarly adding reload button
        self.reload_btn = QAction("⟳", self)
        font = self.reload_btn.font()
        font.setPointSize(font.pointSize() + 14)
        self.reload_btn.setFont(font)
        self.reload_btn.setToolTip("Reload page")
        self.reload_btn.triggered.connect(lambda: self.tabs.currentWidget().reload())
        self.navtb.addAction(self.reload_btn)

        # creating home action
        self.home_btn = QAction("⌂", self)
        font = self.home_btn.font()
        font.setPointSize(font.pointSize() + 16)
        self.home_btn.setFont(font)
        self.home_btn.setToolTip("Home page")
        self.home_btn.triggered.connect(self.navigate_home)
        self.navtb.addAction(self.home_btn)

        # adding a separator
        # self.navtb.addSeparator()

        spacer = QLabel()
        spacer.setAccessibleName("spacer")
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.navtb.addWidget(spacer)

        # creating a line edit widget for URL
        self.urlbar = LineEdit()
        self.urlbar.setTextMargins(10, 0, 0, 0)
        self.urlbar.setFixedWidth(max(200, min(self.size().width() // 2, self.screenSize.width()//3)))
        self.urlbar.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.urlbar.returnPressed.connect(self.navigate_to_url)

        # adding line edit to toolbar
        self.navtb.addWidget(self.urlbar)

        # similarly adding stop action
        self.stop_btn = QAction("⤫", self)
        font = self.stop_btn.font()
        font.setPointSize(font.pointSize() + 8)
        self.stop_btn.setFont(font)
        self.stop_btn.setToolTip("Stop loading current page")
        self.stop_btn.triggered.connect(lambda: self.tabs.currentWidget().stop())
        self.navtb.addAction(self.stop_btn)

        spacer = QLabel()
        spacer.setAccessibleName("spacer")
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.navtb.addWidget(spacer)

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
        self.tabs = QTabWidget()
        self.tabs.setTabShape(QTabWidget.TabShape.Rounded)
        self.tabs.tabBar().setShape(QTabBar.Shape.RoundedNorth)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North if self.h_tabbar else QTabWidget.TabPosition.West)
        self.tabs.setStyleSheet(self.h_tab_style if self.h_tabbar else self.v_tab_style)
        self.tabs.setMovable(True)
        self.tabs.tabBar().setContentsMargins(0, 0, 0, 0)
        self.tabs.tabBar().setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.tabs.tabBar().setIconSize(QSize(32, 32))
        self.tabs.tabBar().tabMoved.connect(self.tab_moved)

        # creating a context menu to allow closing tabs when close button is hidden
        self.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.showContextMenu)
        self.tabsContextMenu = QMenu()
        self.tabsContextMenu.setMinimumHeight(54)
        self.tabsContextMenu.setContentsMargins(5, 14, 5, 5)
        self.close_action = QAction()
        self.close_action.setIcon(QIcon(self.close_ico))
        self.tabsContextMenu.addAction(self.close_action)
        # Controlling context menu with mouse left-click
        # self.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        # self.tabsContextMenu.aboutToHide.connect(self.menu_hiding)
        # self.tabClicked = False

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
        self.setCentralWidget(self.tabs)

        # open all windows and their tabs
        if self.new_win:
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

        # adding add tab action
        self.add_tab_action()

        # creating a statusbar (required to resize window when applying custom titlebar)
        self.status = QStatusBar(self)
        self.dl_progress = QProgressBar()
        self.dl_progress.setMinimum(0)
        self.dl_progress.setMaximum(100)
        self.status.addPermanentWidget(self.dl_progress)
        self.dl_stop = QPushButton()
        self.dl_stop.setStyleSheet(open(resource_path("qss/small_button.qss")).read())
        self.dl_stop.setIcon(QIcon(self.close_ico))
        self.dl_stop.setText("Cancel Download")
        self.dl_stop.clicked.connect(self.stop_download)
        self.status.addPermanentWidget(self.dl_stop)
        self.setStatusBar(self.status)
        self.statusBar().setVisible(False)

        # Prepare clean all warning dialog
        self.clean_dlg = Dialog(self, message="This will erase all your history and stored cookies.\n\n"
                                              "Are you sure you want to proceed?")
        self.clean_dlg.accepted.connect(self.clean_all)
        self.clean_dlg.rejected.connect(self.clean_dlg.close)

        self.moving = False
        self.maxNormal = False
        self.item = None

        # allTabsButtons = self.tabs.findChildren(QAbstractButton)
        # for button in allTabsButtons:
        #     if button.inherits("CloseButton"):
        #         button.setIcon(QIcon(resource_path("res/close.png")))
        #         button.setIconSize(QSize(24, 24))
        #         button.setToolTip("Test")

    @pyqtSlot("QWidget*", "QWidget*")
    def on_focusChanged(self, old, now):
        if self.urlbar == now:
            QTimer.singleShot(100, self.urlbar.selectAll)

    # method for adding new tab
    def add_tab(self, qurl=None, zoom=1.0, label="Loading..."):

        # if url is blank
        if qurl is None:
            # creating a google url
            qurl = QUrl('http://www.google.es///')

        # creating a QWebEngineView object
        browser = QWebEngineView()
        page = browser.page()

        # Enable/Disable cookies
        page.profile().defaultProfile().cookieStore().setCookieFilter(self.cookie_filter)

        # Enabling fullscreen in YouTube and other sites
        browser.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        page.fullScreenRequested.connect(lambda request: self.fullscr(request))

        # Enabling some extra features
        # page.featurePermissionRequested.connect(lambda u, f, p=page, b=browser: p.setFeaturePermission(u, f, QWebEnginePage.PermissionGrantedByUser))
        page.settings().setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, True)
        browser.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        browser.settings().setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
        browser.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)

        # setting url to browser
        browser.setUrl(qurl)
        # this saves time if launched with several open tabs (will be reloaded in tab_changed() method)
        # browser.stop()

        # setting page zoom factor
        page.setZoomFactor(zoom)

        # setting tab index and default icon
        i = self.tabs.addTab(browser, label if self.h_tabbar else "")
        self.tabs.tabBar().setTabIcon(i, QIcon(resource_path("res/web.png")))

        # adding action to the browser when url changes
        browser.urlChanged.connect(lambda u, b=browser: self.update_urlbar(u, b))

        # adding action to the browser when title or icon change
        page.titleChanged.connect(lambda title, index=i: self.title_changed(title, index))
        page.iconChanged.connect(lambda icon, index=i: self.icon_changed(icon, index))

        # manage file downloads (including pages and files)
        page.profile().downloadRequested.connect(self.download_file)

        # manage context menu options (only those not already working out-of-the-box)
        act1 = page.action(page.WebAction.OpenLinkInNewTab)
        act1.disconnect()
        act1.triggered.connect(lambda checked, p=page: self.add_new_tab(p.contextMenuData().linkUrl()))
        act2 = page.action(page.WebAction.OpenLinkInNewWindow)
        act2.disconnect()
        if self.new_win:
            act2.setVisible(False)
        else:
            act2.triggered.connect(lambda checked, p=page: self.show_in_new_window([[p.contextMenuData().linkUrl(), 1.0, True]]))
        act3 = page.action(page.WebAction.ViewSource)
        self.inspector = QWebEngineView()
        act3.disconnect()
        act3.triggered.connect(lambda checked, p=page: self.inspect_page(p))

        return i

    def fullscr(self, request):
        if request.toggleOn():
            # PyQt fullScreen() doesn't take into account actual screen size
            # e.g. in a monitor using a lower resolution than the standard one (w/ black side stripes)
            # ugly hack to simulate fullscreen without really entering into it
            # from win32api import GetMonitorInfo, MonitorFromPoint
            # primary_monitor = MonitorFromPoint((0, 0))
            # monitor_info = GetMonitorInfo(primary_monitor)
            # monitor_area = monitor_info.get("Monitor")
            # work_area = monitor_info.get("Work")
            # taskbar_height = monitor_area[3] - work_area[3]
            # print("The taskbar height is {}.".format(taskbar_height))
            # self.prev_rect = self.geometry()
            # self.setGeometry(0, 0, self.screenSize.width() - 1, self.screenSize.height() - taskbar_height)
            self.navtb.setVisible(False)
            self.tabs.tabBar().setVisible(False)
            request.accept()
            self.showFullScreen()
        else:
            # self.setGeometry(self.prev_rect)
            self.navtb.setVisible(True)
            self.tabs.tabBar().setVisible(True)
            request.accept()
            self.showNormal()

    # adding action to download files
    def download_file(self, item: QWebEngineDownloadItem):

        accept = True
        if item and item.state() == QWebEngineDownloadItem.DownloadState.DownloadRequested:

            if self.item is None:

                self.item = item

                # download the whole page content
                if item.isSavePageDownload():
                    item.setSavePageFormat(QWebEngineDownloadItem.SavePageFormat.CompleteHtmlSaveFormat)

                itemFileName = item.downloadFileName()
                # download item is proposing ".mhtml" extension for web pages... changing it if that's the case
                if itemFileName.endswith(".mhtml"):
                    itemFileName = itemFileName.rsplit(".mhtml", 1)[0] + ".html"
                norm_name = self.get_valid_filename(itemFileName)
                filename, _ = QFileDialog.getSaveFileName(self, "Save File As",
                                                          QDir(item.downloadDirectory()).filePath(norm_name))
                if filename:
                    filename = os.path.normpath(filename)
                    item.setDownloadDirectory(QFileInfo(filename).path())
                    item.setDownloadFileName(QFileInfo(filename).fileName())
                    item.downloadProgress.connect(lambda p, t=item.totalBytes(), n=item.downloadFileName(): self.download_progress(p, t, n))
                    self.tabs.setStatusTip("Downloading file: " + filename)
                    self.dl_progress.setValue(0)
                    self.dl_stop.setEnabled(True)
                    self.statusBar().setVisible(True)

                else:
                    accept = False

            else:
                dialog = Dialog(self, message="Another download is still active. Please wait...\n",
                                buttons=QDialogButtonBox.StandardButton.Ok)
                dialog.exec()
                accept = False

        if accept:
            item.accept()
        else:
            item.cancel()

    def download_progress(self, progress, total, filename):

        value = int(progress / (total if total != 0 else 1) * 100)
        if value == 100:
            self.item = None
            self.tabs.setStatusTip("Finished downloading: " + filename)
            self.dl_progress.setValue(100)
            self.dl_stop.setDisabled(True)
            self.status.repaint()
            QTimer().singleShot(3000, self.dl_finished)

        elif self.item is not None:
            self.dl_progress.setValue(value)

    def stop_download(self):
        if self.item is not None:
            self.item.cancel()
            self.dl_finished()

    def dl_finished(self):
        self.item = None
        self.tabs.setStatusTip("")
        self.dl_progress.setValue(0)
        self.statusBar().setVisible(False)

    def get_valid_filename(self, name):
        s = str(name).strip().replace(" ", "_")
        s = re.sub(r"(?u)[^-\w.]", "", s)
        if s in {"", ".", ".."}:
            return ""
        return s

    def inspect_page(self, p):

        self.inspector.page().setInspectedPage(p)
        self.inspector.setWindowTitle("Web Inspector - " + p.title())
        self.inspector.show()

    def show_in_new_window(self, tabs):

        if not self.new_win:
            w = MainWindow(new_win=True, init_tabs=tabs)
            self.instances.append(w)
            w.show()

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

    def toggle_tabbar(self, toggle=True):

        if toggle:
            self.h_tabbar = not self.h_tabbar

        for i in range(self.tabs.count() - 1):
            if self.h_tabbar:
                self.title_changed(self.tabs.widget(i).page().title(), i)
            else:
                self.tabs.tabBar().setTabText(i, "")
            self.icon_changed(self.tabs.widget(i).page().icon(), i)

        self.tabs.setStyleSheet(self.h_tab_style if self.h_tabbar else self.v_tab_style)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North if self.h_tabbar else QTabWidget.TabPosition.West)
        self.tabs.setTabsClosable(self.h_tabbar)
        self.tabs.tabBar().setTabButton(self.tabs.count() - 1, QTabBar.ButtonPosition.RightSide, None)
        self.tabs.setContextMenuPolicy(
            Qt.ContextMenuPolicy.PreventContextMenu if self.h_tabbar else Qt.ContextMenuPolicy.CustomContextMenu)
        self.toggleTab_btn.setText("˅" if self.h_tabbar else "˃")
        self.toggleTab_btn.setToolTip("Set %s tabs" % ("vertical" if self.h_tabbar else "horizontal"))

    def cookie_filter(self, request):
        # print(f"firstPartyUrl: {request.firstPartyUrl.toString()}, "
        # f"origin: {request.origin.toString()}, "
        # f"thirdParty? {request.thirdParty}"
        # )
        return self.cookies

    def title_changed(self, title, i):
        self.tabs.tabBar().setTabText(i, (("  " + title[:20]) if len(title) > 20 else title) if self.h_tabbar else "")
        self.tabs.setTabToolTip(i, title + ("" if self.h_tabbar else "\n(Right-click to close)"))

    def icon_changed(self, icon: QIcon, i):
        if self.h_tabbar:
            new_icon = icon
        else:
            new_icon = QIcon(icon.pixmap(QSize(32, 32)).transformed(QTransform().rotate(90),
                                                                    Qt.TransformationMode.SmoothTransformation))
        self.tabs.tabBar().setTabIcon(i, new_icon)

    # when tab is changed
    def current_tab_changed(self, i):

        if i < self.tabs.count() - 1:
            # get the curl
            qurl = self.tabs.currentWidget().url()

            # update the url
            self.update_urlbar(qurl, self.tabs.currentWidget())

            # reload url (saves time at start, while not taking much if already loaded)
            # self.tabs.currentWidget().reload()

        # self.tabClicked = False

    def tab_clicked(self, i):

        if app.mouseButtons() == Qt.MouseButton.LeftButton:
            if i == self.tabs.count() - 1:
                self.add_new_tab()

            # elif 0 <= i < self.tabs.count() - 1:
            #     if not self.h_tabbar and i == self.tabs.currentIndex():
            #         if not self.tabClicked:
            #             self.createContextMenu(i)
            #         else:
            #             self.tabClicked = False

    def showContextMenu(self, point):
        tabIndex = self.tabs.tabBar().tabAt(point)
        if 0 <= tabIndex < self.tabs.count() - 1:
            self.createContextMenu(tabIndex)

    def createContextMenu(self, i):
        text = self.tabs.tabBar().tabToolTip(i)
        self.close_action.setText('Close tab: "' + text + '"')
        self.close_action.triggered.disconnect()
        self.close_action.triggered.connect(lambda: self.close_current_tab(i))
        tab_rect = self.tabs.tabBar().tabRect(i)
        tab_width = tab_rect.width()
        tab_height = tab_rect.height()
        pos = QPoint(self.tabs.tabBar().x() + tab_width, self.tabs.tabBar().y() + tab_height * i)
        self.tabsContextMenu.exec(self.tabs.mapToGlobal(pos))

    # def menu_hiding(self):
    #     mouse_pos: QPoint = self.mapFromGlobal(QCursor.pos())
    #     tabIndex = self.tabs.tabBar().tabAt(QPoint(mouse_pos.x() - self.tabs.x(), mouse_pos.y() - self.tabs.y()))
    #     self.tabClicked = self.tabs.tabBar().rect().contains(mouse_pos) and tabIndex == self.tabs.currentIndex()

    def tab_moved(self, to_index, from_index):
        # updating index-dependent signals when tab is moved
        page = self.tabs.widget(to_index).page()
        page.titleChanged.disconnect()
        page.titleChanged.connect(lambda title, index=to_index: self.title_changed(title, index))
        page.iconChanged.disconnect()
        page.iconChanged.connect(lambda icon, index=to_index: self.icon_changed(icon, index))
        page = self.tabs.widget(from_index).page()
        page.titleChanged.disconnect()
        page.titleChanged.connect(lambda title, index=from_index: self.title_changed(title, index))
        page.iconChanged.disconnect()
        page.iconChanged.connect(lambda icon, index=from_index: self.icon_changed(icon, index))

    def close_current_tab(self, i):
        # if there is only one tab
        if self.tabs.count() < 2:
            # close aplication
            app.quit()

        else:
            # else remove the tab
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
        self.tabs.currentWidget().setUrl(QUrl("https://www.google.es///"))

    def manage_cookies(self, clicked):

        if clicked:
            self.cookies = not self.cookies
        self.cookie_btn.setText("🍪" if self.cookies else "⛔")
        self.cookie_btn.setToolTip("Cookies are now enabled" if self.cookies else "Cookies are now disabled")

    # method for navigate to url
    def navigate_to_url(self):

        # Set default icon
        self.tabs.tabBar().setTabIcon(self.tabs.currentIndex(), QIcon(resource_path("res/web.png")))

        # get the line edit text
        # convert it to QUrl object
        qurl = QUrl(self.urlbar.text())

        # if scheme is blank
        if not qurl.isValid() or "." not in qurl.url():
            # search in Google
            qurl.setUrl("https://www.google.es/search?q=%s&safe=active&" % self.urlbar.text())
        elif qurl.scheme() == "":
            # set scheme
            qurl.setScheme("https")

        # set the url
        self.tabs.currentWidget().setUrl(qurl)

    # method to update the url
    def update_urlbar(self, qurl, browser: QWidget = None):

        # If this signal is not from the current tab, ignore
        if browser != self.tabs.currentWidget():
            # do nothing
            return

        # set text to the url bar
        self.urlbar.setText(qurl.toString())

        # Enable/Disable navigation arrows according to page history
        page = browser.page()
        self.back_btn.setEnabled(page.history().canGoBack())
        self.next_btn.setEnabled(page.history().canGoForward())

    def clean_all(self):
        self.clean_dlg.close()
        for i in range(self.tabs.count() - 1):
            page = self.tabs.widget(i).page()
            page.history().clear()
            page.profile().defaultProfile().cookieStore().deleteAllCookies()

        # Disable navigation arrows (history wiped)
        self.back_btn.setEnabled(False)
        self.next_btn.setEnabled(False)

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

        else:
            self.showMaximized()
            self.maxNormal = True
            self.max_btn.setText("⧉")

    def resizeEvent(self, event):
        # propagate event
        QMainWindow.resizeEvent(self, event)

        # update grip areas
        self.updateGrips()

        # check and adjust urlbar width
        new_width = max(200, min(self.size().width() // 2, self.screenSize.width()//3))
        if self.urlbar.size().width() != new_width:
            self.urlbar.setFixedWidth(new_width)

    def closeEvent(self, a0, QMouseEvent=None):

        # stop existing downloads:
        if self.item is not None:
            self.item.cancel()
            self.item = None

        # Save current browser contents and settings
        # only main instance may save settings
        if not self.new_win:
            tabs = []
            for i in range(self.tabs.count() - 1):
                browser = self.tabs.widget(i)
                tabs.append([browser.url().toString(), browser.page().zoomFactor(), i == self.tabs.currentIndex()])
            self.config["tabs"] = tabs
            self.config["pos"] = [self.pos().x(), self.pos().y()]
            self.config["size"] = [self.size().width(), self.size().height()]
            self.config["cookies"] = self.cookies
            self.config["h_tabbar"] = self.h_tabbar

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
                        new_tabs.append(
                            [browser.url().toString(), browser.page().zoomFactor(), i == w.tabs.currentIndex()])
                    new_wins.append(new_tabs)

                # closing all other open child windows
                w.close()

            self.config["new_wins"] = new_wins

            with open("coward.json", "w") as f:
                f.write(json.dumps(self.config, indent=4))


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


class TitleBar(QToolBar):

    def __init__(self, parent, qss):
        super().__init__(parent)

        self.parent = parent
        self.qss = qss

        self.parent.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAutoFillBackground(True)
        self.setBackgroundRole(QPalette.Highlight)
        self.setStyleSheet(qss)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent.moving = True
            self.parent.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.parent.moving:
            self.parent.move(event.globalPos() - self.parent.offset)


class SideGrip(QWidget):
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


def resource_path(relative_path, inversed=False):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    ret = os.path.normpath(os.path.join(base_path, relative_path))
    if inversed:
        ret = ret.replace("\\", "/")
    return ret


def setDPIAwareness():
    if sys.platform == "win32":
        import ctypes
        try:
            dpiAware = ctypes.windll.user32.GetAwarenessFromDpiAwarenessContext(ctypes.windll.user32.GetThreadDpiAwarenessContext())
        except AttributeError:  # Windows server does not implement GetAwarenessFromDpiAwarenessContext
            dpiAware = 0

        if dpiAware == 0:
            # It seems that this can't be invoked twice. Setting it to 1 for apps having 0 (unaware) may have less impact
            ctypes.windll.shcore.SetProcessDpiAwareness(1)


def setSystemDPISettings():
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_SCALE_FACTOR"] = "1"


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

# TODO: check the behavior of these settings and decide if they are needed and in which cases
# setDPIAwareness()
# setSystemDPISettings()
# app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
# if hasattr(QStyleFactory, 'AA_UseHighDpiPixmaps'):
#     app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

# creating and showing MainWindow object
window = MainWindow()
window.show()

# loop
app.exec()
