import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

import pyaml
import sys
if sys.version_info.major > 2: unicode = str


def load(string):
    return yaml.load(string, Loader=Loader)


def dump(data):
    return pyaml.dump(data, dst=unicode)


def read(path):
    with open(path) as stream:
        return load(stream)


def write(path, data):
    with open(path, 'w') as stream:
        stream.write(dump(data))
