import unittest

from stencila import Session, components


class ConstructTest(unittest.TestCase):

    def test(self):
        c = Session()
        self.assertTrue(isinstance(c, Session))
        self.assertTrue(c in components)

if __name__ == '__main__':
    unittest.main()
