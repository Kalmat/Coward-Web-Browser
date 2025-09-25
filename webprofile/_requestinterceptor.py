import os
import time

import requests
from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo

from logger import LOGGER, LoggerSettings
from settings import DefaultSettings

try:
    # braveblock is only available in python 3.11 by now
    from braveblock import Adblocker
except:
    DefaultSettings.AdBlocker.enableAdBlocker = False
    LOGGER.write(LoggerSettings.LogLevels.info, "RequestInterceptor", f"Failed to load braveblock module. Python 3.11 is required to enable this feature")


class RequestInterceptor(QWebEngineUrlRequestInterceptor):

    def __init__(self, blocked_urls, rulesFolder):
        super().__init__()

        # List of URLs (as strings or patterns) to block
        self.blocked_urls = blocked_urls
        self.easylistPath = os.path.join(rulesFolder, DefaultSettings.AdBlocker.easylistFile)
        self.easyprivacyPath = os.path.join(rulesFolder, DefaultSettings.AdBlocker.easyprivacytFile)

        # enable / disable adblocker
        self.enableAdBlocker = DefaultSettings.AdBlocker.enableAdBlocker
        self.resourceTypes = {}

        if self.enableAdBlocker:

            self.resourceTypes = self.getRequestType()

            currTime = time.time()
            if (not os.path.exists(self.easylistPath) or currTime - os.path.getmtime(self.easylistPath) >= 7 * 86400
                    or not os.path.exists(self.easyprivacyPath) or currTime - os.path.getmtime(self.easyprivacyPath) >= 7 * 86400):
                self.updateRules(self.easylistPath, self.easyprivacyPath)

            # Load EasyList rules (download easylist.txt beforehand)
            with open(self.easylistPath, "r", encoding="utf-8") as f:
                easylist = f.readlines()
            with open(self.easyprivacyPath, "r", encoding="utf-8") as f:
                easyprivacy = f.readlines()

            # Create Adblocker instance (using our own downloaded rules files)
            self.adblocker = Adblocker(
                rules=list(set(easylist + easyprivacy)),
                include_easylist=False,
                include_easyprivacy=False
            )

            LOGGER.write(LoggerSettings.LogLevels.info, "RequestInterceptor",  "Finished initialization")

    def interceptRequest(self, info: QWebEngineUrlRequestInfo):
        url = info.requestUrl().url()

        # Check if the request URL is in the blocked list
        if not QUrl(url).isValid() or any(blocked in url for blocked in self.blocked_urls):
            # Block the request (redirect to about:blank? How to detect it is not the "main" url???)
            info.block(True)
            LOGGER.write(LoggerSettings.LogLevels.info, "RequestInterceptor", f"Black List Blocked: {url}")

        # check ad-block rules
        if self.enableAdBlocker:
            should_block = self.adblocker.check_network_urls(
                url=url,
                source_url=info.initiator().url(),
                request_type=self.resourceTypes.get(info.resourceType(), ""))
            if should_block:
                info.block(True)
                LOGGER.write(LoggerSettings.LogLevels.info, "RequestInterceptor",  f"AD Blocked: {url}")

    def getRequestType(self):
        """
            document: Represents a request for a document (HTML page).
            subdocument: Represents embedded pages, usually included via HTML inline frames (iframes).
            stylesheet: Represents a request for a CSS stylesheet.
            script: Represents a request for a JavaScript file.
            image: Represents a request for an image file (e.g., .jpg, .png).
            ping: Represents requests initiated via the navigator.sendBeacon() method.
            websocket: Represents requests initiated via the WebSocket object.
            xmlhttprequest: Represents requests made using the XMLHttpRequest object or fetch API.
        """
        resourceTypes = {
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame: "document",
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeSubFrame: "subdocument",
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeStylesheet: "stylesheet",
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeScript: "script",
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeImage: "image",
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypePing: "ping",
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeWebSocket: "websocket",
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeXhr: "xmlhttprequest"
        }
        return resourceTypes

    def updateRules(self, easylistPath, easyPrivacyPath):

        response = requests.get(DefaultSettings.AdBlocker.easylistUrl)
        if response.status_code == 200:
            with open(easylistPath, "wb") as file:
                file.write(response.content)
            LOGGER.write(LoggerSettings.LogLevels.info, "RequestInterceptor", "easylist updated successfully!")
        else:
            LOGGER.wirte(LoggerSettings.LogLevels.error, "RequestInterceptor", "easylist failed to download")

        response = requests.get(DefaultSettings.AdBlocker.easyprivacyUrl)
        if response.status_code == 200:
            with open(easyPrivacyPath, "wb") as file:
                file.write(response.content)
            LOGGER.write(LoggerSettings.LogLevels.info, "RequestInterceptor", "easyprivacy updated successfully!")
        else:
            LOGGER.wirte(LoggerSettings.LogLevels.error, "RequestInterceptor", "easyprivacy failed to download")
