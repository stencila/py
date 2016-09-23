import json
import logging
import os
import six
from six.moves import socketserver
from io import BytesIO, StringIO
import re
import threading
import traceback

from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule, BaseConverter
from werkzeug.serving import ThreadedWSGIServer


class HttpServer:

    def __init__(self, instance, address='127.0.0.1', port=None):
        self._instance = instance
        self._address = address
        self._port = port
        self._server = None

    @property
    def origin(self):
        """
        Get the origin URL for this server (scheme + address + port)
        """
        return 'http://%s:%s' % (self._address, self._port)

    @property
    def status(self):
        return 'on' if self._server else 'off'

    def serve(self, on=True, real=True):
        if on:
            # Setup a logger for werkzeug (which prevents it from printing to stdout)
            logs = self._instance.logs
            logger = logging.getLogger('werkzeug')
            handler = logging.FileHandler(os.path.join(logs, 'py-http-server.log'))
            handler.setLevel(logging.WARNING)
            formatter = logging.Formatter('%(asctime)s|%(levelname)s|%(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            # This shouldn't be necessary but if you don't do it, occaisionally
            # the statup message goes to stdout
            import werkzeug
            werkzeug._internal._logger = logger

            # Find an available port and serve on it
            self._port = 2000
            if real:
                while self._port < 65535:
                    try:
                        self._server = ThreadedWSGIServer(
                            self._address, self._port, self
                        )
                    except socketserver.socket.error as exc:
                        if exc.args[0] == 98:
                            self._port += 10
                        else:
                            raise
                    else:
                        thread = threading.Thread(target=self._server.serve_forever)
                        thread.daemon = True
                        thread.start()
                        break

            return self.origin
        else:
            if real:
                self._server.shutdown()
                self._server = None

    def __call__(self, environ, start_response):
        """
        WSGI application interface

        Does conversion of JSON request data into method args and
        method output back into a JSON response
        """
        request = Request(environ)
        method, args = self.dispatch(request.path)

        def respond():
            if method == self.web:
                return method(request, *args)
            else:
                token_required = self._instance.token
                token_provided = request.args.get('token')
                if not token_provided:
                    token_provided = request.cookies.get('token')
                if token_provided != token_required:
                    return Response(self._instance.login(), status=403)
                try:
                    response = method(request, *args)
                except Exception:
                    stream = StringIO() if six.PY3 else BytesIO()
                    traceback.print_exc(file=stream)
                    response = Response(stream.getvalue(), status=500)

                response.set_cookie('token', token_required)
                return response

        return respond()(environ, start_response)

    instance_call_re = re.compile(r'^/!(.+)$')
    component_call_re = re.compile(r'^/(.+?)!(.+)$')

    def dispatch(self, path):
        if path == '/favicon.ico':
            return self.web, ['images/favicon.ico']
        if path[:5] == '/web/':
            return self.web, [path[5:]]

        if path == '/':
            return self.get, [None]

        match = self.instance_call_re.match(path)
        if match:
            return self.call, [None, match.group(1)]

        if path[:5] == '/new/':
            return self.new, [path[5:]]

        match = self.component_call_re.match(path)
        if match:
            return self.call, list(match.groups())

        return self.get, [path[1:]]

    def web(self, request, path):
        url = 'http://127.0.0.1:9000/web/' + path
        return Response(status=302, headers=[('Location', url)])

    def new(self, request, type):
        url = '/' + self._instance.shorten(
            self._instance.new(type).address
        )
        return Response('', status=302, headers=[('Location', url)])

    def get(self, request, address):
        content = self._instance.get(address, 'html')
        return Response(content, mimetype='text/html')

    def call(self, request, address, method):
        if request.data:
            args = json.loads(request.data.decode('utf-8'))
        else:
            args = {}
        result = self._instance.call(address, method, args)
        content = json.dumps(result)
        return Response(content, mimetype='application/json')
