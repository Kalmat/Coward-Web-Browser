import os

from PyQt6.QtCore import QThread
from flask import Flask, Response, url_for

from settings import DefaultSettings

app = Flask("Coward - Stream Player", template_folder=os.path.abspath("html"))
_endpointIndex = 0
_page_stream_data = {}


class HttpManager(QThread):

    def __init__(self):
        super().__init__()

        self._flaskRunning = False

    def run(self):

        if self._flaskRunning:
            return

        self._flaskRunning = True
        global app

        @app.route('/page/<path:page_name>')
        def dynamic_page(pageIndex):
            return self._stream_data(pageIndex)

        @app.route('/page/<path:page_name>')
        def dynamic_index(pageIndex):
            _, title, _ = _page_stream_data.get(str(pageIndex))
            return f"""
                <!DOCTYPE html>
                <html lang="es">
                    <head>
                        <title>{title}</title>
                    </head>
                    <body style="margin:0; background:black;">
                        <video width="100%" height="100%" controls autoplay style="position:absolute;">
                            <source src="/stream/{pageIndex}" type="video/mp4">
                            Your browser does not support the video tag.
                        </video>
                    </body>
                </html>
            """

        def has_no_empty_params(rule):
            defaults = rule.defaults if rule.defaults is not None else ()
            arguments = rule.arguments if rule.arguments is not None else ()
            return len(defaults) >= len(arguments)

        @app.route("/site-map")
        def site_map():
            list = []
            for rule in app.url_map.iter_rules():
                # Filter out rules we can't navigate to in a browser
                # and rules that require parameters
                if "GET" in rule.methods and has_no_empty_params(rule):
                    url = url_for(rule.endpoint, **(rule.defaults or {}))
                    list.append([url, rule.endpoint])
            return str(list)

        # the (not so) dynamic endpoints must be all set before running the flask app
        for i in range(100):
            pageIndex = str(i)
            app.add_url_rule(
                f'/index/{pageIndex}',
                endpoint=f'index_{pageIndex}',
                view_func=lambda index=pageIndex: dynamic_index(index)
            )
            app.add_url_rule(
                f'/stream/{pageIndex}',
                endpoint=f'stream_{pageIndex}',
                view_func=lambda index=pageIndex: dynamic_page(index)
            )

        # run flask to serve stream pages from localhost
        app.run(
            host=DefaultSettings.Player.httpServerHost,
            port=DefaultSettings.Player.httpServerPort,
            threaded=True
        )

    def setStreamData(self, stream_data, title, url):
        global _endpointIndex
        global _page_stream_data
        _page_stream_data[str(_endpointIndex)] = [stream_data, title, url]
        _endpointIndex = (_endpointIndex + 1) % 100

    def _stream_data(self, pageIndex):
        global _page_stream_data
        stream_data, title, url = _page_stream_data.get(str(pageIndex))
        return Response(stream_data, mimetype='video/mp4')

    def stop(self):
        self.quit()


# Not sure what solution is better (direct stdout or reading/writing)
# def generate():
#     try:
#         while True:
#             chunk = self.ffmpeg_process.stdout.read(1024 * 1024)  # Read in 1MB chunks
#             if not chunk:
#                 break
#             yield chunk
#
#     except Exception as e:
#         self.handleError(True)
#
# return Response(generate(), mimetype='video/mp4')
