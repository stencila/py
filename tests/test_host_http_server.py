import re
import json

from stencila.host import host
from stencila.host_http_server import HostHttpServer

from werkzeug.wrappers import Request, Response
from werkzeug.test import Client, EnvironBuilder

import pytest


def request(**kwargs):
    return Request(EnvironBuilder(**kwargs).get_environ())


def test_start_stop():
    s = HostHttpServer(host)
    c = Client(s, Response)

    s.start()
    assert re.match('^http://127.0.0.1', s.url)

    #r = c.get('/')
    #assert r.status == '403 FORBIDDEN'
    #assert not re.search('components', r.data.decode('utf-8')), 'is not authenticated'

    #r = c.get('/?token='+host.token)
    #assert r.status == '200 OK'
    #assert re.search('components', r.data.decode('utf-8')), 'is authenticated'

    #r = c.get('/!foo-bar')
    #assert r.status == '500 INTERNAL SERVER ERROR'
    #assert re.search('Traceback', r.data.decode('utf-8')), 'returns a traceback of error'

    s.stop()
    assert s.url is None


def test_route():
    s = HostHttpServer(host)

    assert s.route('OPTIONS', None) == (s.options,)

    assert s.route('GET', '/') == (s.home,)

    assert s.route('GET', '/static/some/file.js') == (s.static, 'some/file.js')
    assert s.route('GET', '/favicon.ico') == (s.static, 'favicon.ico')

    assert s.route('POST', '/type') == (s.post, 'type')

    assert s.route('GET', '/id') == (s.get, 'id')

    assert s.route('PUT', '/id!method') == (s.put, 'id', 'method')

    assert s.route('DELETE', '/id') == (s.delete, 'id')


def test_home():
    s = HostHttpServer(host)

    r = s.home(request(headers={'Accept': 'application/json'}))
    assert r.status == '200 OK'
    assert json.loads(r.data.decode()) == host.options()

    r = s.home(request())
    assert r.status == '200 OK'
    assert r.headers['Content-Type'] == 'text/html; charset=utf-8'

@pytest.mark.skip
def test_static():
    s = HostHttpServer(host)

    r = s.static(request(), 'logo-name-beta.svg')
    assert r.status == '200 OK'
    assert r.headers['content-type'] == 'image/svg+xml'
    assert r.data == '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'

    r = s.static(request(), 'foo.bar')
    assert r.status == '404'

    r = s.static(request(), '../DESCRIPTION')
    assert r.status == '403'


def test_post():
    s = HostHttpServer(host)

    r = s.post(request(), 'PythonContext')
    assert r.status == '200 OK'
    assert r.headers['content-type'] == 'application/json'


def test_get():
    s = HostHttpServer(host)

    r1 = s.post(request(), 'PythonContext')
    r2 = s.get(request(), json.loads(r1.data.decode()))
    assert r2.status == '200 OK'
    assert r2.headers['content-type'] == 'application/json'
    assert r2.data.decode() == '{}'


def test_put():
    s = HostHttpServer(host)

    r1 = s.post(request(), 'PythonContext')
    r2 = s.put(request(data='{"code":"6*7"}'), json.loads(r1.data.decode()), 'runCode')
    assert r2.status == '200 OK'
    assert r2.headers['content-type'] == 'application/json'
    assert json.loads(r2.data.decode())['output']['content'] == '42'
