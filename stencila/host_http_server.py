import json
import logging
import os
import six
from six.moves import socketserver
from io import BytesIO, StringIO
import re
import threading
import traceback
import mimetypes

from werkzeug.wrappers import Request, Response
from werkzeug.serving import ThreadedWSGIServer


class HostHttpServer(object):

    def __init__(self, host, address='127.0.0.1', port=2000):
        self._host = host
        self._address = address
        self._port = port
        self._server = None

    @property
    def url(self):
        """
        Get the URL for this server
        """
        return 'http://%s:%s' % (self._address, self._port) if self._server else None

    def start(self, real=True):
        """
        Start the server
        """
        # Setup a logger for Werkzeug (which prevents it from printing to stdout)
        logger = logging.getLogger('werkzeug')
        log_path = os.path.join(self._host._home, 'logs', 'py-host-http-server.log')
        if not os.path.exists(os.path.dirname(log_path)):
            os.makedirs(os.path.dirname(log_path))
        handler = logging.FileHandler(log_path)
        handler.setLevel(logging.WARNING)
        formatter = logging.Formatter('%(asctime)s|%(levelname)s|%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # This shouldn't be necessary but if you don't do it, occaisionally
        # the statup message goes to stdout
        import werkzeug
        werkzeug._internal._logger = logger

        # Find an available port and serve on it
        if real:
            while self._port < 65535:
                try:
                    self._server = ThreadedWSGIServer(
                        self._address, self._port, self
                    )
                except socketserver.socket.error as exc: # pragma: no cover
                    if exc.args[0] == 98:
                        self._port += 10
                    else:
                        raise
                else:
                    thread = threading.Thread(target=self._server.serve_forever)
                    thread.daemon = True
                    thread.start()
                    break
        return self

    def stop(self, real=True):
        """
        Stop the server
        """
        if self._server:
            self._server.shutdown()
            self._server = None
        return self

    def __call__(self, environ, start_response):
        """
        Handle a HTTP request

        This is the WSGI application interface.
        It does conversion of JSON request data into method args and
        method output back into a JSON response
        """
        request = Request(environ)
        method_args = self.route(request.method, request.path)
        method = method_args[0]
        args = method_args[1:]

        try:
            response = method(request, *args)
        except Exception:
            stream = StringIO() if six.PY3 else BytesIO()
            traceback.print_exc(file=stream)
            response = Response(stream.getvalue(), status=500)

        # CORS access header added to all requests
        # See https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS
        response.headers['Access-Control-Allow-Origin'] = '*'

        return response(environ, start_response)

    def route(self, verb, path):
        """
        Route a HTTP request
        """
        if verb == 'OPTIONS':
            return (self.options,)

        if path == '/':
            return (self.home,)
        if path == '/favicon.ico':
            return (self.static, 'favicon.ico')
        if path[:8] == '/static/':
            return (self.static, path[8:])

        match = re.match(r'^/(.+?)(!(.+))?$', path)
        if match:
            id = match.group(1)
            method = match.group(3)
            if verb == 'POST' and id:
                return (self.post, id)
            if verb == 'GET' and id:
                return (self.get, id)
            elif verb == 'PUT' and id and method:
                return (self.put, id, method)
            elif verb == 'DELETE' and id:
                return (self.delete, id)

        return None

    def options(self, request):
        return Response(
            # CORS preflight headers. See https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Max-Age': '1728000'
            }
        )

    def home(self, request):
        if 'application/json' in request.headers.get('accept', ''):
            return Response(
                to_json(self._host.options()),
                mimetype='application/json'
            )
        else:
            return self.static(request, 'index.html')

    def static(self, request, path):
        static_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))
        requested_path = os.path.abspath(os.path.join(static_path, path))
        if os.path.commonprefix([static_path, requested_path]) != static_path:
            return Response(status=403)
        elif not os.path.exists(requested_path):
            return Response(status=404)
        else:
            return Response(
                open(requested_path).read(),
                mimetype=mimetypes.guess_type(path)[0]
            )

    def post(self, request, type):
        args = json.loads(request.data.decode()) if request.data else {}
        if 'name' in args:
            name = args.get('name')
            del args['name']
        else:
            name = None
        return Response(
            to_json(self._host.post(type, name, args)),
            mimetype='application/json'
        )

    def get(self, request, id):
        return Response(
            to_json(self._host.get(id)),
            mimetype='application/json'
        )

    def put(self, request, id, method):
        args = json.loads(request.data.decode()) if request.data else []
        return Response(
            to_json(self._host.put(id, method, args)),
            mimetype='application/json'
        )

    def delete(self, request, id):
        self._host.delete(id)

        return Response(
            '',
            mimetype='application/json'
        )


class JSONEncoder(json.JSONEncoder):

    def default(self, object):
        try:
            iterable = iter(object)
        except TypeError:
            pass
        else:
            return list(iterable)

        try:
            properties = object.__dict__
        except AttributeError:
            pass
        else:
            return dict((key, value) for key, value in properties.items() if not key.startswith('_'))

        return JSONEncoder.default(self, object)


def to_json(object):
    return JSONEncoder().encode(object)
