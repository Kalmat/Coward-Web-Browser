import os

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWebEngineCore import QWebEnginePage

import utils
from mediaplayer import QtMediaPlayer
from settings import DefaultSettings
from mediaplayer._streamer import Streamer


class WebPage(QWebEnginePage):

    _playerClosedSig = pyqtSignal()

    def __init__(self, profile, parent, mediaErrorSignal=None):
        super(WebPage, self).__init__(profile, parent)

        self.mediaError = mediaErrorSignal
        self.stream_thread = None
        self.media_player = None

        self._playerClosedSig.connect(self.closeExternalPlayer)

        self._debugInfoEnabled = False
        self._logToFile = False
        self._logFile = "pagelog.txt"
        self._logFileOpen = False

    def accept_feature(self, origin, feature):
        self.setFeaturePermission(origin, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser)

    def reject_feature(self, origin, feature):
        self.setFeaturePermission(origin, feature, QWebEnginePage.PermissionPolicy.PermissionDeniedByUser)

    def accept_player(self):
        self.openInExternalPlayer()

    def reject_player(self):
        pass

    def javaScriptConsoleMessage(self, level, message, lineNumber=0, sourceID=""):

        if self._debugInfoEnabled:
            debugInfo = "Error Level: {} --- URL: {} --- Message: {} --- Line number: {}".format(level, sourceID, message, lineNumber)
            if self._logToFile:
                openMode = "a" if self._logFileOpen is None else "w"
                with open(self._logFile, openMode) as f:
                    self._logFileOpen = True
                    f.write(debugInfo + "\n")
            else:
                print(debugInfo)

        # if level == WebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
        #
        #     # this is totally empirical and based in just one a small number of cases
        #     # TODO: find a better way to catch and handle page errors
        #     # this is promissing but... how to access this data?
        #     # "debug_error": "{\"errorCode\":\"html5.unsupportedlive\",\"errorMessage\":\"No se admite este formato de vídeo.\",\"Ua\":\"HTML5_NO_AVAILABLE_FORMATS_FALLBACK\",\"Cx\":\"\",\"cN\":\"buildRej.1;a.1;d.1;drm.0;f18.0;c18.0;f133.1;f140.1;f242.1;cAAC.0;cAVC.0;cVP9.1;a6s.1\",\"Rl\":2,\"cpn\":\"KSAdNV_auzm2Ivhf\"}",
        #
        #     # this works for twitch, but not for YT live videos
        #     if "Player" in message and "ErrorNotSupported" in message:
        #         self.mediaError.emit(self)
        # elif level ==WebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel:
        #
        #     if "generate_204" in message:
        #         if sourceID == self.url().toString():
        #             # this works, but throws too many "false" alarms
        #             self.checkCanPlayMedia()

    def enableDebugInfo(self, enable, logging):
        # We could add the level of debugging (Info, Warning, Error...), but not for now
        self._debugInfoEnabled = enable
        self._logToFile = logging
        if not logging:
            # deactivating and activating logging again is equivalent to clear the log file
            self._logFileOpen = False

    def checkCanPlayMedia(self):
        # this detects media failures, but sometimes it sends "false" alarms (e.g. in YT videos)
        # other times it returns ok, but it is not (e.g. 2nd time and following in Twitch)
        # see example of debug data at the end of the file. How could we get this info from python/PyQt?
        # this is ASYNCHRONOUS, so can't be used to return any value. Must use a method/function to handle return
        self.runJavaScript("""
                            var mediaElements = document.querySelectorAll('video, audio');
                            var canPlay = Array.from(mediaElements).every(media => media.canPlayType(media.type) !== '');
                            canPlay;""", lambda ok: self.handleMediaError(ok)
                           )

    def handleMediaError(self, ok):
        if not ok:
            self.mediaError.emit(self)

    def openInExternalPlayer(self):

        # check how to manage internal/external choice:
        if DefaultSettings.Player.useExternalPlayer and os.path.exists(DefaultSettings.Player.externalPlayerPath):
            self.stream_thread = Streamer(url=self.url().toString(),
                                          stream_file=DefaultSettings.Player.streamTempFile,
                                          external_player=DefaultSettings.Player.externalPlayerPath
                                          )

        else:
            self.stream_thread = Streamer(url=self.url().toString(),
                                          stream_file=DefaultSettings.Player.streamTempFile,
                                          )
            self.media_player = QtMediaPlayer(stream_file=DefaultSettings.Player.streamTempFile,
                                              title=self.title(),
                                              closedSig=self._playerClosedSig)
            self.media_player.show()
            self.media_player.start()

        self.stream_thread.start()

    def closeExternalPlayer(self):
        try:
            self.stream_thread.stop()
            utils.kill_process(self.stream_thread.pid)
        except:
            pass
        if self.media_player is not None:
            self.media_player.stop()
            if self.media_player.isVisible():
                self.media_player.close()
                self.media_player.deleteLater()
            if os.path.exists(DefaultSettings.Player.streamTempFile):
                try:
                    os.remove(DefaultSettings.Player.streamTempFile)
                except:
                    pass
            self.media_player = None


