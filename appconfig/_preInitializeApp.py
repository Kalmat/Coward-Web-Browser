import os
import sys

import utils
from logger import LOGGER
from settings import DefaultSettings
from ._common import (setDPIAwareness, setSystemDPISettings, setApplicationDPISettings, force_icon,
                      exception_hook, set_widevine_var, set_multimedia_preferred_plugins)
from ._options import OptionsParser


def preInitializeApp(options):

    def overrideDefaultSettings(options: OptionsParser):

        # enable / disable debug, including Chromium debug info
        if options.enableDebug is not None:
            LOGGER.enableDebug(options.enableDebug)
            # is this necessary or are these messages also caught by JavaScriptConsoleMessages()?
            # utils.enableChromiumDebug()

        # enable / disable debugging javascript console messages (requires to enable debug too)
        if options.enableJavaConsoleMessages is not None:
            LOGGER.enableJavaConsoleMessages(options.enableJavaConsoleMessages)

        # enable / disable debugging adblocker messages in request interceptor (requires to enable debug too)
        if options.enableRequestInterceptorMessages is not None:
            LOGGER.enableRequestInterceptorMessages(options.enableRequestInterceptorMessages)

        # enable / disable logging to file
        if options.enableLogging is not None:
            LOGGER.enableLogging(options.enableLogging)

        # enable / disable ad blocker
        if options.enableAdblocker is not None:
            DefaultSettings.AdBlocker.enableAdBlocker = options.enableAdblocker

        # select security level
        if options.securityLevel is not None:
            DefaultSettings.Security.securityLevel = options.securityLevel

        if options.theme is not None:
            DefaultSettings.Theme.defaultTheme = options.theme

        if options.externalPlayerType is not None:
            DefaultSettings.Player.externalPlayerType = options.externalPlayerType

    # Qt6 is DPI-Aware, so all this is not likely required
    if options.enableDPI:
        setDPIAwareness()
        setSystemDPISettings()
        setApplicationDPISettings()

    # try to load widevine if available
    set_widevine_var(os.path.join("externalplayer", "widevine", "widevinecdm.dll"))

    # this might be useful when using QMediaPlayer (or maybe not...)
    if DefaultSettings.Player.externalPlayerType in (DefaultSettings.Player.PlayerTypes.qt,
                                                     DefaultSettings.Player.PlayerTypes.qt_ffmpeg_Udp,
                                                     DefaultSettings.Player.PlayerTypes.qt_ffmpeg_Stdout):
        set_multimedia_preferred_plugins()

    if not utils.is_packaged():

        # change application icon even when running as Python script
        force_icon('kalmat.coward.nav.01')

        # This will allow to show some tracebacks (not all, anyway)
        sys._excepthook = sys.excepthook
        sys.excepthook = exception_hook

    overrideDefaultSettings(options)

