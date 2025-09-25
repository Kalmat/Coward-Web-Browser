import os
import sys
import traceback

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QStyleFactory, QApplication

import utils


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


def enableChromiumDebug():
    # this must be set before creating QWebEngineView objects
    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (flags + ' --enable-logging=stderr --v=0')


def set_widevine_var(widevine_relative_path):
    # to play some media which uses non-built-in codecs, QtWebEngine must be built with option -webengine-proprietary-codecs
    # https://doc.qt.io/qt-6/qtwebengine-features.html#audio-and-video-codecs
    # in addition to that, for some sites using widevine (DRM protection), this variable must also be set before creating app:
    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (flags + ' --widevine-path="%s"'
                                                % utils.resource_path(widevine_relative_path, inverted=True, use_dist_folder="dist"))


def set_multimedia_preferred_plugins():
    flags = os.environ.get('QT_MULTIMEDIA_PREFERRED_PLUGINS', "")
    os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = (flags + ' windowsmediafoundation')
