class ComponentConverter(object):
    """
    The base class for Component converters

    Converters are used to convert Stencila components between alternative formats.
    This base class merely defines an API for converters and provides some default
    implementations.
    """

    def load(self, doc, content, format, **options):
        raise NotImplementedError("This method must be implmented in derived class")

    def dump(self, doc, format, **options):
        raise NotImplementedError("This method must be implmented in derived class")

    def read(self, doc, path, format, **options):
        with open(path) as file:
            self.load(doc, file.read(), format, **options)

    def write(self, doc, path, format, **options):
        with open(path, 'w') as file:
            file.write(self.dump(doc, format, **options))
