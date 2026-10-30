import unittest
from text import normalize_name

class Tests(unittest.TestCase):
    def test_case(self):
        self.assertEqual(normalize_name(' Alice '), 'alice')
