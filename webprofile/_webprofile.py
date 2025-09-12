import os
import time

from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo
from adblockparser import AdblockRules

from settings import DefaultSettings


class WebProfile(QWebEngineProfile):

    def __init__(self, cache_path, browser=None, cookie_filter=None):

        if cache_path is None:
            super(WebProfile, self).__init__(browser)
            self._setIncognitoPage()
        else:
            super(WebProfile, self).__init__(os.path.basename(cache_path), browser)
            self._setNormalPage(cache_path)

        # set cookie filter
        if cookie_filter is not None:
            self.defaultProfile().cookieStore().setCookieFilter(cookie_filter)

        # set request interceptor
        # this ad page makes the whole browser crash: https://aswpsdkeu.com/notify/v2/ua-sdk.min.js
        # TODO: how to fix it? (it's going to be impossible to manage all these pages)
        self.interceptor = RequestInterceptor(["aswpsdkeu"], DefaultSettings.App.enableAdBlocker)
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


class RequestInterceptor(QWebEngineUrlRequestInterceptor):

    def __init__(self, blocked_urls, enableAdBlocker=False):
        super().__init__()

        # List of URLs (as strings or patterns) to block
        self.blocked_urls = blocked_urls

        # enable / disable adblocker
        self.enableAdBlocker = enableAdBlocker

        # this is extremely slow!!!! Unable to install pyre2 (wheel build fails)
        if self.enableAdBlocker:
            if time.time() - os.path.getmtime("easylist.txt") >= 7 * 86400:
                self.updateRules()

            # Load EasyList rules (download easylist.txt beforehand)
            with open("easylist.txt", "r", encoding="utf-8") as f:
                raw_rules = f.readlines()

            # Create AdblockRules instance
            self.rules = AdblockRules(raw_rules, skip_unsupported_rules=False, use_re2=True)

    def interceptRequest(self, info: QWebEngineUrlRequestInfo):
        url = info.requestUrl().url()
        # print("INTERCEPTOR", info.firstPartyUrl(), info.navigationType(), info.initiator(), info.requestMethod(), url)

        # Check if the request URL is in the blocked list
        if any(blocked in url for blocked in self.blocked_urls):
            # Block the request (redirect to about:blank? How to detect it is not the "main" url???)
            info.block(True)
            print(f"Black List Blocked: {url}")

        # check ad-block rules
        elif self.enableAdBlocker:
            if self.rules.should_block(url):
                info.block(True)
                print(f"AD Blocked: {url}")

    def updateRules(self):

        import requests
        url = 'https://easylist.to/easylist/easylist.txt'
        response = requests.get(url)
        if response.status_code == 200:
            with open("easylist.txt", "wb") as file:
                file.write(response.content)
            print("File downloaded successfully!")
        else:
            print("Failed to download the file.")