import os
import re
import sys
import traceback

import numpy as np
import psutil
from PIL import Image
from PIL.ImageQt import ImageQt
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QStyleFactory, QApplication


def screenSize(parent):
    return parent.screen().availableGeometry()


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
                                                % resource_path(widevine_relative_path, inverted=True, use_dist_folder="dist"))


def set_multimedia_preferred_plugins():
    flags = os.environ.get('QT_MULTIMEDIA_PREFERRED_PLUGINS', "")
    os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = (flags + ' windowsmediafoundation')


def fixDarkImage(pixmap):

    def pixmapToArray(pixmap):
        try:
            return np.array(Image.fromqpixmap(pixmap))
        except:
            return None

    def is_dark(array, thrshld=64):
        return np.mean(array) <= thrshld

    def changeImageBackground(array):
        array[array[:, :, 3] == 0] = [255, 255, 255, 255]
        return array

    array = pixmapToArray(pixmap)
    if array is not None and is_dark(array):
        array = changeImageBackground(array)
        pil_image = Image.fromarray(array)
        qt_image = ImageQt(pil_image)
        pixmap = QPixmap.fromImage(qt_image)

    return pixmap


def kill_process(proc_pid):
    # Thanks to Jovik: https://stackoverflow.com/questions/4789837/how-to-terminate-a-python-subprocess-launched-with-shell-true
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()


def is_packaged():
    return getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")


def app_location():
    # this function returns de actual application location (where .py or .exe files are located)
    # Thanks to pullmyteeth: https://stackoverflow.com/questions/404744/determining-application-path-in-a-python-exe-generated-by-pyinstaller
    if is_packaged():
        location = os.path.dirname(sys.executable)
    else:
        location = os.path.dirname(sys.modules["__main__"].__file__)
    return location


def resource_path(relative_path, inverted=False, use_dist_folder=""):
    # this will find resources packaged or not within the executable, with a relative path from application folder
    # when intended to use pyinstaller, move the external resources to the dist folder and set use_dist_folder accordingly (most likely "dist")
    path = ""
    ret = ""
    found = False
    if is_packaged():
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        ret = os.path.normpath(os.path.join(base_path, relative_path))
        if os.path.exists(ret):
            found = True

    if not found:
        # resource is not package within executable
        base_path = app_location()
        if not is_packaged():
            base_path = os.path.normpath(os.path.join(base_path, use_dist_folder))
        ret = os.path.normpath(os.path.join(base_path, relative_path))
        if os.path.exists(ret):
            found = True

    if found:
        if inverted:
            # required in some syntax (e.g. .qss)
            ret = ret.replace("\\", "/")
        path = ret

    return path


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
