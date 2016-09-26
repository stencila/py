from stencila.component_meta_yaml import ComponentMetaYaml


class Mock:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_dump():
    c = Mock(
        title='Title',
        authors=[
            dict(name='Peter Pan'),
            dict(name='Captain Hook')
        ]
    )

    assert ComponentMetaYaml().dump(c) == '''title: Title
author:
  - name: 'Peter Pan'
  - name: 'Captain Hook'
'''
