import sys

from logger import LOGGER, LoggerSettings
from settings import DefaultSettings
from themes import Themes


class Options:

    deleteCache = "--delete_cache"
    dontCloseOnRelaunch = "--dont_close_on_relaunch"
    deletePlayerTemp = "--delete_player_temp"
    enableDebug = "-enable_debug"
    enableJavaConsoleMessages = "-enable_JavaConsoleMessages"
    enableRequestInterceptorMessages = "-enable_RequestInterceptorMessages"
    enableLogging = "-enable_logging"
    enableDPI = "-enable_DPI"
    securityLevel = "-security_level"
    cookies = "-allow_cookies"
    thirdPartyCookies = "-allow_third_party_cookies"
    enableAdblocker = "-enable_adblocker"
    theme = "-theme"
    externalPlayerType = "-player_type"
    incognitoMode = "--incognito"


class OptionsParser:

    def __init__(self, args):

        self.deleteCache = Options.deleteCache in args
        self.dontCloseOnRelaunch = Options.dontCloseOnRelaunch in args
        self.deletePlayerTemp = Options.deletePlayerTemp in args
        self.enableDebug = self._getBool(args, Options.enableDebug)
        self.enableJavaConsoleMessages = self._getBool(args, Options.enableJavaConsoleMessages)
        self.enableRequestInterceptorMessages = self._getBool(args, Options.enableRequestInterceptorMessages)
        self.enableLogging = self._getBool(args, Options.enableLogging)
        self.enableDPI = Options.enableDPI in args
        self.securityLevel = self._getSecurityLevel(args, Options.securityLevel)
        self.cookies = self._getBool(args, Options.cookies)
        self.thirdPartyCookies = self._getBool(args, Options.cookies)
        self.enableAdblocker = self._getBool(args, Options.enableAdblocker)
        self.theme = self._getTheme(args, Options.theme)
        self.externalPlayerType = self._getPlayerType(args, Options.externalPlayerType)
        self.incognitoMode = True if Options.incognitoMode in args else None

    def _getValue(self, args, option):
        try:
            index = args.index(option)
            value = args[index + 1]
            if not value:
                value = None
        except:
            value = None
        return value

    def _getStr(self, args, option):
        value = self._getValue(args, option)
        if value is not None:
            if value:
                return value
            else:
                LOGGER.write(LoggerSettings.LogLevels.info, "OptionsParser", f"Value is not valid for {option} option", force=True)
        return None

    def _getBool(self, args, option):
        value = self._getValue(args, option)
        if value is not None:
            if value in ("True", "true", "1", "False", "false", "0"):
                return value in ("True", "true", "1")
            else:
                valid_values = "True/true/1 or False/false/0"
                LOGGER.write(LoggerSettings.LogLevels.info, "OptionsParser", f"Value for {option} must be in {valid_values}", force=True)
        return None

    def _getSecurityLevel(self, args, option):
        value = self._getValue(args, option)
        if value is not None:
            if value in DefaultSettings.Security.SecurityLevels:
                return value
            else:
                valid_values = [(item.value + " / ") for i, item in enumerate(LoggerSettings.LogLevels) if i < len(LoggerSettings.LogLevels) - 1]
                LOGGER.write(LoggerSettings.LogLevels.info, "OptionsParser", f"Value for {option} must be one of: {valid_values}", force=True)
        return None

    def _getTheme(self, args, option):
        value = self._getValue(args, option)
        if value is not None:
            if value in Themes.Theme:
                return value
            else:
                valid_values = [(item.value + " / ") for i, item in enumerate(Themes.Theme) if i < len(Themes.Theme) - 1]
                LOGGER.write(LoggerSettings.LogLevels.info, "OptionsParser", f"Value for {option} must be one of: {valid_values}", force=True)
        return None

    def _getPlayerType(self, args, option):
        value = self._getValue(args, option)
        if value is not None:
            if value in DefaultSettings.Player.PlayerTypes:
                return value
            else:
                valid_values = [(item.value + " / ") for i, item in enumerate(DefaultSettings.Player.PlayerTypes) if i < len(DefaultSettings.Player.PlayerTypes) - 1]
                LOGGER.write(LoggerSettings.LogLevels.info, "OptionsParser", f"Value for {option} must be one of: {valid_values}", force=True)
        return None


OPTIONS = OptionsParser(sys.argv)
