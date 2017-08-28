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
from werkzeug.serving import BaseWSGIServer


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
        log_path = os.path.join(self._host.temp_dir(), 'logs', 'py-host-http-server.log')
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
                    # Do not use a threaded server because (amongst possible other issues)
                    # a SQLte connection can only be used from within the same thread
                    self._server = BaseWSGIServer(
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

            # CORS headers are used to control access by browsers. In particular, CORS
            # can prevent access by XHR requests made by Javascript in third party sites.
            # See https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS

            # Get the Origin header (sent in CORS and POST requests) and fall back to Referer header
            # if it is not present (either of these should be present in most browser requests)
            origin = request.headers.get('Origin')
            if not origin and request.headers.get('Referer'):
                match = re.match(r'^https?://([\w.]+)(:\d+)?', request.headers.get('Referer'))
                if match:
                    origin = match.group(0)

            # Check that host is in whitelist
            if origin:
                match = re.match(r'^https?://([\w.]+)(:\d+)?', origin)
                if match:
                    host = match.group(1)
                    if host not in ('127.0.0.1', 'localhost', 'open.stenci.la'):
                        origin = None
                else:
                    origin = None

            # If an origin has been found and is authorized set CORS headers
            # Without these headers browser XHR request get an error like:
            #     No 'Access-Control-Allow-Origin' header is present on the requested resource.
            #     Origin 'http://evil.hackers:4000' is therefore not allowed access.
            if origin:
                # 'Simple' requests (GET and POST XHR requests)
                response.headers['Access-Control-Allow-Origin'] = origin
                # Allow sending cookies and other credentials
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                # Pre-flighted requests by OPTIONS method (made before PUT, DELETE etc
                # XHR requests and in other circumstances)
                # get additional CORS headers
                if request.method == 'OPTIONS':
                    # Allowable methods and headers
                    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
                    # "how long the response to the preflight request can be cached for without
                    # sending another preflight request"
                    response.headers['Access-Control-Max-Age'] = '86400'  # 24 hours
        except Exception:
            stream = StringIO() if six.PY3 else BytesIO()
            traceback.print_exc(file=stream)
            response = Response(stream.getvalue(), status=500)

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
        return Response()

    def home(self, request):
        if 'application/json' in request.headers.get('accept', ''):
            return Response(
                to_json(self._host.manifest()),
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
        kwargs = json.loads(request.data.decode()) if request.data else {}
        if 'name' in kwargs:
            name = kwargs.get('name')
            del kwargs['name']
        else:
            name = None
        return Response(
            to_json(self._host.post(type, name, kwargs)),
            mimetype='application/json'
        )

    def get(self, request, id):
        return Response(
            to_json(self._host.get(id)),
            mimetype='application/json'
        )

    def put(self, request, id, method):
        kwargs = json.loads(request.data.decode()) if request.data else {}
        return Response(
            to_json(self._host.put(id, method, kwargs)),
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
