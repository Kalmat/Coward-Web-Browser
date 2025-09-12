import os
import time
import requests

from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo
from adblockparser import AdblockRules

from settings import DefaultSettings


class WebProfile(QWebEngineProfile):

    def __init__(self, cache_path, browser=None, cookie_filter=None, enableAdBlocker=False, rulesFolder=""):

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
        self.interceptor = RequestInterceptor(["aswpsdkeu"], enableAdBlocker, rulesFolder)
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

    def __init__(self, blocked_urls, enableAdBlocker=False, rulesFolder=""):
        super().__init__()

        # List of URLs (as strings or patterns) to block
        self.blocked_urls = blocked_urls
        self.rulesPath = os.path.join(rulesFolder, "easylist.txt")

        # enable / disable adblocker
        self.enableAdBlocker = enableAdBlocker

        # this is extremely slow!!!!
        # Installing pyre2 may improve performance, but fails to install (wheel build fails)
        if enableAdBlocker:
            if not os.path.exists(self.rulesPath) or time.time() - os.path.getmtime(self.rulesPath) >= 7 * 86400:
                self.updateRules(self.rulesPath)

            # Load EasyList rules (download easylist.txt beforehand)
            with open(self.rulesPath, "r", encoding="utf-8") as f:
                raw_rules = f.readlines()

            # Create AdblockRules instance
            self.rules = AdblockRules(raw_rules,
                                      # use_re2 = True,  # enable this again when pyre2 is installed
                                      skip_unsupported_rules=False)

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

    def updateRules(self, rulesPath):

        response = requests.get(DefaultSettings.Browser.rulesFile)
        if response.status_code == 200:
            with open(rulesPath, "wb") as file:
                file.write(response.content)
            print("File downloaded successfully!")
        else:
            print("Failed to download the file.")