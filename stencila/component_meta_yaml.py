from collections import OrderedDict

from .helpers import yaml_ as yaml


class ComponentMetaYaml(object):
    """
    Generates a YAML header to be inserted component files e.g RMarkdown

    Currently, generates YAML fields using the Pandoc format for YAML metadata
    http://pandoc.org/MANUAL.html#extension-yaml_metadata_block
    """

    def load(self, component, meta):
        """
        Load a component's meta-data from YAML

        Uses the descriptor setters defined for the component class
        """
        data = yaml.load(meta)

        component.title = data.get('title')
        component.authors = data.get('author')

    def dump(self, component):
        """
        Dump a component's meta-data to YAML

        Uses the descriptor getters defined for the component class
        """
        data = OrderedDict()

        if component.title:
            data['title'] = component.title

        authors = component.authors
        if authors and len(authors):
            authors_data = []
            for author in authors:
                author_data = OrderedDict()
                for field in ('name', 'orcid', 'affiliation'):
                    if field in author:
                        author_data[field] = author[field]
                authors_data.append(author_data)
            data['author'] = authors_data

        return yaml.dump(data)
