import os

from PyQt6.QtWebEngineCore import QWebEngineProfile

from settings import DefaultSettings


class WebProfile(QWebEngineProfile):

    def __init__(self, cache_path, browser, cookie_filter=None):

        if cache_path is None:
            super(WebProfile, self).__init__(browser)
            self._setIncognitoPage(cookie_filter)
        else:
            super(WebProfile, self).__init__(os.path.basename(cache_path), browser)
            self._setNormalPage(cache_path, cookie_filter)

    def _setNormalPage(self, cache_path, cookie_filter):

        # profile cache and storage settings
        self.setCachePath(cache_path)
        # this might be redundant since it is a custom storage (not off-the-record)
        self.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.setPersistentStoragePath(cache_path)

        # profile permissions settings
        self.setPersistentPermissionsPolicy(QWebEngineProfile.PersistentPermissionsPolicy.StoreOnDisk)

        # profile cookies settings
        self.setPersistentCookiesPolicy(DefaultSettings.Cookies.persistentPolicy)
        if cookie_filter is not None:
            self.defaultProfile().cookieStore().setCookieFilter(cookie_filter)

    def _setIncognitoPage(self, cookie_filter):

        # profile cookies settings
        self.setPersistentCookiesPolicy(DefaultSettings.Cookies.incognitoPersistentPolicy)
        if cookie_filter is not None:
            self.defaultProfile().cookieStore().setCookieFilter(cookie_filter)
