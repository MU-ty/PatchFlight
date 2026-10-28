import json, tempfile, unittest
from pathlib import Path
from patchflight import execute, contained

class HarnessTests(unittest.TestCase):
    def test_repair_trace_and_source_untouched(self):
        source=Path('fixtures/buggy').resolve(); before=(source/'calc.py').read_text()
        responses=iter([{'action':'read','path':'calc.py'},{'action':'write','path':'calc.py','content':'def add(a, b):\n    return a + b\n'},{'action':'test'},{'action':'finish','summary':'fixed'}])
        with tempfile.TemporaryDirectory() as d:
            trace=Path(d)/'trace.jsonl'; result=execute(source,'Fix addition',trace,lambda _:json.dumps(next(responses)))
            events=[json.loads(x) for x in trace.read_text().splitlines()]
            self.assertEqual(result['status'],'passed'); self.assertIn('return a + b',result['patch']); self.assertEqual(before,(source/'calc.py').read_text()); self.assertEqual(events[-1]['status'],'passed')
    def test_reject_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): contained(Path(d),'../escape')
    def test_finish_requires_passing_test_after_write(self):
        actions=iter([{'action':'write','path':'calc.py','content':'broken'},{'action':'finish'}])
        with tempfile.TemporaryDirectory() as d:
            result=execute('fixtures/buggy','fix',Path(d)/'t',lambda _:json.dumps(next(actions)),steps=2)
            self.assertEqual(result['status'],'exhausted')
    def test_failed_test_cannot_finish(self):
        actions=iter([{'action':'write','path':'calc.py','content':'def add(a,b): return a-b\n'},{'action':'test'},{'action':'finish'}])
        with tempfile.TemporaryDirectory() as d:
            result=execute('fixtures/buggy','fix',Path(d)/'t',lambda _:json.dumps(next(actions)),steps=3)
            self.assertEqual(result['status'],'exhausted')
if __name__=='__main__': unittest.main()
