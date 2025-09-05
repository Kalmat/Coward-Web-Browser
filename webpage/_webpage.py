import os
import subprocess
import time

from PyQt6.QtCore import QSize
from PyQt6.QtWebEngineCore import QWebEnginePage
from streamlink import Streamlink

import utils
from dialog import DialogsManager
from settings import DefaultSettings


class WebPage(QWebEnginePage):

    def __init__(self, profile, parent, mediaErrorSignal=None):
        super(WebPage, self).__init__(profile, parent)

        self.mediaError = mediaErrorSignal
        self.playerProcess = None

        self._debugInfoEnabled = False
        self._logToFile = False
        self._logFile = "pagelog.txt"
        self._logFileOpen = False

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
        s_path = utils.resource_path(os.path.join('externalplayer', 'streamlink', 'bin', 'streamlink.exe'), use_dist_folder="dist")
        p_path = utils.resource_path(os.path.join('externalplayer', 'mpv', 'mpv.exe'), use_dist_folder="dist")

        if os.path.exists(s_path) and os.path.exists(p_path):
            cmd = s_path + ' --player ' + p_path + ' %s 1080p,1080p60,720p,720p60,best' % self.url().toString()
            if self.playerProcess is not None and self.playerProcess.poll() is None:
                utils.kill_process(self.playerProcess.pid)
            self.playerProcess = subprocess.Popen(cmd, shell=True)
        # ISSUE: how to pack it all? within pyinstaller (is it allowed by authors)? Downloaded by user?
        # Solution: use streamlink python module, but don't know how to play the stream in MPV player or QMediaPlayer
        # session = Streamlink()
        # session.set_option("player", p_path)
        # plugin_name, plugin_class, resolved_url = session.resolve_url(self.url().toString())
        # plugin = plugin_class(session, resolved_url, options={"plugin-option": 123})
        # streams = plugin.streams()
        # stream = streams["best"]
        # # fd = streams["best"].open()

    def closeExternalPlayer(self):
        # closeEvent doesn't seem to be called at page level (???)
        if self.playerProcess is not None and self.playerProcess.poll() is None:
            utils.kill_process(self.playerProcess.pid)


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