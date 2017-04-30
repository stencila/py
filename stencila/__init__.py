import time

from .python_context import PythonContext
from .sqlite_context import SqliteContext
from .host import Host, host
from .host_http_server import HostHttpServer
from .value import type, pack, unpack


def start():  # pragma: no cover
    """
    Start serving the Stencila host
    """
    host.start()


def stop():  # pragma: no cover
    """
    Stop serving the Stencila host
    """
    host.stop()


def run():  # pragma: no cover
    """
    Start serving the Stencila host
    """
    start()
    print('Use Ctrl+C to stop')
    while True:
        try:
            time.sleep(0x7FFFFFFF)
        except KeyboardInterrupt:
            break
