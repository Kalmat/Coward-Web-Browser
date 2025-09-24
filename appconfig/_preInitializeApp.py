import os
import sys

import utils
from settings import DefaultSettings
from ._common import (setDPIAwareness, setSystemDPISettings, setApplicationDPISettings, setupDebug, force_icon,
                      exception_hook, set_widevine_var, set_multimedia_preferred_plugins)


def preInitializeApp(args):

    # setup debug and logging according to args passed
    setupDebug(args)

    # Qt6 is DPI-Aware, so all this is not likely required
    # setDPIAwareness()
    # setSystemDPISettings()
    # setApplicationDPISettings()

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
