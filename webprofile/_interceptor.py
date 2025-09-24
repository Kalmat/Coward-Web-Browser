import os
import time

import requests
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo

from settings import DefaultSettings
try:
    # braveblock is only available in python 3.11 by now
    from braveblock import Adblocker
except:
    DefaultSettings.AdBlocker.enableAdBlocker = False


class RequestInterceptor(QWebEngineUrlRequestInterceptor):

    def __init__(self, blocked_urls, rulesFolder):
        super().__init__()

        # List of URLs (as strings or patterns) to block
        self.blocked_urls = blocked_urls
        self.easylistPath = os.path.join(rulesFolder, DefaultSettings.AdBlocker.easylistFile)
        self.easyprivacyPath = os.path.join(rulesFolder, DefaultSettings.AdBlocker.easyprivacytFile)

        # enable / disable adblocker
        self.enableAdBlocker = DefaultSettings.AdBlocker.enableAdBlocker

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

            # Create Adblocker instance
            self.adblocker = Adblocker(rules=list(set(easylist + easyprivacy)))

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
            should_block = self.adblocker.check_network_urls(
                url=url,
                source_url=info.initiator().url(),
                request_type=self.resourceTypes.get(info.resourceType(), ""))
            if should_block:
                info.block(True)
                # print(f"AD Blocked: {url}")

    def getRequestType(self):
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
            print("File downloaded successfully!")
        else:
            print("Failed to download the file.")
        response = requests.get(DefaultSettings.AdBlocker.easyprivacyUrl)
        if response.status_code == 200:
            with open(easyPrivacyPath, "wb") as file:
                file.write(response.content)
            print("File downloaded successfully!")
        else:
            print("Failed to download the file.")
