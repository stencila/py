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

    def __init__(self, host, address='127.0.0.1', port=2000, authorization=True, tickets_reuse=True):
        self._host = host
        self._address = address
        self._port = port

        auth = os.environ.get('STENCILA_AUTH')
        if auth == 'true':
            authorization = True
        elif auth == 'false':
            authorization = False
        self._authorization = authorization

        self._server = None
        self._tickets = []
        self._tickets_reuse = tickets_reuse
        self._tokens = []

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
        # Check authorization. Note that browsers do not send credentials (e.g. cookies)
        # in OPTIONS requests
        cookie = None
        if self._authorization and request.method != 'OPTIONS':
            # Check for ticket
            ticket = request.args.get('ticket')
            if ticket:
                # Check ticket is valid
                if not self.ticket_check(ticket):
                    return Response(status=403)
                else:
                    # Set token cookie
                    cookie = 'token=%s; Path=/' % self.token_create()
            else:
                # Check for token
                token = request.cookies.get('token')
                if not token or not self.token_check(token):
                    return Response(status=403)

        # Route request to a method
        method_args = self.route(request.method, request.path)
        method = method_args[0]
        args = method_args[1:]
        if method is None:
            return Response(status=400)

        # Run method
        try:
            response = method(request, *args)
        except Exception:
            stream = StringIO() if six.PY3 else BytesIO()
            traceback.print_exc(file=stream)
            return Response(stream.getvalue(), status=500)

        # CORS used to control access by browsers. In particular, CORS
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

        # Set cookie header if necessary
        if cookie:
            response.headers['Set-Cookie'] = cookie

        return response

    def route(self, verb, path):
        """
        Route a HTTP request
        """
        if verb == 'OPTIONS':
            return (self.options,)

        if path == '/':
            return (self.static, 'index.html')
        if path[:8] == '/static/':
            return (self.static, path[8:])
        if path == '/manifest':
            return (self.run, 'manifest')

        if path[:9] == '/environ/':
            if verb == 'POST':
                return (self.run, 'startup', path[9:])
            if verb == 'DELETE':
                return (self.run, 'shutdown', path[9:])

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
        """
        Handle a OPTIONS request

        Necessary for preflighted CORS requests (https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS#Preflighted_requests)
        """
        return Response()

    def static(self, request, path):
        """
        Handle a GET request for a static file
        """
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

    def run(self, request, method, *args):
        """
        Run a host method
        """
        if request.data:
            arg = json.loads(request.data.decode())
            args.push(arg)
        result = getattr(self._host, method)(*args)
        json = to_json(result)
        return Response(json, mimetype='application/json')

    def post(self, request, type):
        """
        Handle a POST request
        """
        kwargs = json.loads(request.data.decode()) if request.data else {}
        return Response(
            to_json(self._host.post(type, kwargs)),
            mimetype='application/json'
        )

    def get(self, request, name):
        """
        Handle a GET request
        """
        return Response(
            to_json(self._host.get(name)),
            mimetype='application/json'
        )

    def put(self, request, name, method):
        """
        Handle a PUT request
        """
        kwargs = json.loads(request.data.decode()) if request.data else {}
        return Response(
            to_json(self._host.put(name, method, kwargs)),
            mimetype='application/json'
        )

    def delete(self, request, name):
        """
        Handle a DELETE request
        """
        self._host.delete(name)

        return Response(
            '',
            mimetype='application/json'
        )

    def ticket_create(self):
        """
        Create a ticket (an access token)
        """
        ticket = ''.join(random.choice(
            string.ascii_lowercase + string.ascii_uppercase + string.digits
        ) for _ in range(12))
        self._tickets.append(ticket)
        return ticket

    def ticket_check(self, ticket):
        """
        Check that a ticket is valid.

        If it is, and ``tickets_reuse = False```, then it is removed from
        the list of valid tickets
        """
        if ticket in self._tickets:
            if not self._tickets_reuse:
                self._tickets.remove(ticket)
            return True
        else:
            return False

    def ticketed_url(self):
        """
        Create a URL with a ticket query parameter so users
        can connect to this server
        """
        url = self.url
        if self._authorization:
            url += '/?ticket=' + self.ticket_create()
        return url

    def token_create(self):
        """
        Create a token (a multiple-use access token)
        """
        token = ''.join(random.choice(
            string.ascii_lowercase + string.ascii_uppercase + string.digits
        ) for _ in range(64))
        self._tokens.append(token)
        return token

    def token_check(self, token):
        """
        Check that a token is valid.
        """
        return token in self._tokens


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
