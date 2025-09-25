from enum import Enum


class LoggerSettings:
    class LogLevels(Enum):
        info = "[INFO]"
        warning = "[WARN]"
        error = "[ERROR]"
        fatal = "[FATAL]"

    debugEnabled = False  # print application messages and JavaScriptConsoleMessages
    loggingEnabled = False  # log messages to file instead of printing them (requires debug enabled)
    loggerFolder = ".logs"
    logDepth = 0  # max number of old log files to keep (-1 = infinite)

