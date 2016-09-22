import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


def load(string):
    return yaml.load(string, Loader=Loader)


def dump(data):
    return yaml.dump(data, Dumper=Dumper)


def read(path):
    with open(path) as stream:
        return load(stream)


def write(path, data):
    with open(path, 'w') as stream:
        stream.write(dump(data))
