from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

import utils
from settings import DefaultSettings


def setAppAttributes(parent):

    # is this useful in any scenario?
    # QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)

    # setting window title and icon
    parent.setWindowTitle(DefaultSettings.App.appName)
    parent.setWindowIcon(QIcon(DefaultSettings.App.appIcon))

    # if not setting this, main window loses focus and flickers when showing tooltips... ????
    parent.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)

    # This is required by sidegrips to make them invisible (hide dots), and also by shadow
    parent.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    # Set tracking mouse ON if needed
    # self.setMouseTracking(True)


def appGeometry(parent, position, size, is_custom_title, is_new_win):

    screenSize = utils.screenSize(parent)
    x, y = position.x(), position.y()
    w, h = size.width(), size.height()
    gap = 0 if is_custom_title else 50
    if is_new_win:
        x += 50
        y += 50
        gap += 50
    x = max(0, min(x, screenSize.width() - w))
    y = max(gap, min(y, screenSize.height() - h))
    w = max(800, min(w, screenSize.width() - x))
    h = max(600, min(h, screenSize.height() - y))
    rect = QRect(x, y, w, h)
    return rect


def setGraphicsEffects(MainWindow):

    MainWindow.setContentsMargins(10, 10, 10, 10)
    effect = QGraphicsDropShadowEffect(MainWindow)
    effect.setBlurRadius(15)
    effect.setOffset(0, 0)
    effect.setColor(Qt.GlobalColor.black)
    MainWindow.setGraphicsEffect(effect)

