import unittest
from search import contains

class Oracle(unittest.TestCase):
    def test_cases(self):
        for values, target, expected in [([], 1, False), ([1], 1, True), ([1, 2, 3], 3, True), ([1, 2], 5, False), ([2, 2], 2, True)]:
            self.assertEqual(contains(values, target), expected)

if __name__ == "__main__":
    unittest.main()
