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
        self.deleteCache = False

    def checkDeleteCache(self):
        return Options.DeleteCache in sys.argv

    def deleteCache(self, last_cache):
        # wipe all cache folders except the last one if requested by user (in a new process or it will be locked)
        lastCacheName = os.path.basename(last_cache)
        cacheFolder = os.path.dirname(last_cache)
        tempCache = os.path.join(os.path.dirname(cacheFolder), lastCacheName)
        shutil.move(last_cache, tempCache)
        print("CACHE FOLDER", last_cache, cacheFolder)
        # shutil.rmtree(cacheFolder)
        shutil.move(tempCache, cacheFolder)
