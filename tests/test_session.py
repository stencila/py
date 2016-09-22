import os
import re

from stencila import session, Session


def test_instance():
    assert isinstance(session, Session)


def test_config():
    os.environ['STENCILA_STARTUP_SERVE'] = 'false'
    session = Session()
    assert session._config['startup']['serve'] == False


def test_serve():
    url = session.serve(real=False)
    assert re.match(r'http://127\.0\.0\.1:2\d\d\d', url)

