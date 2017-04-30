import time

from .value import type, pack, unpack
from .python_context import PythonContext
from .host import Host, host


def start():
    """
    Start serving the Stencila host
    """
    host.start()


def stop():
    """
    Stop serving the Stencila host
    """
    host.stop()


def run():
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
