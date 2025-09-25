import os
import time

from settings import DefaultSettings


class Logger:

    def __init__(self):

        self.debugEnabled = DefaultSettings.Logger.debugEnabled
        self.loggingEnabled = DefaultSettings.Logger.loggingEnabled
        self.logDepth = DefaultSettings.Logger.logDepth

        self.logFolder = DefaultSettings.Logger.loggerFolder

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
        msg = str(error_level) + time.strftime(" %Y%m%d-%H%M%S ") + origin + " --- " + message
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
