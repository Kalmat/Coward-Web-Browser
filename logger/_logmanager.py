import os
import time

from ._logger_settings import LoggerSettings


class LoggerManager:

    def __init__(self):

        self.debugEnabled = LoggerSettings.debugEnabled
        self.javaConsoleMessagesEnabled = LoggerSettings.javaConsoleEnabled
        self.requestInterceptorMessagesEnabled = LoggerSettings.requestInterceptorEnabled
        self.loggingEnabled = LoggerSettings.loggingEnabled
        self.logDepth = LoggerSettings.logDepth
        self.logFolder = LoggerSettings.loggerFolder

        if self.loggingEnabled and not os.path.exists(self.logFolder):
            os.makedirs(self.logFolder)

        self.checkFiles(self.logFolder, self.logDepth)
        self.enableLogging(self.loggingEnabled)

    def enableDebug(self, enable):
        self.debugEnabled = enable

    def enableJavaConsoleMessages(self, enable):
        self.javaConsoleMessagesEnabled = enable

    def enableRequestInterceptorMessages(self, enable):
        self.requestInterceptorMessagesEnabled = enable

    def enableLogging(self, enable):

        self.loggingEnabled = enable

        if self.loggingEnabled:

            if not os.path.exists(self.logFolder):
                os.makedirs(self.logFolder)

            date = time.strftime("%Y%m%d-%H%M%S")
            self.logFile = os.path.join(self.logFolder, f"log-{date}")
            with open(self.logFile, "w", encoding="utf-8"):
                pass

    def setLogDepth(self, logDepth):
        self.logDepth = logDepth
        self.checkFiles(self.logFolder, self.logDepth)

    def write(self, error_level, origin, message, force=False):
        msg = error_level.value + time.strftime(" %Y/%m/%d-%H:%M:%S ") + origin + " --- " + message
        if self.debugEnabled or force:
            if (origin not in ("JavaScriptConsole", "RequestInterceptor") or
                    (origin == "JavaScriptConsole" and self.javaConsoleMessagesEnabled) or
                    (origin == "RequestInterceptor" and self.requestInterceptorMessagesEnabled)):
                if self.loggingEnabled:
                    with open(self.logFile, 'a', encoding="utf-8") as file:
                        file.write(msg + "\n")
                else:
                    print(msg)

    def checkFiles(self, logFolder, logDepth):

        if os.path.isdir(logFolder):
            logFiles = list(os.listdir(logFolder))
            logFiles.sort(reverse=True)

            if len(logFiles) > logDepth >= 0:
                for file in logFiles[logDepth:]:
                    try:
                        os.remove(os.path.join(logFolder, file))
                    except:
                        pass
