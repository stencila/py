import os
import re

from stencila import instance, Instance


def test_instance():
    assert isinstance(instance, Instance)


def test_config():
    os.environ['STENCILA_STARTUP_SERVE'] = 'false'
    instance = Instance()
    assert instance._config['startup']['serve'] == False


def test_serve():
    url = instance.serve(real=False)
    assert re.match(r'http://127\.0\.0\.1:2\d\d\d', url)

