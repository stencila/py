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

from ..version import __version__


class HttpServer(object):

    def __init__(self, instance, address='127.0.0.1', port=2000):
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
        else:
            if real:
                self._server.shutdown()
                self._server = None

        return self

    def __call__(self, environ, start_response):
        """
        WSGI application interface

        Does conversion of JSON request data into method args and
        method output back into a JSON response
        """
        request = Request(environ)
        method_args = self.route(request.method, request.path)
        method = method_args[0]
        args = method_args[1:]

        def respond():
            if method in (self.web,):
                return method(request, *args)
            else:
                # TODO Restrict if not listening to localhost and/or
                # request is not from localhost
                restricted = False
                if restricted:
                    token_provided = request.args.get('token')
                    if not token_provided:
                        token_provided = request.cookies.get('token')
                    if token_provided != self._instance.token:
                        return self.web(request, 'login.html')
                try:
                    response = method(request, *args)
                except Exception:
                    stream = StringIO() if six.PY3 else BytesIO()
                    traceback.print_exc(file=stream)
                    response = Response(stream.getvalue(), status=500)

                if restricted:
                    response.set_cookie('token', self._instance.token)

                response.headers['Server'] = 'stencila-py-' + __version__

                return response

        return respond()(environ, start_response)

    def route(self, method, path):
        if path == '/favicon.ico':
            return (self.web, 'images/favicon.ico')
        if path[:5] == '/web/':
            return (self.web, path[5:])
        match = re.match(r'^/(.+?)?!(.+)$', path)
        if match:
            address = match.group(1)
            name = match.group(2)
            if method == 'GET':
                return (self.get, address, name)
            elif method == 'PUT':
                return (self.set, address, name)
            elif method == 'POST':
                return (self.call, address, name)
        address = path[1:]
        if address == '':
            address = None
        return (self.show, address)

    def web(self, request, path):
        url = 'http://127.0.0.1:9000/web/' + path
        return Response(status=302, headers=[('Location', url)])

    def show(self, request, address):
        component = self._instance.open(address)
        if 'application/json' in request.headers.get('accept'):
            content = component.show('json')
            mimetype = 'application/json'
        else:
            content = component.show('html')
            mimetype = 'text/html'
        return Response(content, mimetype=mimetype)

    def get(self, request, address, name):
        obj = self._instance.open(address)
        result = getattr(obj, name)
        return Response(json.dumps(result), mimetype='application/json')

    def set(self, request, address, name):
        if request.data:
            obj = self._instance.open(address)
            value = json.loads(request.data.decode())
            setattr(obj, name, value)
        return Response('', mimetype='application/json')

    def call(self, request, address, name):
        obj = self._instance.open(address)
        method = getattr(obj, name)
        if request.data:
            args = json.loads(request.data.decode())
            if type(args) is list:
                result = method(*args)
            elif type(args) is dict:
                result = method(**args)
            else:
                result = method(args)
        else:
            result = method()
        if isinstance(result, Component):
            content = result.dump('json')
        else:
            content = json.dumps(result)
        return Response(content, mimetype='application/json')
