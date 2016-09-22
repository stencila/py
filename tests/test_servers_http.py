from stencila import instance
from stencila.servers.http import HttpServer


def test_http():
    s = HttpServer(instance)
    assert s.serve(real=False) == 'http://127.0.0.1:2000'
