import os
import shutil
import subprocess

from PyQt6.QtCore import Qt, QDir
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest
from PyQt6.QtWidgets import QPushButton, QProgressBar, QLabel, QGridLayout, QWidget, QFileDialog, QVBoxLayout

import utils
from logger import LOGGER, LoggerSettings
from settings import DefaultSettings


class DownloadManager(QWidget):

    _item_width = 356
    _item_height = 54

    def __init__(self, parent=None):
        super(DownloadManager, self).__init__(parent)

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)

        # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # effect = QGraphicsDropShadowEffect()
        # effect.setColor(QApplication.palette().color(QPalette.ColorRole.Shadow))
        # effect.setBlurRadius(50)
        # effect.setOffset(5)
        # self.setGraphicsEffect(effect)

        self.setWindowTitle("Coward - Downloads")
        self.mainLayout = QVBoxLayout()
        self.mainLayout.setContentsMargins(5, 5, 5, 5)
        self.mainLayout.setSpacing(10)
        self.setLayout(self.mainLayout)

        self.init_label = QLabel("No Donwloads active yet...")
        self.init_label.setContentsMargins(10, 0, 0, 0)
        self.init_label.setFixedSize(self._item_width, self._item_height)
        self.mainLayout.addWidget(self.init_label)

        self.downloads = {}

        self.pause_char = "⫿⫿"
        self.cancel_char = "🗙"
        self.resume_char = "⟳"
        self.folder_char = "🗀"

        # to avoid garbage, downloads will be stored in system Temp folder, then moved to selected location
        self.tempFolder = os.path.join(DefaultSettings.App.tempFolder, DefaultSettings.Downloads.downloadTempFolder)
        try:
            shutil.rmtree(self.tempFolder)
        except:
            LOGGER.write(LoggerSettings.LogLevels.info, "DownloadManager", "Download temp folder not found")

    def addDownload(self, item):

        accept = True
        added = False
        filename = ""
        tempfile = ""
        if item and item.state() == QWebEngineDownloadRequest.DownloadState.DownloadRequested:

            if item.isSavePageDownload():
                # download the whole page content (html file + folder)
                item.setSavePageFormat(QWebEngineDownloadRequest.SavePageFormat.CompleteHtmlSaveFormat)

            norm_name = utils.get_valid_filename(item.downloadFileName())
            filename, _ = QFileDialog.getSaveFileName(self, "Save File As", QDir(item.downloadDirectory()).filePath(norm_name))
            if filename:
                filename = os.path.normpath(filename)
                tempfile = os.path.join(self.tempFolder, str(item.id()), os.path.basename(filename))
                item.setDownloadDirectory(os.path.dirname(tempfile))
                item.setDownloadFileName(os.path.basename(filename))
                item.receivedBytesChanged.connect(lambda i=item.id(): self.updateDownload(i))
                item.isFinishedChanged.connect(lambda i=item.id(): self.downloadFinished(i))
                item.stateChanged.connect(lambda s, i=item.id(): self.onStateChanged(s, i))
                added = True

            else:
                accept = False

        if accept:
            item.accept()
            if added:
                # request is triggered several times. Only the first time will be added to the UI
                self._add(item, os.path.basename(filename), filename, tempfile)

        else:
            item.cancel()
            del item

        return added

    def _add(self, item, title, location, tempfile):

        self.init_label.hide()

        widget = QWidget()
        widget.setObjectName("dl_item")
        widget.setFixedSize(self._item_width, self._item_height)
        layout = QGridLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        name = QLabel()
        name.setObjectName("name")
        name.setText(title)
        name.setToolTip(location)
        layout.addWidget(name, 0, 0)

        prog = QProgressBar()
        prog.setObjectName("prog")
        prog.setTextVisible(False)
        prog.setFixedHeight(10)
        prog.setMinimum(0)
        prog.setMaximum(100)
        layout.addWidget(prog, 1, 0)

        pause = QPushButton()
        pause.setObjectName("pause")
        pause.setText(self.pause_char)
        pause.setToolTip("Pause download")
        pause.clicked.connect(lambda checked, b=pause, i=item, l=location: self.pause(checked, b, i, l))
        layout.addWidget(pause, 0, 1)

        close_loc = QPushButton()
        close_loc.setText(self.cancel_char)
        close_loc.setObjectName("close_loc")
        close_loc.setToolTip("Cancel download")
        close_loc.clicked.connect(lambda checked, b=close_loc, i=item, l=location: self.close_loc(checked, b, i, l))
        layout.addWidget(close_loc, 0, 2)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 0)

        widget.setLayout(layout)
        self.mainLayout.insertWidget(0, widget)
        self.downloads[str(item.id())] = [item, title, location, tempfile, widget]

    def updateDownload(self, dl_id):

        dl_data = self.downloads.get(str(dl_id), [])
        if dl_data:
            item, _, _, _, widget = dl_data

            prog = widget.findChild(QProgressBar, "prog")
            value = int(item.receivedBytes() / (item.totalBytes() or 1) * 100)
            prog.setValue(value)

    def downloadFinished(self, dl_id):

        dl_data = self.downloads.get(str(dl_id), [])
        if dl_data:
            item, _, location, tempfile, widget = dl_data

            pause = widget.findChild(QPushButton, "pause")
            pause.hide()
            close_loc = widget.findChild(QPushButton, "close_loc")
            close_loc.setText(self.folder_char)
            close_loc.setToolTip("Open file location")
            prog = widget.findChild(QProgressBar, "prog")
            prog.hide()
            if item.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                try:
                    shutil.move(tempfile, location)
                    if item.isSavePageDownload():
                        shutil.move(tempfile.rsplit(".", 1)[0] + "_files", os.path.dirname(location))
                except:
                    LOGGER.write(LoggerSettings.LogLevels.error, "DownloadManager", "Temp file not found. Download failed")

    def onStateChanged(self, state, dl_id):

        dl_data = self.downloads.get(str(dl_id), [])
        if dl_data:
            item, _, location, tempfile, widget = dl_data

            if state not in (QWebEngineDownloadRequest.DownloadState.DownloadInProgress,
                             QWebEngineDownloadRequest.DownloadState.DownloadCompleted):
                name = widget.findChild(QLabel, "name")
                font = name.font()
                font.setStrikeOut(True)
                name.setFont(font)
                prog = widget.findChild(QProgressBar, "prog")
                prog.hide()
                pause = widget.findChild(QPushButton, "pause")
                pause.hide()
                close_loc = widget.findChild(QPushButton, "close_loc")
                close_loc.hide()

    def pause(self, checked, button, item, location):

        if button.text() == self.pause_char:
            try:
                item.pause()
            except:
                pass
            button.setText(self.resume_char)

        elif button.text() == self.resume_char:
            dl_data = self.downloads.get(str(item.id()), [])
            if dl_data:
                _, _, _, _, widget = dl_data

                item.resume()
                button.setText(self.pause_char)
                name = widget.findChild(QLabel, "name")
                font = name.font()
                font.setStrikeOut(False)
                name.setFont(font)
                prog = widget.findChild(QProgressBar, "prog")
                prog.show()
                close_loc = widget.findChild(QPushButton, "close_loc")
                close_loc.setText(self.cancel_char)

    def close_loc(self, checked, button, item, location):

        if button.text() == self.folder_char:
            if os.path.isfile(location):
                subprocess.Popen(r'explorer /select, "%s"' % location)
            else:
                button.hide()
                dl_data = self.downloads.get(str(item.id()), [])
                if dl_data:
                    _, _, _, _, widget = dl_data

                    name = widget.findChild(QLabel, "name")
                    font = name.font()
                    font.setStrikeOut(True)
                    name.setFont(font)

        elif button.text() == self.cancel_char:
            try:
                item.cancel()
            except:
                pass
            dl_data = self.downloads.get(str(item.id()), [])
            if dl_data:
                _, _, _, tempfile, widget = dl_data

                name = widget.findChild(QLabel, "name")
                font = name.font()
                font.setStrikeOut(True)
                name.setFont(font)
                prog = widget.findChild(QProgressBar, "prog")
                prog.hide()
                pause = widget.findChild(QPushButton, "pause")
                pause.hide()
                close_loc = widget.findChild(QPushButton, "close_loc")
                close_loc.hide()

    def cancelAllDownloads(self):
        for dl_id in self.downloads.keys():
            item, _, location, tempfile, _ = self.downloads[dl_id]
            try:
                item.cancel()
            except:
                pass
        try:
            shutil.rmtree(self.tempFolder)
        except:
            pass

    def keyReleaseEvent(self, a0):
        self.parent().mouseReleaseEvent(a0)