"""
    {
        "ns": "yt",
        "el": "detailpage",
        "cpn": "KSAdNV_auzm2Ivhf",
        "ver": 2,
        "cmt": "0",
        "fs": "0",
        "rt": "13.429",
        "euri": "",
        "lact": 1,
        "live": "dvr",
        "cl": "800254696",
        "mos": 0,
        "state": "80",
        "volume": 100,
        "cbr": "Chrome",
        "cbrver": "130.0.0.0",
        "c": "WEB",
        "cver": "2.20250903.04.00",
        "cplayer": "UNIPLAYER",
        "cos": "Windows",
        "cosver": "10.0",
        "cplatform": "DESKTOP",
        "hl": "es_ES",
        "cr": "ES",
        "fexp": "v1,23986034,18610,695255,14625955,11684381,53408,9105,22730,2821,106030,18644,14869,47210,15124,65,13526,391,26504,3333,5919,3479,2519,10511,23206,15179,2,20220,19253,563,11782,5392,5656,2625,1904,12017,5345,700,64,4324,5396,5385,5451,553,10582,657,1724,4994,1098,4174,1059,8860,1787,2640,1721,1085,2617,5949,3927,802,1163,1115,1658,10096,3566,375,477,60,195,1011,1283,1820,326,1825,2080,796,3510",
        "muted": "0",
        "docid": "2YU6LiighmA",
        "ei": "V8i5aMWGOsDQp-oPy6rVmQ0",
        "plid": "AAY9_NFAawUWE4_Z",
        "referrer": "https://www.youtube.com/watch?v=h_Ci5lnWTb0",
        "sdetail": "rv:h_Ci5lnWTb0",
        "sourceid": "yw",
        "of": "0xrCoUZQGBZ626KaPU2tGw",
        "vm": "CAEQARgEOjJBSHFpSlRJMUQza3ZXdFR0SjZadlVXT3J4bHNzbjRXUEx2V3BnRWdhZ05VcFdPUHdId2JTQUZVQTZSUmRxRDFfQXp6UXhnYWFwWG9lbFVuVGZPVmZxRzMyTDhQb1VUN190OE5VeER6bUdMU0pUdUk5eVBfZnlLTE45bDJpMWg1RklhSG8waUE",
        "vct": "0.000",
        "vd": "NaN",
        "vpl": "",
        "vbu": "",
        "vbs": "",
        "vpa": "1",
        "vsk": "0",
        "ven": "0",
        "vpr": "1",
        "vrs": "0",
        "vns": "0",
        "vec": "null",
        "vemsg": "",
        "vvol": "1",
        "vdom": "1",
        "vsrc": "0",
        "vw": "963",
        "vh": "542",
        "dvf": 0,
        "tvf": 0,
        "debug_error": "{\"errorCode\":\"html5.unsupportedlive\",\"errorMessage\":\"No se admite este formato de vídeo.\",\"Ua\":\"HTML5_NO_AVAILABLE_FORMATS_FALLBACK\",\"Cx\":\"\",\"cN\":\"buildRej.1;a.1;d.1;drm.0;f18.0;c18.0;f133.1;f140.1;f242.1;cAAC.0;cAVC.0;cVP9.1;a6s.1\",\"Rl\":2,\"cpn\":\"KSAdNV_auzm2Ivhf\"}",
        "prerolls": "heartbeat,ad",
        "ismb": 15700000,
        "latency_class": "LOW",
        "lowlatency": "1",
        "leader": 1,
        "segduration": 2,
        "lat": 0,
        "relative_loudness": "NaN",
        "user_qual": 0,
        "release_version": "youtube.player.web_20250827_22_RC00",
        "debug_videoId": "2YU6LiighmA",
        "0sz": "false",
        "op": "",
        "yof": "true",
        "dis": "",
        "gpu": "ANGLE_(NVIDIA,_NVIDIA_GeForce_RTX_4080_(0x00002704)_Direct3D11_vs_5_0_ps_5_0,_D3D11)",
        "ps": "desktop-polymer",
        "js": "/s/player/79e70f61/player_ias.vflset/es_ES/base.js",
        "debug_playbackQuality": "unknown",
        "debug_date": "Thu Sep 04 2025 19:12:06 GMT+0200 (hora de verano de Europa central)",
        "origin": "https://www.youtube.com",
        "timestamp": 1757005926133
    }
"""