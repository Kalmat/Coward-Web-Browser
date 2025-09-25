import os
import time

from ._logger_settings import LoggerSettings


class LoggerManager:

    def __init__(self):

        self.debugEnabled = LoggerSettings.debugEnabled
        self.loggingEnabled = LoggerSettings.loggingEnabled
        self.logDepth = LoggerSettings.logDepth
        self.logFolder = LoggerSettings.loggerFolder

        if not os.path.exists(self.logFolder):
            os.makedirs(self.logFolder)

        self.checkFiles(self.logFolder, self.logDepth)
        self.enableLogging(self.loggingEnabled)

    def enableDebug(self, enable):
        self.debugEnabled = enable

    def enableLogging(self, enable):

        self.loggingEnabled = enable

        if self.loggingEnabled:

            date = time.strftime("%Y%m%d-%H%M%S")
            self.logFile = os.path.join(self.logFolder, f"log-{date}")
            with open(self.logFile, "w"):
                pass

    def setLogDepth(self, logDepth):
        self.logDepth = logDepth
        self.checkFiles(self.logFolder, self.logDepth)

    def write(self, error_level, origin, message, force=False):
        msg = error_level.value + time.strftime(" %Y%m%d-%H%M%S ") + origin + " --- " + message
        if self.debugEnabled or force:
            if self.loggingEnabled:
                with open(self.logFile, 'a') as file:
                    file.write(msg + "\n")
            else:
                print(msg)

    def checkFiles(self, logFolder, logDepth):

        logFiles = list(os.listdir(logFolder))
        logFiles.sort(reverse=True)

        if len(logFiles) > logDepth >= 0:
            for i in range(logDepth, len(logFiles)):
                try:
                    os.remove(os.path.join(logFolder, logFiles[i]))
                except:
                    pass
