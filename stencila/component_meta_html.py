
class ComponentMetaHtml(object):
    """
    Generates elements to be inserted into the ``<head>`` of a HTML
    page for a component.

    A list of ``<meta>`` tags is available at https://wiki.whatwg.org/wiki/MetaExtensions.
    Currently we use standard ones like ``description`` and ``author`` as well as those
    used by Google Scholar e.g. ``citation_autor`` https://scholar.google.com/intl/en/scholar/inclusion.html#indexing.
    """

    def dump(self, component):
        html = '<title>%s</title>\n' % component.title if component.title else 'Untitled'
        html += '<meta name="address" content="%s">' % component.address
        if component.description:
            html += '<meta name="description" content="%s">\n' % component.description
        if component.keywords:
            html += '<meta name="keywords" content="%s">\n' % ', '.join(component.keywords)
        if component.authors:
            html += ''.join(['<meta name="author" content="%s">\n' % author['name'] for author in component.authors])
            html += ''.join(['<meta name="citation_author" content="%s">\n' % author['name'] for author in component.authors])
        if component.date:
            html += '<meta name="citation_publication_date" content="%s">\n' % component.date
        return html
