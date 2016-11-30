from .component_converter import ComponentConverter


class ComponentHtml(ComponentConverter):
    """
    A Component converter for HTML

    This is a fallback returned by ``Component.converter()`` so
    that methods like ``Component.show()`` (which may want HTML) do not error.
    """

    def load(self, component, html, format='html'):
        """
        Load a component from a html string
        """
        raise NotImplementedError()

    def dump(self, component, format='html'):
        """
        Dump a document to a HTML string
        """
        return ''
