import re
import json

from stencila.host import host
from stencila.host_http_server import HostHttpServer
from stencila.value import pack

from werkzeug.wrappers import Request, Response
from werkzeug.test import Client, EnvironBuilder

import pytest


def request(**kwargs):
    return Request(EnvironBuilder(**kwargs).get_environ())


def test_start_stop():
    server = HostHttpServer(host)

    server.start()
    assert re.match('^http://127.0.0.1', server.url)

    server.stop()
    assert server.url is None


def test_handle():
    server = HostHttpServer(host)
    client = Client(server, Response)

    server.start()

    response = client.get('/')
    assert response.status == '200 OK'

    server.stop()


def test_handle_authorization():
    server = HostHttpServer(host)
    client = Client(server, Response)

    server.start()

    response = client.post('/PythonContext')
    assert response.status_code == 401

    def auth_headers (token):
        return {'Authorization': 'Bearer %s' % token}

    token1 = host.generate_token()
    response = client.post('/PythonContext', headers = auth_headers(token1))
    assert response.data.decode() == '"pythonContext1"'
    assert response.status_code == 200

    server.stop()


def test_route():
    server = HostHttpServer(host)

    assert server.route('GET', '/static/some/file.js') == ('static', 'some/file.js')

    assert server.route('POST', '/type', True) == ('run', 'create', 'type')

    assert server.route('GET', '/id', True) == ('run', 'get', 'id')

    assert server.route('PUT', '/id!method', True) == ('run', 'call', 'id', 'method')

    assert server.route('DELETE', '/id', True) == ('run', 'delete', 'id')


def test_static():
    server = HostHttpServer(host)
    req = request()
    res = Response()

    res = server.static(req, res, 'logo-name-beta.svg')
    assert res.status == '200 OK'
    assert res.headers['content-type'] == 'image/svg+xml'
    assert res.data.decode()[:54] == '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'

    res = server.static(req, res, 'foo.bar')
    assert res.status == '404 NOT FOUND'

    res = server.static(req, res, '../DESCRIPTION')
    assert res.status == '403 FORBIDDEN'


def test_run():
    server = HostHttpServer(host)
    req = request()
    res = Response()

    # Create a context
    res = server.run(req, res, 'create', 'PythonContext')
    assert res.status == '200 OK'
    assert res.headers['content-type'] == 'application/json'

    id = json.loads(res.data.decode())

    # Get the context
    res = server.run(req, res, 'get', id)
    assert res.status == '200 OK'
    assert res.headers['content-type'] == 'application/json'
    assert res.data.decode() == '{}'

    # Call a context method
    res = server.run(request(data='{"code":"6*7"}'), res, 'call', id, 'execute')
    assert res.status == '200 OK'
    assert res.headers['content-type'] == 'application/json'
    cell = json.loads(res.data.decode())
    assert cell['outputs'][0]['value']['data'] == 42

    # Delete the context
    res = server.run(req, res, 'delete', id)
    assert res.status == '200 OK'
