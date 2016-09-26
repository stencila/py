import tempfile

import stencila.helpers.yaml_ as yaml


def test_dump():
    # Based on http://stackoverflow.com/q/25108581/4625911
    data = {
        'name': 'foo',
        'my_list': [
            {'foo': 'test', 'bar': 'test2'},
            {'foo': 'test3', 'bar': 'test4'}],
        'hello': 'world',
    }

    assert yaml.dump(data) == '''hello: world
my_list:
  - bar: test2
    foo: test
  - bar: test4
    foo: test3
name: foo
'''
