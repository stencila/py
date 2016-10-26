from os.path import dirname, abspath
import tempfile

from stencila import instance, Document

here = dirname(abspath(__file__)) + '/'


def test_new():
    d = Document()
    assert isinstance(d, Document)
    assert d.type == 'document'
    assert d in instance.components
    assert instance.open(d.address) is d


def test_convert():
    d = Document()

    d.html = 'My name is <em>HTML</em>.'
    assert d.html == 'My name is <em>HTML</em>.'
    assert d.md == 'My name is *HTML*.'

    d.md = 'My name is *Markdown*.'
    assert d.md == 'My name is *Markdown*.'
    assert d.html == '<p>My name is <em>Markdown</em>.</p>'


def test_know():
    assert Document.know(here + 'document.html')
    assert Document.know(here + 'document.md')
    assert Document.know(here + 'document.odt')
    assert Document.know(here + 'document.docx')
    assert not Document.know('document.foo')


def test_read():
    d = Document()
    assert d.read(here + 'document.html').html == '<p>Hello from <em>HTML</em>!</p>'
    assert d.read(here + 'document.md').html == '<p>Hello from <em>Markdown</em>!</p>'
    assert d.read(here + 'document.odt').html == '<p>Hello from <em>LibreOffice</em>!</p>'
    assert d.read(here + 'document.docx').html == '<p>Hello from <em>Word</em>!</p>'


def test_write():
    d = Document()
    html = '<p>Hello from <em>Stencila</em>!</p>'
    d.html = html
    for format in 'html', 'md', 'odt', 'docx':
        handle, path = tempfile.mkstemp('.' + format)
        assert d.write(path).read(path).html == html
