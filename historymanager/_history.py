import os

from PyQt6.QtCore import QSettings

from settings import DefaultSettings


class History:

    def __init__(self, history_folder, history_file):

        self._historyObj = QSettings(QSettings.Format.IniFormat,
                                     QSettings.Scope.UserScope,
                                     history_folder,
                                     history_file
                                     )

        self._historyValues = self._getDict("History/history", {})
        self.filterHistory()

    def _getDict(self, key, defaultValue):
        value = defaultValue
        try:
            value = self._historyObj.value(key)
        except:
            pass
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
                historySorted[key] = self._historyValues[key]
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
        for key in self._historyValues.keys():
            item_url = self._historyValues[key]["url"]
            if url == item_url:
                added = False
                del self._historyValues[key]
                break
        self._historyValues[date] = {
            "title": title,
            "url": url,
            "icon": icon
        }
        return added

    def deleteHistoryEntry(self, key):
        try:
            del self._historyValues[key]
        except:
            pass

    def saveHistory(self):
        self._historyObj.setValue("History/history", self._historyValues)

    def instance(self):
        if self._historyObj is None:
            return None
        else:
            return self
