from PyQt6.QtCore import Qt, QCoreApplication, QSize
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolButton, QLabel, QSizePolicy, QMenu, QStyle, QTabWidget

from downloadmanager import DownloadManager
from lineedit import LineEdit
from searchwidget import SearchWidget
from hoverwidget import HoverWidget
from settings import DefaultSettings
from sidegrips import AppSideGrips
from tabbar import TabBar
from themes import Themes
from titlebar import TitleBar


class Ui_MainWindow:

    def __init__(self, parent, settings, is_new_win, is_icognito):

        # prepare grips to resize window when using a custom title bar
        if settings.isCustomTitleBar:
            self.appGrips = AppSideGrips(parent, DefaultSettings.Grips.gripSize)

        # creating download manager before custom title bar to allow moving it too
        self.dl_manager = DownloadManager(parent)
        self.dl_manager.hide()

        # creating search widget before custom title bar to allow moving it too
        self.search_widget = SearchWidget(parent, parent.searchPage)
        self.search_widget.hide()

        # creating a toolbar for navigation
        self.navtab = TitleBar(parent, settings.isCustomTitleBar, None, parent.leaveNavBarSig)
        self.navtab.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.navtab.setMovable(False)
        self.navtab.setFloatable(False)
        self.navtab.setFloatable(False)
        parent.addToolBar(self.navtab)

        # adding toggle vertical / horizontal tabbar button
        # self.toggleTab_btn = QToolButton(self.navtab)
        # self.toggleTab_btn.setObjectName("toggle_tab")
        # font = self.toggleTab_btn.font()
        # font.setPointSize(font.pointSize() + 2)
        # self.toggleTab_btn.setFont(font)
        # self.toggleTab_act = self.navtab.addWidget(self.toggleTab_btn)

        # adding auto-hide mgt.
        self.auto_on_char = "⇲"
        self.auto_off_char = "⇱"
        self.auto_btn = QAction(self.auto_on_char if settings.autoHide else self.auto_off_char, self.navtab)
        font = self.auto_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.auto_btn.setFont(font)
        self.auto_btn.setToolTip("Auto-hide is now " + ("Enabled" if settings.autoHide else "Disabled"))
        self.navtab.addAction(self.auto_btn)

        self.navtab.addSeparator()

        # creating back action
        self.back_btn = QAction("🡠", self.navtab)
        font = self.back_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.back_btn.setFont(font)
        self.back_btn.setDisabled(True)
        self.back_btn.setToolTip("Back to previous page")
        self.navtab.addAction(self.back_btn)

        # adding next button
        self.next_btn = QAction("🡢", self.navtab)
        font = self.next_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.next_btn.setFont(font)
        self.next_btn.setDisabled(True)
        self.next_btn.setToolTip("Forward to next page")
        self.navtab.addAction(self.next_btn)

        # adding reload / stop button
        self.reload_char = "⟳"
        self.stop_char = "⤬"
        self.reload_btn = QAction(self.reload_char, self.navtab)
        font = self.reload_btn.font()
        font.setPointSize(font.pointSize() + 10)
        self.reload_btn.setFont(font)
        self.reload_btn.setToolTip("Reload page")
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
        self.urlbar.setMaximumHeight(parent.action_size - 6)
        self.urlbar.setTextMargins(10, 0, 0, 0)
        self.urlbar.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.navtab.addWidget(self.urlbar)

        # adding a space in between to allow moving the window in all sizes
        spacer = QLabel()
        spacer.setObjectName("spacer")
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        spacer.setMinimumWidth(20)
        spacer.setMaximumWidth(150)
        self.navtab.addWidget(spacer)

        # adding stream button
        self.ext_player_btn = QAction("ျ", self.navtab)  # ြ🗔🗔🕹ျ𓂀⏿
        font = self.next_btn.font()
        font.setPointSize(font.pointSize() + 4)
        self.ext_player_btn.setFont(font)
        self.ext_player_btn.setToolTip("Open in external player\n"
                                       "(may fix non-compatible media issues)")
        self.navtab.addAction(self.ext_player_btn)

        # adding search option
        self.search_on_btn = QToolButton(self.navtab)
        self.search_on_btn.setObjectName("search_on")
        font = self.search_on_btn.font()
        font.setPointSize(font.pointSize() + 8)
        self.search_on_btn.setFont(font)
        self.search_on_btn.setText("⌕")
        self.search_on_btn.setToolTip("Search text in this page")
        self.search_on_act = self.navtab.addWidget(self.search_on_btn)

        self.search_off_btn = QToolButton(self.navtab)
        self.search_off_btn.setObjectName("search_off")
        font = self.search_off_btn.font()
        font.setPointSize(font.pointSize() + 8)
        self.search_off_btn.setFont(font)
        self.search_off_btn.setText("⌕")
        self.search_off_btn.setToolTip("Search text in this page")
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
        self.dl_on_act = self.navtab.addWidget(self.dl_on_btn)

        self.dl_off_btn = QToolButton(self.navtab)
        self.dl_off_btn.setObjectName("dl_off")
        font = self.dl_off_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.dl_off_btn.setFont(font)
        self.dl_off_btn.setText("🡣")
        self.dl_off_btn.setToolTip("Show / hide downloads")
        self.dl_off_act = self.navtab.addWidget(self.dl_off_btn)
        self.dl_off_act.setVisible(False)

        self.navtab.addSeparator()

        # adding cookie mgt.
        self.cookie_btn = QAction("", self.navtab)
        font = self.cookie_btn.font()
        font.setPointSize(font.pointSize() + 4)
        self.cookie_btn.setFont(font)
        self.navtab.addAction(self.cookie_btn)

        # adding cleaning mgt.
        self.clean_btn = QAction("🧹", self.navtab)
        font = self.clean_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.clean_btn.setFont(font)
        self.clean_btn.setToolTip("Erase history and cookies")
        self.navtab.addAction(self.clean_btn)

        # adding open incognito window 🕶️🕶🥷👻👺
        self.ninja_btn = QToolButton(self.navtab)
        self.ninja_btn.setObjectName("incognito")
        self.ninja_btn.setText("👻")
        font = self.ninja_btn.font()
        font.setPointSize(font.pointSize() + 6)
        self.ninja_btn.setFont(font)
        self.ninja_btn.setToolTip("Open new window in incognito mode")
        self.ninja_act = self.navtab.addWidget(self.ninja_btn)
        if parent.isNewWin:
            if parent.isIncognito:
                self.ninja_act.setDisabled(True)
            else:
                self.ninja_act.setVisible(False)

        if parent.settings.isCustomTitleBar:
            self.navtab.addSeparator()

            self.min_btn = QAction("―", self.navtab)
            self.min_btn.setToolTip("Minimize")
            font = self.min_btn.font()
            font.setPointSize(font.pointSize() + 2)
            self.min_btn.setFont(font)
            self.navtab.addAction(self.min_btn)

            self.max_btn = QAction(" ⃞ ", self.navtab)
            self.max_btn.setToolTip("Maximize")
            font = self.max_btn.font()
            font.setPointSize(font.pointSize() + 4)
            self.max_btn.setFont(font)
            self.navtab.addAction(self.max_btn)

            self.closewin_btn = QToolButton(self.navtab)
            self.closewin_btn.setObjectName("close_win")
            self.closewin_btn.setText("🕱")
            self.closewin_btn.setToolTip("Quit, coward")
            font = self.closewin_btn.font()
            font.setPointSize(font.pointSize() + 8)
            self.closewin_btn.setFont(font)
            self.navtab.addWidget(self.closewin_btn)


        # tab bar styles
        # horizontal
        self.h_tab_style = Themes.styleSheet(DefaultSettings.Theme.defaultTheme, Themes.Section.horizontalTabs)
        self.h_tab_style = self.h_tab_style % (DefaultSettings.Icons.tabSeparator, parent.action_size, int(parent.action_size * 0.75))
        # vertical
        self.v_tab_style = Themes.styleSheet(DefaultSettings.Theme.defaultTheme, Themes.Section.verticalTabs)
        self.v_tab_style = self.v_tab_style % (parent.action_size, parent.action_size)

        # creating a tab widget
        self.tabs = QTabWidget(parent)
        self.tabBar = TabBar(self.tabs, None, parent.leaveTabBarSig)
        self.tabs.setTabBar(self.tabBar)
        self.tabs.setMovable(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North if settings.isTabBarHorizontal else QTabWidget.TabPosition.West)
        self.tabs.tabBar().setContentsMargins(0, 0, 0, 0)
        self.tabs.tabBar().setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.tabs.tabBar().setIconSize(QSize(settings.iconSize, settings.iconSize))

        # creating a context menu to allow closing tabs when close button is hidden
        self.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabsContextMenu = QMenu()
        self.tabsContextMenu.setMinimumHeight(parent.action_size + 6)
        self.tabsContextMenu.setContentsMargins(0, 5, 0, 0)
        self.close_action = QAction()
        self.close_action.setIcon(parent.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical))
        self.tabsContextMenu.addAction(self.close_action)

        # creating a context menu to allow closing tabs when close button is hidden
        self.newTabContextMenu = QMenu()
        self.newTabContextMenu.setMinimumHeight(parent.action_size + 6)
        self.newTabContextMenu.setContentsMargins(0, 5, 0, 0)
        self.newWindow_action = QAction()
        self.newWindow_action.setIcon(parent.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton))
        self.newWindow_action.setText("Open new tab in separate window")
        self.newTabContextMenu.addAction(self.newWindow_action)

        # making document mode true
        self.tabs.setDocumentMode(True)

        # making tabs as central widget
        parent.setCentralWidget(self.tabs)

        # set hover areas for auto-hide mode
        # auto-hide navigation bar
        self.hoverHWidget = HoverWidget(parent, self.navtab, parent.enterHHoverSig)
        self.navtab.setFixedHeight(parent.action_size + 4)
        self.hoverHWidget.setGeometry(parent.x(), parent.y(), parent.width(), 20)
        self.hoverHWidget.hide()
        # auto-hide tab bar
        self.hoverVWidget = HoverWidget(parent, self.tabs.tabBar(), parent.enterVHoverSig)
        self.hoverVWidget.setGeometry(parent.x(), parent.action_size, 20, parent.height())
        self.hoverVWidget.hide()

    def retranslateUi(self, MainWindow):
        _translate = QCoreApplication.translate
        # MainWindow.setWindowTitle(_translate("MainWindow", "Sample Editor"))
        # self.menu_File.setTitle(_translate("MainWindow", "&File"))
        pass
