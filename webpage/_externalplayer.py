from PyQt6.QtCore import pyqtSignal, pyqtSlot, QObject

from mediaplayer import Streamer, QtMediaPlayer
from settings import DefaultSettings


class ExternalPlayer(QObject):

    _bufferingStartedSig = pyqtSignal(str)
    _streamStartedSig = pyqtSignal(str)
    _streamErrorSig = pyqtSignal(str, str)
    _streamClosedSig = pyqtSignal(bool, str)
    _playerClosedSig = pyqtSignal(str)

    def __init__(self, page, dialog_manager, http_manager):
        super().__init__()

        self.page = page
        self.dialog_manager = dialog_manager
        self.http_manager = http_manager

        self.streamers = {}
        self.players = {}
        self.dialogsToDelete = {}

        self._bufferingStartedSig.connect(self.bufferingStarted)
        self._streamStartedSig.connect(self.streamStarted)
        self._streamErrorSig.connect(self.handleStreamError)
        self._streamClosedSig.connect(self.closeExternalPlayer)
        self._playerClosedSig.connect(self.externalPlayerClosed)

    def handleExternalPlayerRequest(self, url):
        message = DefaultSettings.DialogMessages.externalPlayerRequest
        self.showDialog(
            message=message,
            acceptSlot=lambda u=url: self.openInExternalPlayer(u)
        )

    def openInExternalPlayer(self, url):
        # allow (or not) multiple external player instances per page
        keys = list(self.streamers.keys())
        if any(url in key for key in keys):
            self.showDialog(
                message=DefaultSettings.StreamErrorMessages.onePlayerOnly,
                buttonOkOnly=True)
            return

        # check how to manage internal/external choice:
        if DefaultSettings.Player.externalPlayerType == DefaultSettings.Player.PlayerTypes.mpv:
            stream_thread = self.launchStream(url=self.page.url().toString(),
                                              title=self.page.title())
            stream_thread.start()

        elif DefaultSettings.Player.externalPlayerType == DefaultSettings.Player.PlayerTypes.http:
            self.http_manager.start()
            stream_thread = self.launchStream(url=self.page.url().toString(),
                                              title=self.page.title())
            stream_thread.start()

        elif DefaultSettings.Player.externalPlayerType in (DefaultSettings.Player.PlayerTypes.qt,
                                                           DefaultSettings.Player.PlayerTypes.qt_ffmpeg_Udp,
                                                           DefaultSettings.Player.PlayerTypes.qt_ffmpeg_Stdout):
            media_player = QtMediaPlayer(title=self.page.title(),
                                         url=self.page.url().toString(),
                                         player_type=DefaultSettings.Player.externalPlayerType,
                                         index=len(self.streamers),
                                         closedSig=self._playerClosedSig)

            stream_thread = self.launchStream(url=self.page.url().toString(),
                                              title="",
                                              ffmpeg_started_sig=media_player.streamStartedSig)
            stream_thread.start()
            media_player.show()
            media_player.start()
            self.players[self.page.url().toString()] = media_player

    def launchStream(self, url, title, ffmpeg_started_sig=None):
        stream_thread = Streamer(url=url,
                                 title=title,
                                 player_type=DefaultSettings.Player.externalPlayerType,
                                 http_manager=self.http_manager,
                                 buffering_started_sig=self._bufferingStartedSig,
                                 stream_started_sig=self._streamStartedSig,
                                 stream_error_sig=self._streamErrorSig,
                                 closed_sig=self._streamClosedSig,
                                 ffmpeg_started_sig=ffmpeg_started_sig,
                                 index=len(self.streamers))
        self.streamers[url] = stream_thread
        return stream_thread

    @pyqtSlot(str)
    def bufferingStarted(self, qurl):
        dialog = self.showDialog(
            message=DefaultSettings.DialogMessages.bufferingStarted,
            buttonOkOnly=True)
        self.dialogsToDelete[qurl] = dialog

    @pyqtSlot(str)
    def streamStarted(self, qurl):
        dialog = self.dialogsToDelete.get(qurl, None)
        if dialog is not None:
            self.dialog_manager.deleteDialog(dialog)
            del self.dialogsToDelete[qurl]

    # handle streamer errors, and close external players which may remain open
    @pyqtSlot(str, str)
    def handleStreamError(self, error, qurl):
        message = DefaultSettings.DialogMessages.streamError % error
        dialog = self.showDialog(
            message=message,
            buttonOkOnly=True)
        self.streamStarted(qurl)

    # close evertything related to streaming media: streamer (if not already closed), media player and delete files
    @pyqtSlot(str)
    def externalPlayerClosed(self, qurl):
        self.closeExternalPlayer(False, qurl)

    @pyqtSlot(bool, str)
    def closeExternalPlayer(self, streamStopped, qurl):
        # close evertything related to streaming media: streamer (if not already closed), media player and delete files
        stream_thread = self.streamers.get(qurl, None)
        self.streamStarted(qurl)
        if stream_thread is not None:
            if not streamStopped:
                stream_thread.stop()
            stream_thread.quit()
            if qurl in self.streamers.keys():
                del self.streamers[qurl]
        if self.http_manager is not None:
            self.http_manager.stop()
        media_player = self.players.get(qurl, None)
        if media_player is not None:
            media_player.stop()
            media_player.close()
            if qurl in self.players.keys():
                del self.players[qurl]

    def showDialog(self, message, buttonOkOnly=False, acceptSlot=None, rejectSlot=None):
        dialog = self.dialog_manager.createDialog(
            icon=self.page.icon(),
            title=self.page.title() or self.page.url().toString(),
            message=message,
            buttonOkOnly=buttonOkOnly,
            acceptedSlot=acceptSlot,
            rejectedSlot=rejectSlot
        )
        return dialog


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