import json
import logging
import os
from six.moves import socketserver
from io import BytesIO
import re
import threading
import traceback

from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule, BaseConverter
from werkzeug.serving import ThreadedWSGIServer


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


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
        '''
        WSGI application interface

        Does conversion of JSON request data into method args and
        method output back into a JSON response
        '''
        request = Request(environ)

        restricted = self.restricted(request)
        set_token = False
        if restricted:
            token_required = self._instance.token
            token_given = request.args.get('token')
            if not token_given:
                token_given = request.cookies.get('token')
            if token_given != token_required:
                response = self.authenticate(request)
                return response(environ, start_response)
            else:
                set_token = True

        try:
            method, args = self.dispatch(request.path)
            response = method(request, *args)
        except Exception:
            stream = BytesIO()
            traceback.print_exc(file=stream)
            response = Response(stream.getvalue(), status=500)

        if set_token:
            response.set_cookie('token', token_required)
        return response(environ, start_response)

    def restricted(self, request):
        if request.path[:5] == '/web/':
            return False
        return True

    def authenticate(self, request):
        return self.respond(
            self._instance.page(),
            mimetype='text/html'
        )

    call_re = re.compile(r'^/(.+?)!(.+)$')

    def dispatch(self, path):
        if path == '/':
            return self.home, []
        if path == '/manifest':
            return self.manifest, []
        if path == '/favicon.ico':
            return self.favicon, []
        if path[:5] == '/web/':
            return self.web, [path[5:]]
        if path[:5] == '/new/':
            return self.new, [path[5:]]

        match = self.call_re.match(path)
        if match:
            return self.call, list(match.groups())

        return self.page, [path[1:]]

    def home(self, request):
        return self.respond(
            self._instance.page(),
            mimetype='text/html'
        )

    def manifest(self, request):
        return self.respond(
            self._instance.manifest()
        )

    def favicon(self, request):
        return self.respond('')

    def web(self, request, path):
        if 1:
            return self.respond(
                status=302,
                # TODO only do this if in development - config option
                headers=[('Location', 'http://127.0.0.1:9000/web/' + path)]
            )

    def new(self, request, type):
        component = self._instance.new(type)
        return self.respond(
            status=302,
            headers=[('Location', '/' + self._instance.shorten(component.address()))]
        )

    def page(self, request, address):
        component = self._instance.open(address)
        return self.respond(
            component.page(),
            mimetype='text/html'
        )

    def call(self, request, address, method):
        component = self._instance.open(address)
        bound_method = getattr(component, method)
        if request.data:
            kwargs = json.loads(request.data.decode('utf-8'))
        else:
            kwargs = {}
        return self.respond(
            bound_method(**kwargs),
            mimetype='text/html'
        )

    def respond(self, data={}, status=200, headers=[], mimetype='application/json'):
        if mimetype == 'application/json' and type(data) != str:
            content = json.dumps(data)
        else:
            content = data
        return Response(content, status=status, headers=headers, mimetype=mimetype)
