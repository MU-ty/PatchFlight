import unittest
from calc import add

class Oracle(unittest.TestCase):
    def test_cases(self):
        for a, b, expected in [(2, 3, 5), (-4, 9, 5), (0, 0, 0), (7, -10, -3)]:
            self.assertEqual(add(a, b), expected)

if __name__ == "__main__":
    unittest.main()
