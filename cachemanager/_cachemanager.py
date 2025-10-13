import os
import shutil

from logger import LOGGER, LoggerSettings
from settings import DefaultSettings


class CacheManager:

    def __init__(self, cache_folder):

        # prepare cache folders and variables
        self.cacheStorageFolder = os.path.join(cache_folder, DefaultSettings.Storage.Cache.cacheFolder)
        self.cachePath = os.path.join(self.cacheStorageFolder, DefaultSettings.Storage.Cache.cacheFile)

        self.deleteCacheRequested = False

        LOGGER.write(LoggerSettings.LogLevels.info, "CacheManager", "Finished initialization")

    def deleteCache(self):
        # wipe all cache folders except the last one if requested by user (in a new process, or it will be locked)
        try:
            shutil.rmtree(self.cachePath)
            LOGGER.write(LoggerSettings.LogLevels.info, "CacheManager", "Cache files deleted")
        except:
            LOGGER.write(LoggerSettings.LogLevels.info, "CacheManager", "Cache files not found when trying to delete them")