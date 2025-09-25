import os
import shutil

from PyQt6.QtCore import QSettings, QPoint, QSize

from logger import LOGGER, LoggerSettings
import utils
from ._default_settings import DefaultSettings


class Settings:

    def __init__(self, parent):

        self._settings = QSettings(QSettings.Format.IniFormat,
                                   QSettings.Scope.UserScope,
                                   DefaultSettings.Storage.App.storageFolder,
                                   DefaultSettings.Storage.Settings.settingsFile
                                   )

        self._allowCookies = self._getBool("Security/cookies", True)
        self._enableHistory = self._getBool("Security/history", True)
        self._theme = self._getStr("Appearance/theme", DefaultSettings.Theme.defaultTheme)
        self._forceDark = self._getBool("Appearance/dark", False)
        self._incognitoTheme = self._getStr("Appearance/incognito_theme", DefaultSettings.Theme.deafultIncognitoTheme)
        self._isCustomTitleBar = self._getBool("Appearance/custom_title", True)
        self._horizontalTabBar = self._getBool("Appearance/h_tabbar", False)
        self._iconSize = self._getInt("Appearance/icon_size", 24)
        self._radius = self._getInt("Appearance/border_radius", 0)
        self._autoHide = self._getBool("Appearance/auto_hide", False)
        self._position = self._settings.value("Window/pos", QPoint(100, 100))
        self._size = self._settings.value("Window/size", QSize(min(utils.screenSize(parent).width() // 2, 1024), min(utils.screenSize(parent).height() - 200, 1024)))
        self._previousTabs = self._getList("Session/tabs", DefaultSettings.Browser.defaultTabs)
        self._newwindows = self._getList("Session/new_wins", [])

    def _getValue(self, key, defaultValue):
        value = defaultValue
        try:
            value = self._settings.value(key)
        except Exception as e:
            LOGGER.write(LoggerSettings.LogLevels.info, "Settings", f"Invalid settings key: {key}")
        return value

    def _getStr(self, key, defaultValue):
        value = defaultValue
        try:
            value = self._settings.value(key)
        except:
            LOGGER.write(LoggerSettings.LogLevels.info, "Settings", f"Invalid settings key: {key}")
        return str(value or defaultValue)

    def _getInt(self, key, defaultValue):
        value = defaultValue
        try:
            value = self._settings.value(key)
        except:
            LOGGER.write(LoggerSettings.LogLevels.info, "Settings", f"Invalid settings key: {key}")
        return int(value or defaultValue)

    def _getBool(self, key, defaultValue):
        value = defaultValue
        try:
            value = self._settings.value(key)
        except:
            LOGGER.write(LoggerSettings.LogLevels.info, "Settings", f"Invalid settings key: {key}")
        return bool((value or defaultValue) in (True, "true"))

    def _getList(self, key, defaultValue):
        value = defaultValue
        try:
            value = self._settings.value(key)
        except:
            LOGGER.write(LoggerSettings.LogLevels.info, "Settings", f"Invalid settings key: {key}")
        return value or defaultValue

    @property
    def settingsFolder(self):
        return os.path.dirname(self._settings.fileName())

    @property
    def settingsFile(self):
        return os.path.basename(self._settings.fileName())

    @property
    def settingsPath(self):
        return self._settings.fileName()

    def backupSettings(self):
        try:
            shutil.copyfile(self.settingsPath, self.settingsPath + ".bak")
        except:
            LOGGER.write(LoggerSettings.LogLevels.error, "Settings", f"Backup settings failed")

    @property
    def theme(self):
        return self._theme

    def setTheme(self, value, persistent=False):
        self._theme = value
        if persistent:
            self._settings.setValue("Appearance/theme", value)

    @property
    def forceDark(self):
        return self._forceDark

    def setForceDark(self, value, persistent=False):
        self._dark = value
        if persistent:
            self._settings.setValue("Appearance/dark", value)

    @property
    def incognitoTheme(self):
        return self._incognitoTheme

    def setIncognitoTheme(self, value, persistent=False):
        self._incognitoTheme = value
        if persistent:
            self._settings.setValue("Appearance/incognito_theme", value)

    @property
    def isCustomTitleBar(self):
        return self._isCustomTitleBar

    def setCustomTitleBar(self, value, persistent=False):
        self._isCustomTitleBar = value
        if persistent:
            self._settings.setValue("Appearance/custom_title", value)

    @property
    def autoHide(self):
        return self._autoHide

    def setAutoHide(self, value, persistent=False):
        self._autoHide = value
        if persistent:
            self._settings.setValue("Appearance/auto_hide", value)

    @property
    def position(self):
        return self._position

    def setPosition(self, value, persistent=False):
        self._position = value
        if persistent:
            self._settings.setValue("Window/pos", value)

    @property
    def size(self):
        return self._size

    def setSize(self, value, persistent=False):
        self._size = value
        if persistent:
            self._settings.setValue("Window/size", value)

    @property
    def radius(self):
        return self._radius

    def setRadius(self, value, persistent=False):
        self._radius = value
        if persistent:
            self._settings.setValue("Appearance/border_radius", value)

    @property
    def iconSize(self):
        return self._iconSize

    def setIconSize(self, value, persistent=False):
        self._iconSize = value
        if persistent:
            self._settings.setValue("Appearance/icon_size", value)

    @property
    def allowCookies(self):
        return self._allowCookies

    def setAllowCookies(self, value, persistent=False):
        self._allowCookies = value
        if persistent:
            self._settings.setValue("Security/cookies", value)

    @property
    def enableHistory(self):
        return self._enableHistory

    def setEnableHistory(self, value, persistent=False):
        self._enableHistory = value
        if persistent:
            self._settings.setValue("Security/history", value)

    @property
    def isTabBarHorizontal(self):
        return self._horizontalTabBar

    @property
    def isTabBarVertical(self):
        return not self._horizontalTabBar

    def setTabBarHorizontal(self, value, persistent=False):
        self._horizontalTabBar = value
        if persistent:
            self._settings.setValue("Appearance/h_tabbar", value)

    def setTabBarVertical(self, value, persistent=False):
        self._horizontalTabBar = not value
        if persistent:
            self._settings.setValue("Appearance/h_tabbar", not value)

    @property
    def previousTabs(self):
        return self._previousTabs

    def setPreviousTabs(self, value, persistent=False):
        self._previousTabs = value
        if persistent:
            self._settings.setValue("Session/tabs", value)

    @property
    def newWindows(self):
        return self._newwindows

    def setNewWindows(self, value, persistent=False):
        self._newwindows = value
        if persistent:
            self._settings.setValue("Session/new_wins", value)

    def instance(self):
        if self._settings is None:
            return None
        else:
            return self
