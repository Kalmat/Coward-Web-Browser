import os

from PyQt6.QtWebEngineCore import QWebEngineProfile

from settings import DefaultSettings


class WebProfile(QWebEngineProfile):

    def __init__(self, cache_path, browser=None, cookie_filter=None, interceptor_manager=None):

        if cache_path is None:
            super(WebProfile, self).__init__(browser)
            self._setIncognitoPage()
        else:
            super(WebProfile, self).__init__(os.path.basename(cache_path), browser)
            self._setNormalPage(cache_path)

        # set cookie filter
        if cookie_filter is not None:
            self.defaultProfile().cookieStore().setCookieFilter(cookie_filter)

        # set request interceptor if needed
        # e.g. this ad page makes the whole browser crash: https://aswpsdkeu.com/notify/v2/ua-sdk.min.js
        # it seems impossible to automatically prevent these errors
        # included a "Fatal Error" page to detect these pages and manually avoid them using interceptor's urlBlackList
        # if DefaultSettings.AdBlocker.urlBlackList or enableAdBlocker:
        self.interceptor = interceptor_manager
        self.setUrlRequestInterceptor(self.interceptor)

    def _setNormalPage(self, cache_path):

        # profile cache and storage settings
        self.setCachePath(cache_path)
        # this might be redundant since it is a custom storage (not off-the-record)
        self.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.setPersistentStoragePath(cache_path)

        # profile permissions settings
        self.setPersistentPermissionsPolicy(QWebEngineProfile.PersistentPermissionsPolicy.StoreOnDisk)

        # profile cookies settings
        self.setPersistentCookiesPolicy(DefaultSettings.Cookies.persistentPolicy)

    def _setIncognitoPage(self):

        # profile cookies settings
        self.setPersistentCookiesPolicy(DefaultSettings.Cookies.incognitoPersistentPolicy)
