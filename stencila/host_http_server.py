import json
import logging
import os
import six
from six.moves import socketserver
from io import BytesIO, StringIO
import random
import re
import string
import threading
import traceback
import mimetypes

from werkzeug.wrappers import Request, Response
from werkzeug.serving import BaseWSGIServer


class HostHttpServer(object):
    """
    A HTTP server for a Host

    Provides access to a ``Host`` via a REST-like HTTP protocol using ``POST`` to
    create new instance and ``PUT`` to run one of it's methods. Implements authorization
    using single-, or multi-, use "tickets" and session tokens.

    The following example illustrates creating a ``PythonContext`` and then
    running it's ``execute`` method. It uses the ``http`` command line tool (https://httpie.org/)
    for brevity and session management but you could also use ``curl`` or other
    HTTP client.

    .. code-block:: bash

        # Start the server
        > python -m stencila
        Host has started at: http://127.0.0.1:2000/?ticket=w8Z0ZkuWlz8Y
        Use Ctrl+C to stop

        # Then in another shell create a new PythonContext (using the above ticket
        # to obtain access authorization and a session token) using POST
        > http --session=/tmp/session.json  POST :2000/PythonContext?ticket=w8Z0ZkuWlz8Y
        HTTP/1.0 200 OK
        Content-Length: 21
        Content-Type: application/json
        Date: Wed, 28 Feb 2018 21:36:37 GMT
        Server: Werkzeug/0.12.2 Python/2.7.12
        Set-Cookie: token=PjvskQ38vtuJQg2hNYEHwPppvw8RKbs0AaYcA9uStannZkGfRr3I0g9jyeQD3L3f; Path=/

        "pythonContext1"

        # Then use the returned name of the PythonContext instance to run it's "execute" method
        # using PUT
        > http --session=/tmp/session.json  PUT :2000/pythonContext1!execute code='sys.version'
        HTTP/1.0 200 OK
        Content-Length: 153
        Content-Type: application/json
        Date: Wed, 28 Feb 2018 21:39:54 GMT
        Server: Werkzeug/0.12.2 Python/2.7.12

        {
            "messages": [],
            "value": {
                "data": "2.7.12 (default, Nov 20 2017, 18:23:56) [GCC 5.4.0 20160609]",
                "type": "string"
            }
        }

    """

    def __init__(self, host, address='127.0.0.1', port=2000):
        self._host = host
        self._address = address
        self._port = port
        self._server = None

    @property
    def url(self):
        """
        Get the URL of the server

        :returns: A URL string
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
        The WSGI application interface.
        """
        request = Request(environ)
        response = self.handle(request)
        return response(environ, start_response)

    def handle(self, request):
        """
        Handle a HTTP request
        """
        response = Response()
        try:
            # Check authorization
            authorized = False
            if not self._host.key:
                authorized = True
            else:
                auth_header = request.headers.get('Authorization')
                if auth_header:
                    match = re.match(r'^Bearer (.+)', auth_header)
                    if match:
                        token = match.group(1)
                        try:
                            self._host.authorize_token(token)
                        except Exception as exc:
                            return self.error403(request, response, str(exc))
                        else:
                            authorized = True

            # Add CORS headers used to control access by browsers. In particular, CORS
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
                    match = re.match(r'^((127\.0\.0\.1)|(localhost)|(([^.]+\.)?stenci\.la))$', host)
                    if not match:
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

            if request.method == 'OPTIONS':
                # For preflighted CORS OPTIONS requests return an empty response with headers set
                # (https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS#Preflighted_requests)
                return response
            else:
                # Route request to a method
                endpoint = self.route(request.method, request.path, authorized)
                if not endpoint:
                    return self.error400()

                method_name = endpoint[0]
                method_args = endpoint[1:]
                method = getattr(self, method_name)
                response = method(request, response, *method_args)
                return response
        except Exception as exc:
            return self.error500(request, response)

    def route(self, verb, path, authorized=False):
        """
        Route a HTTP request
        """
        if path == '/':
            return ('static', 'index.html')
        if path[:8] == '/static/':
            return ('static', path[8:])
        if path == '/manifest':
            return ('run', 'manifest')

        if not authorized: return ('error401', path)

        if path[:9] == '/environ/':
            if verb == 'POST':
                return ('run', 'startup', path[9:])
            if verb == 'DELETE':
                return ('run', 'shutdown', path[9:])

        match = re.match(r'^/(.+?)(!(.+))?$', path)
        if match:
            id = match.group(1)
            method = match.group(3)
            if verb == 'POST' and id:
                return ('run', 'create', id)
            if verb == 'GET' and id:
                return ('run', 'get', id)
            elif verb == 'PUT' and id and method:
                return ('run', 'call', id, method)
            elif verb == 'DELETE' and id:
                return ('run', 'delete', id)

        return None

    def static(self, request, response, path):
        """
        Handle a GET request for a static file
        """
        static_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))
        requested_path = os.path.abspath(os.path.join(static_path, path))
        if os.path.commonprefix([static_path, requested_path]) != static_path:
            return self.error403(request, response)
        elif not os.path.exists(requested_path):
            return self.error404(request, response)
        else:
            response.set_data(open(requested_path).read())
            response.headers['Content-Type'] = mimetypes.guess_type(path)[0]
            return response

    def run(self, request, response, method, *args):
        """
        Run a host method
        """
        args = list(args)
        if request.data:
            arg = json.loads(request.data.decode())
            args.append(arg)
        result = getattr(self._host, method)(*args)
        data = to_json(result)

        response.set_data(data)
        response.headers['Content-Type'] = 'application/json'
        return response

    def error(self, request, response, code, name, what = ''):
        response.status_code = code
        response.set_data('%s: %s' % (name, what))
        response.headers['Content-Type'] = 'text/plain'
        return response

    def error400(self, request, response, what = ''):
        return self.error(request, response, 400, 'Bad request', what)

    def error401(self, request, response, what = ''):
        return self.error(request, response, 401, 'Unauthorized', what)

    def error403(self, request, response, what = ''):
        return self.error(request, response, 403, 'Forbidden', what)

    def error404(self, request, response, what = ''):
        return self.error(request, response, 404, 'Not found', what)

    def error500(self, request, response):
        stream = StringIO() if six.PY3 else BytesIO()
        traceback.print_exc(file=stream)
        trace = stream.getvalue()
        return self.error(request, response, 500, 'Internal error', trace)


class JSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for Python object
    """

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
