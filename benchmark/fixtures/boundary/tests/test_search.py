import unittest
from search import contains

class Tests(unittest.TestCase):
    def test_last_item(self):
        self.assertTrue(contains([1, 2, 3], 3))
