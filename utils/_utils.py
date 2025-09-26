import os
import re
import sys

import numpy as np
import psutil
from PIL import Image
from PIL.ImageQt import ImageQt
from PyQt6.QtGui import QPixmap


def screenSize(parent):
    return parent.screen().availableGeometry()


def fixDarkImage(pixmap):

    def pixmapToArray(pixmap):
        try:
            return np.array(Image.fromqpixmap(pixmap))
        except:
            return None

    def is_dark(array, thrshld=64):
        try:
            # Create a boolean mask for pixels where the alpha channel is 255 (fully transparent)
            transparent_mask = array[:, :, 3] == 255
            # Use the mask to select only the non-transparent pixels
            non_transparent_pixels = array[transparent_mask][:, :3]
        except:
            # some icons will not have any alpha channel, then take the original image
            non_transparent_pixels = array
        return np.mean(non_transparent_pixels) <= thrshld

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
