import unittest

from stencila import Document, components


class ConstructTest(unittest.TestCase):

    def test(self):
        c = Document()
        self.assertTrue(isinstance(c, Document))
        self.assertTrue(c in components)


if __name__ == '__main__':
    unittest.main()
