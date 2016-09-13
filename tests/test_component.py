import unittest
import tempfile
import os

from stencila import Component, components


class ConstructTest(unittest.TestCase):

    def test(self):
        c = Component()
        self.assertTrue(isinstance(c, Component))
        self.assertTrue(c in components)


class ReadWritePathTest(unittest.TestCase):

    def test_normal(self):
        p1 = tempfile.mkstemp()[1]
        p2 = tempfile.mkstemp()[1]

        c = Component(p1)
        self.assertEqual(c.path(), p1)

        c.read()
        self.assertEqual(c.path(), p1)

        c.read(p2)
        self.assertEqual(c.path(), p2)

        c.write()
        self.assertEqual(c.path(), p2)

        c.write(p1)
        self.assertEqual(c.path(), p1)

    def test_read_error(self):
        c = Component('foo/bar')  # This is OK

        with self.assertRaises(Exception):
            c.read()  # This explicit read is not OK

    def test_write_nonexistant(self):
        dir = os.path.join(tempfile.mkdtemp(), 'foo')

        file = os.path.join(dir, 'bar', 'boop.txt')
        c = Component(file)
        self.assertTrue(c.path(), file)
        c.write()
        self.assertTrue(os.path.exists(os.path.join(dir, 'bar')))
        self.assertTrue(not os.path.exists(file))

        dir2 = os.path.join(dir, 'bee')
        c.write(dir2)
        self.assertTrue(os.path.exists(dir2))
        self.assertEqual(c.path(), dir2)


if __name__ == '__main__':
    unittest.main()
