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
        self._historyValuesByUrl = {}
        self.filterHistory()

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
        keys = list(self._historyValues.keys())
        keys.sort(reverse=True)
        historySorted = {}
        for i, key in enumerate(keys):
            if i <= DefaultSettings.History.historySize:
                item = self._historyValues[key]
                historySorted[key] = item
                self._historyValuesByUrl[item["url"]] = key
            else:
                icon_file = self._historyValues[key]["icon"]
                if os.path.exists(icon_file):
                    try:
                        os.remove(icon_file)
                    except:
                        pass
        self._historyValues = historySorted

    @property
    def history(self):
        return self._historyValues

    def addHistoryEntry(self, value):
        added = True
        date, title, url, icon = value
        old_date = self._historyValuesByUrl.get(url, None)
        self._historyValuesByUrl[url] = date
        if old_date is not None:
            added = False
            del self._historyValues[old_date]
        self._historyValues[date] = {
            "title": title,
            "url": url,
            "icon": icon
        }
        return added

    def deleteHistoryEntry(self, key):
        try:
            url = self._historyValues[key]["url"]
            del self._historyValues[key]
            del self._historyValuesByUrl[url]
            LOGGER.write(LoggerSettings.LogLevels.info, "History", f"History entry deleted: {url}")
        except:
            LOGGER.write(LoggerSettings.LogLevels.warning, "HistoryManager", f"History entry couldn't be deleted: {key}")

    def deleteAllHistory(self):
        try:
            shutil.rmtree(self.historyFolder)
            self._historyValues = {}
            self._historyValuesByUrl = {}
            self.saveHistory()
            LOGGER.write(LoggerSettings.LogLevels.info, "HistoryManager", "History deleted")
        except:
            LOGGER.write(LoggerSettings.LogLevels.warning, "HistoryManager", "History folder not found when trying to delete it")

    def saveHistory(self):
        self._historyObj.setValue("History/history", self._historyValues)

    def instance(self):
        if self._historyObj is None:
            return None
        else:
            return self
