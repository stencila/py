import tempfile

from stencila.helpers.pandoc import pandoc


def test_convert():
    c = pandoc.convert
    assert c('Hello', 'md', 'html') == '<p>Hello</p>\n'
    assert c('<p>Hello</p>', 'html', 'md') == 'Hello\n'
