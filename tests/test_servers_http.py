from stencila import session
from stencila.servers.http import HttpServer


def test_http():
    s = HttpServer(session)
    assert s.serve(real=False) == 'http://127.0.0.1:2000'
