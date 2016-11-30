import json

from .component_converter import ComponentConverter


class ComponentJson(ComponentConverter):
    """
    A Component converter for JSON.
    """

    def load(self, component, json, format='json'):
        """
        Load a component from a JSON string
        """
        raise NotImplementedError()

    def dump(self, component, format='json'):
        """
        Dump a document to a HTML string
        """
        return json.dumps({
            'type': component.type,
            'id': component.id,
            'address': component.address,
            'url': component.url
        })
