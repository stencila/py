class ComponentConverter(object):
    """
    The base class for Component converters

    Converters are used to convert Stencila components between alternative formats.
    This base class merely defines an API for converters and provides some default
    implementations.
    """

    def load(self, doc, content, format, **options):
        """
        Load a document from a string
        """
        raise NotImplementedError("This method must be implmented in derived class")

    def dump(self, doc, format, **options):
        """
        Dump a document to a string
        """
        raise NotImplementedError("This method must be implmented in derived class")

    def read(self, doc, path, format, **options):
        """
        Read a document from a file
        """
        with open(path) as file:
            self.load(doc, file.read(), format, **options)

    def write(self, doc, path, format, **options):
        """
        Write a document to a file
        """
        with open(path, 'w') as file:
            file.write(self.dump(doc, format, **options))
