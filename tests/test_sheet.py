import unittest

from stencila import Sheet, components


class ConstructTest(unittest.TestCase):

    def test(self):
        c = Sheet()
        self.assertTrue(isinstance(c, Sheet))
        self.assertTrue(c in components)

if __name__ == '__main__':
    unittest.main()
