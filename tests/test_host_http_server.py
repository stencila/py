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
    s = HostHttpServer(host)

    s.start()
    assert re.match('^http://127.0.0.1', s.url)

    s.stop()
    assert s.url is None


def test_handle():
    s = HostHttpServer(host)
    c = Client(s, Response)

    s.start()

    r = c.get('/')
    assert r.status == '200 OK'

    s.stop()


def test_route():
    s = HostHttpServer(host)

    assert s.route('OPTIONS', None) == (s.options,)

    assert s.route('GET', '/static/some/file.js') == (s.static, 'some/file.js')

    assert s.route('POST', '/type') == (s.run, 'create', 'type')

    assert s.route('GET', '/id') == (s.run, 'get', 'id')

    assert s.route('PUT', '/id!method') == (s.run, 'call', 'id', 'method')

    assert s.route('DELETE', '/id') == (s.run, 'delete', 'id')


def test_options():
    s = HostHttpServer(host)

    r = s.options(request())
    assert r.status == '200 OK'


def test_static():
    s = HostHttpServer(host)

    r = s.static(request(), 'logo-name-beta.svg')
    assert r.status == '200 OK'
    assert r.headers['content-type'] == 'image/svg+xml'
    assert r.data.decode()[:54] == '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'

    r = s.static(request(), 'foo.bar')
    assert r.status == '404 NOT FOUND'

    r = s.static(request(), '../DESCRIPTION')
    assert r.status == '403 FORBIDDEN'


def test_run():
    s = HostHttpServer(host)

    # Create a context
    r = s.run(request(), 'create', 'PythonContext')
    assert r.status == '200 OK'
    assert r.headers['content-type'] == 'application/json'

    id = json.loads(r.data.decode())

    # Get the context
    r = s.run(request(), 'get', id)
    assert r.status == '200 OK'
    assert r.headers['content-type'] == 'application/json'
    assert r.data.decode() == '{}'

    # Call a context method
    r = s.run(request(data='{"code":"6*7"}'), 'call', id, 'execute')
    assert r.status == '200 OK'
    assert r.headers['content-type'] == 'application/json'
    cell = json.loads(r.data.decode())
    assert cell['outputs'][0]['value']['data'] == 42

    # Delete the context
    r = s.run(request(), 'delete', id)
    assert r.status == '200 OK'
