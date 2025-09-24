import os
import requests

from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo
from settings import DefaultSettings
try:
    from braveblock import Adblocker
except:
    DefaultSettings.AdBlocker.enableAdBlocker = False


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

        # set request interceptor if needed
        # e.g. this ad page makes the whole browser crash: https://aswpsdkeu.com/notify/v2/ua-sdk.min.js
        # it seems impossible to automatically prevent these errors
        # included a "Fatal Error" page to detect these pages and manually avoid them using interceptor's urlBlackList
        if DefaultSettings.AdBlocker.urlBlackList or enableAdBlocker:
            self.interceptor = RequestInterceptor(DefaultSettings.AdBlocker.urlBlackList, enableAdBlocker, rulesFolder)
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
        self.rulesPath = os.path.join(rulesFolder, DefaultSettings.AdBlocker.rulesFile)

        # enable / disable adblocker
        self.enableAdBlocker = enableAdBlocker

        if enableAdBlocker:
            # if not os.path.exists(self.rulesPath) or time.time() - os.path.getmtime(self.rulesPath) >= 7 * 86400:
            #     self.updateRules(self.rulesPath)
            #
            # Load EasyList rules (download easylist.txt beforehand)
            # with open(self.rulesPath, "r", encoding="utf-8") as f:
            #     raw_rules = f.readlines()

            # Create Adblocker instance
            self.adblocker = Adblocker(
                include_easylist=True,
                include_easyprivacy=True
            )

    def interceptRequest(self, info: QWebEngineUrlRequestInfo):
        url = info.requestUrl().url()
        # print("INTERCEPTOR", info.firstPartyUrl(), info.navigationType(), info.initiator(), info.requestMethod(), url)

        # Check if the request URL is in the blocked list
        if any(blocked in url for blocked in self.blocked_urls):
            # Block the request (redirect to about:blank? How to detect it is not the "main" url???)
            info.block(True)
            # print(f"Black List Blocked: {url}")

        # check ad-block rules
        elif self.enableAdBlocker:
            if self.adblocker.check_network_urls(
                    url=url,
                    source_url=info.initiator().url(),
                    request_type=self.getRequestType(info.resourceType())
            ):
                info.block(True)
                # print(f"AD Blocked: {url}")

    def getRequestType(self, resourceType):
        """
            document: Represents a request for a document (HTML page).
            image: Represents a request for an image file (e.g., .jpg, .png).
            script: Represents a request for a JavaScript file.
            stylesheet: Represents a request for a CSS stylesheet.
            xmlhttprequest: Represents requests made using the XMLHttpRequest object or fetch API.
            subdocument: Represents embedded pages, usually included via HTML inline frames (iframes).
            ping: Represents requests initiated via the navigator.sendBeacon() method.
            websocket: Represents requests initiated via the WebSocket object.
        """

        if resourceType == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame:
            requestType = "document"
        elif resourceType == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeSubFrame:
            requestType = "subdocument"
        elif resourceType == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeStylesheet:
            requestType = "stylesheet"
        elif resourceType == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeScript:
            requestType = "script"
        elif resourceType == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeImage:
            requestType = "image"
        elif resourceType == QWebEngineUrlRequestInfo.ResourceType.ResourceTypePing:
            requestType = "ping"
        elif resourceType == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeScript:
            requestType = "script"
        elif resourceType == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeWebSocket:
            requestType = "websocket"
        # Add more cases as needed
        else:
            requestType = ""
        return requestType


    def updateRules(self, rulesPath):

        response = requests.get(DefaultSettings.AdBlocker.rulesFileUrl)
        if response.status_code == 200:
            with open(rulesPath, "wb") as file:
                file.write(response.content)
            print("File downloaded successfully!")
        else:
            print("Failed to download the file.")