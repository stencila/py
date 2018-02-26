from .python_context import PythonContext
from .sqlite_context import SqliteContext
from .host import Host, host
from .host_http_server import HostHttpServer
from .value import type, pack, unpack


def register(*args, **kwargs):  # pragma: no cover
    """
    Register the Stencila host
    """
    host.register(*args, **kwargs)


def start(*args, **kwargs):  # pragma: no cover
    """
    Start serving the Stencila host
    """
    host.start(*args, **kwargs)


def stop(*args, **kwargs):  # pragma: no cover
    """
    Stop serving the Stencila host
    """
    host.stop(*args, **kwargs)


def run(*args, **kwargs):  # pragma: no cover
    """
    Start serving the Stencila host
    """
    host.run(*args, **kwargs)
