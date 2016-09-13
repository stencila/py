import unittest

from stencila import Context, components


class ConstructTest(unittest.TestCase):

    def test(self):
        c = Context()
        self.assertTrue(isinstance(c, Context))
        self.assertTrue(c in components)

if __name__ == '__main__':
    unittest.main()
