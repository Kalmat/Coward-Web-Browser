import os
import shutil

from PyQt6.QtCore import QSettings

from logger import LOGGER, LoggerSettings
from settings import DefaultSettings


class History:

    def __init__(self, history_folder, history_file):

        self._historyObj = QSettings(QSettings.Format.IniFormat,
                                     QSettings.Scope.UserScope,
                                     history_folder,
                                     history_file
                                     )

        if not os.path.exists(self.historyFolder):
            os.makedirs(self.historyFolder)

        self._historyValues = self._getDict("History/history", {})
        self.filterHistory()
        LOGGER.write(LoggerSettings.LogLevels.info, "History", f"History loaded")

    def _getDict(self, key, defaultValue):
        value = defaultValue
        try:
            value = self._historyObj.value(key)
        except:
            LOGGER.write(LoggerSettings.LogLevels.warning, "History", f"Wrong value in History: {key}")
        return value or defaultValue

    @property
    def historyFolder(self):
        return os.path.dirname(self._historyObj.fileName())

    @property
    def historyFile(self):
        return os.path.basename(self._historyObj.fileName())

    @property
    def historyPath(self):
        return self._historyObj.fileName()

    def filterHistory(self):
        historySorted = {}
        icons = []
        # sort by date and discard items beyond maximum history size (also delete icon file if not needed anymore)
        for i, (url, item) in enumerate(sorted(self._historyValues.items(), reverse=True, key=lambda item: item[1]["date"])):
            item = self._historyValues[url]
            icon = item["icon"]
            if i <= DefaultSettings.History.historySize:
                historySorted[url] = item
                if icon not in icons:
                    icons.append(icon)
            else:
                if icon != DefaultSettings.Icons.loading and os.path.exists(icon) and icon not in icons:
                    try:
                        os.remove(icon)
                    except:
                        pass
        self._historyValues = historySorted

    @property
    def history(self):
        return self._historyValues

    def addHistoryEntry(self, item):
        added = True
        date, title, url, icon = item
        item = self._historyValues.get(url, None)
        if item is not None:
            added = False
            del self._historyValues[url]
        self._historyValues[url] = {
            "date": date,
            "title": title,
            "icon": icon
        }
        return added

    def updateHistoryEntry(self, url, title=None, icon=None):
        item = self._historyValues.get(url, None)
        if item is not None:
            if title is not None:
                item["title"] = title
            if icon is not None:
                item["icon"] = icon
            self._historyValues[url] = item

    def deleteHistoryEntry(self, url):
        try:
            del self._historyValues[url]
            LOGGER.write(LoggerSettings.LogLevels.info, "History", f"History entry deleted: {url}")
        except:
            LOGGER.write(LoggerSettings.LogLevels.warning, "HistoryManager", f"History entry couldn't be deleted: {url}")

    def deleteAllHistory(self):
        try:
            shutil.rmtree(self.historyFolder)
            self._historyValues = {}
            self.saveHistory()
            LOGGER.write(LoggerSettings.LogLevels.info, "HistoryManager", "History deleted")
        except:
            LOGGER.write(LoggerSettings.LogLevels.warning, "HistoryManager", "History folder not found when trying to delete it")

    def saveHistory(self):
        self._historyObj.setValue("History/history", self._historyValues)
        LOGGER.write(LoggerSettings.LogLevels.info, "HistoryManager", "History saved")

    def instance(self):
        if self._historyObj is None:
            return None
        else:
            return self
