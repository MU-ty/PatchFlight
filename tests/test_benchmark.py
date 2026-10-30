import json
import unittest
from pathlib import Path

from benchmark.run import CASES, ROOT, benchmark, run_case


class BenchmarkTests(unittest.TestCase):
    def test_repeatable_results_and_pristine_fixtures(self):
        files = sorted((ROOT / 'benchmark' / 'fixtures').rglob('*.py'))
        before = {p: p.read_bytes() for p in files}
        first, second = benchmark(), benchmark()
        self.assertEqual(first['summary'], {'successes': 3, 'total': 3, 'tool_errors': 0})
        for a, b in zip(first['cases'], second['cases']):
            for result in (a, b):
                self.assertTrue(result['baseline_failed'])
                self.assertTrue(result['oracle_passed'])
                self.assertEqual(result['steps'], 4)
                self.assertIsNone(result['token_usage'])
                self.assertGreaterEqual(result['latency_seconds'], 0)
            self.assertEqual({k: v for k, v in a.items() if k != 'latency_seconds'},
                             {k: v for k, v in b.items() if k != 'latency_seconds'})
        self.assertEqual(before, {p: p.read_bytes() for p in files})

    def test_oracle_rejects_overfit_patch(self):
        actions = iter([{'action': 'write', 'path': 'calc.py', 'content': 'def add(a,b): return 5\n'},
                        {'action': 'test'}, {'action': 'finish'}])
        result = run_case('addition', lambda _: lambda messages: json.dumps(next(actions)))
        self.assertEqual(result['harness_status'], 'passed')
        self.assertFalse(result['oracle_passed'])
        self.assertFalse(result['success'])

    def test_tool_error_and_exhaustion_are_reported(self):
        actions = iter([{'action': 'read', 'path': '../escape'}] * 8)
        result = run_case('boundary', lambda _: lambda messages: json.dumps(next(actions)))
        self.assertFalse(result['success'])
        self.assertEqual(result['harness_status'], 'exhausted')
        self.assertEqual(result['steps'], 8)
        self.assertEqual(result['tool_errors'], 8)

if __name__ == '__main__':
    unittest.main()
