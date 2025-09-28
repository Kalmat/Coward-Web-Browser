from enum import Enum


class LoggerSettings:
    class LogLevels(Enum):
        info = "[INFO]"
        warning = "[WARN]"
        error = "[ERROR]"
        fatal = "[FATAL]"

    debugEnabled = False  # print application messages and JavaScriptConsoleMessages
    javaConsoleEnabled = False   # print messages for java console (requires debug enabled)
    requestInterceptorEnabled = False   # print messages from request interceptor (requires debug enabled)
    loggingEnabled = False  # log messages to file instead of printing them (requires debug enabled)
    loggerFolder = ".logs"
    logDepth = 0  # max number of old log files to keep (-1 = infinite)

