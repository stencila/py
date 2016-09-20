import json
import SocketServer
import sys

from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule, BaseConverter
from werkzeug.exceptions import HTTPException
from werkzeug.serving import run_simple

from ..main import manifest, shorten, new, info
from ..main import open as component_open


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


class HttpServer:

    def __init__(self, port=None):
        self.port = port

    urls = Map([
        Rule('/manifest',              methods=['GET'],       endpoint='manifest'),
        Rule('/favicon.ico',              methods=['GET'],       endpoint='favicon'),
        Rule('/web/<regex(".+"):path>',    methods=['GET'],       endpoint='web'),

        Rule('/new/<regex(".+"):type>',   methods=['GET'],       endpoint='new'),
        Rule('/<regex(".+"):address>',    methods=['GET'],       endpoint='get'),
    ], converters={'regex': RegexConverter})

    def manifest(self, request):
        return self.respond(
            manifest()
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
        component = new(type)
        return self.respond(
            status=302,
            headers=[('Location', '/' + shorten(component.address()))]
        )

    def get(self, request, address):
        return self.respond(
            component_open(address).page(),
            mimetype='text/html'
        )

    def respond(self, data={}, status=200, headers=[], mimetype='application/json'):
        if mimetype == 'application/json' and type(data) != str:
            content = json.dumps(data)
        else:
            content = data
        return Response(content, status=status, headers=headers, mimetype=mimetype)

    def __call__(self, environ, start_response):
        '''
        WSGI application interface

        Does conversion of JSON request data into method args and
        method output back into a JSON response
        '''
        request = Request(environ)
        adapter = self.urls.bind_to_environ(request.environ)
        try:
            endpoint, kwargs = adapter.match(method=request.method)
            kwargs.update(request=request)
            if request.data:
                kwargs.update(args=json.loads(request.data))
            method = getattr(self, endpoint)
            response = method(**kwargs)
        except HTTPException, e:
            response = e
        return response(environ, start_response)

    def start(self, address='127.0.0.1', port=2000):
        dev = len(sys.argv) > 1 and sys.argv[1] == 'dev'
        if dev:
            print 'Running in development mode. File will reload on changes.'

        while port < 65535:
            try:
                self.port = port
                run_simple(
                    address, port, self,
                    use_debugger=dev,
                    use_reloader=dev,
                    threaded=True
                )
                info('HTTP server is serving\n port: %s' % port)
            except SocketServer.socket.error as exc:
                if exc.args[0] == 98:
                    port += 10
                else:
                    raise
            else:
                break

    def stop(self):
        raise NotImplementedError()
