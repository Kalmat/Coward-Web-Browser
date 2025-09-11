import os
import shutil
import sys

from appconfig import Options
from settings import DefaultSettings


class CacheManager:

    def __init__(self, cache_folder):

        # prepare cache folders and variables
        self.cacheStorageFolder = os.path.join(cache_folder, DefaultSettings.Storage.Cache.cacheFolder)
        self.cachePath = os.path.join(self.cacheStorageFolder, DefaultSettings.Storage.Cache.cacheFile)

        self.lastCache = ""
        self.deleteCacheRequested = False

    def checkDeleteCache(self, args=None):
        last_cache = ""
        for i, item in enumerate(args or sys.argv[1:]):
            if item == Options.DeleteCache:
                last_cache = sys.argv[i + 1]
                break
        return last_cache

    def deleteCache(self, last_cache):
        # wipe all cache folders except the last one if requested by user (in a new process or it will be locked)
        lastCacheName = os.path.basename(last_cache)
        cacheFolder = os.path.dirname(last_cache)
        tempCache = os.path.join(os.path.dirname(cacheFolder), lastCacheName)
        shutil.move(last_cache, tempCache)
        shutil.rmtree(cacheFolder)
        shutil.move(tempCache, cacheFolder)
