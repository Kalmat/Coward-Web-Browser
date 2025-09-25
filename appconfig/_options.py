import sys

from settings import DefaultSettings
from themes import Themes


class Options:

    deleteCache = "-delete_cache"
    deletePlayerTemp = "--delete_player_temp"
    enableDebug = "--enable_debug"
    enableLogging = "--enable_logging"
    enableDPI = "--enable_DPI"
    securityLevel = "-security_level"
    cookies = "--allow_cookies"
    thirdPartyCookies = "--allow_third_party_cookies"
    enableAdblocker = "-enable_adblocker"
    theme = "-theme"
    externalPlayerType = "-player_type"
    incognitoMode = "-incognito"


class OptionsParser:

    def __init__(self, args):

        self.lastCache = self._getStr(args, Options.deleteCache)
        self.deleteCache = self.lastCache is not None
        self.deletePlayerTemp = Options.deletePlayerTemp in args
        self.enableDebug = self._getBool(args, Options.enableDebug)
        self.enableLogging = self._getBool(args, Options.enableLogging)
        self.enableDPI = Options.deleteCache in args
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
        except:
            value = None
        return value

    def _getStr(self, args, option):
        value = self._getValue(args, option)
        return value if value else None

    def _getBool(self, args, option):
        value = self._getValue(args, option)
        return value if value is not None and value in ("True", "true", "1") else None

    def _getSecurityLevel(self, args, option):
        value = self._getValue(args, option)
        return value if value is not None and value in DefaultSettings.Security.SecurityLevels else None

    def _getTheme(self, args, option):
        value = self._getValue(args, option)
        return value if value is not None and value in Themes.Theme else None

    def _getPlayerType(self, args, option):
        value = self._getValue(args, option)
        return value if value is not None and value in DefaultSettings.Player.PlayerTypes else None


OPTIONS = OptionsParser(sys.argv)