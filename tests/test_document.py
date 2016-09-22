from stencila import session, Document


def test_new():
    d = Document()
    assert isinstance(d, Document)
    assert d in session.components


def test_read_file():
    d = Document()
    assert d.read('./tests/test_document_1.html').content('html') == '<p>Hello world!</p>\n'
    assert d.read('./tests/test_document_2.md').content('html') == '<p>Hello <em>world</em>!</p>\n'


def test_page():
    d = Document('./tests/test_document_1.html')
    d.page()
