from enum import Enum


class LoggerSettings:

    class LogLevels(Enum):
        info = "[INFO]"
        warning = "[WARN]"
        error = "[ERROR]"
        fatal = "[FATAL]"

    debugEnabled = False        # print application messages and JavaScriptConsoleMessages
    javaConsoleEnabled = True   # print messages for java console (requires debug enabled)
    requestInterceptorEnabled = True   # print messages from request interceptor (requires debug enabled)
    loggingEnabled = False      # log messages to file instead of printing them (requires debug enabled)
    loggerFolder = ".logs"      # logs folder will be placed next to coward script/exe to facilitate to find them
    logDepth = 1                # max number of old log files to keep (-1 = infinite)
