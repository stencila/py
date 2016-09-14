from stencila import Document, components


def test():
    c = Document()
    assert isinstance(c, Document)
    assert c in components
