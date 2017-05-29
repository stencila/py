from .python_context import PythonContext
from .sqlite_context import SqliteContext
from .host import Host, host
from .host_http_server import HostHttpServer
from .value import type, pack, unpack


def install():  # pragma: no cover
    """
    Install the Stencila host
    """
    host.install()


def environ():  # pragma: no cover
    """
    Display the Stencila host's environment
    """
    import json
    print(json.dumps(host.environ()))


def start(address='127.0.0.1', port=2000):  # pragma: no cover
    """
    Start serving the Stencila host
    """
    host.start(address, port)


def stop():  # pragma: no cover
    """
    Stop serving the Stencila host
    """
    host.stop()


def run(address='127.0.0.1', port=2000):  # pragma: no cover
    """
    Start serving the Stencila host
    """
    host.run(address, port)
