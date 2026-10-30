import unittest
from text import normalize_name

class Oracle(unittest.TestCase):
    def test_cases(self):
        for text, expected in [(' Alice ', 'alice'), ('  ', ''), ('BOB SMITH', 'bob smith'), (' MiXeD ', 'mixed')]:
            self.assertEqual(normalize_name(text), expected)

if __name__ == "__main__":
    unittest.main()
