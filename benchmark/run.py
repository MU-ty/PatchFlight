"""Deterministic harness regression benchmark, not a model capability benchmark."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from patchflight import execute, run_test

CASES = {
    'addition': ('Fix add so it returns the sum.', 'calc.py', 'def add(a, b):\n    return a + b\n'),
    'boundary': ('Fix contains so it checks every element.', 'search.py', 'def contains(values, target):\n    for value in values:\n        if value == target:\n            return True\n    return False\n'),
    'normalization': ('Fix normalize_name to strip whitespace and lowercase.', 'text.py', 'def normalize_name(name):\n    return name.strip().lower()\n'),
}


def oracle(root, case):
    # Oracle is outside the writable workspace and loaded by absolute path.
    oracle_path = Path(__file__).resolve().parent / 'oracles' / (case + '.py')
    env = os.environ.copy()
    env['PYTHONPATH'] = str(root)
    try:
        result = subprocess.run([sys.executable, str(oracle_path)], cwd=root, env=env,
                                capture_output=True, text=True, timeout=20)
        # The oracle files define unittest cases; the explicit runner below discovers them.
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def run_case(name, model_factory=None):
    task, path, fixed = CASES[name]
    fixture = ROOT / 'benchmark' / 'fixtures' / name
    actions = [{'action': 'read', 'path': path}, {'action': 'write', 'path': path, 'content': fixed},
               {'action': 'test'}, {'action': 'finish', 'summary': 'scripted repair'}]
    responses = iter(actions)
    model = model_factory(name) if model_factory else lambda _: json.dumps(next(responses))
    with tempfile.TemporaryDirectory(prefix='patchflight-bench-') as tmp:
        baseline = run_test(fixture, 20)
        trace = Path(tmp) / 'trace.jsonl'
        start = time.perf_counter()
        try:
            result = execute(fixture, task, trace, model, evaluator=lambda root: oracle(root, name))
            error = None
        except Exception as exc:
            result = {'status': 'error', 'evaluation': False}
            error = f'{type(exc).__name__}: {exc}'
        elapsed = time.perf_counter() - start
        events = [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
        tool_events = [e for e in events if e['kind'] == 'tool_result']
        errors = sum('error' in e['result'] or (e['action'] == 'test' and e['result'].get('exit_code') == 124) for e in tool_events)
        return {'fixture': name, 'baseline_failed': baseline['exit_code'] not in (0, 124),
                'harness_status': result['status'], 'oracle_passed': result.get('evaluation') is True,
                'success': baseline['exit_code'] not in (0, 124) and result['status'] == 'passed' and result.get('evaluation') is True,
                'tool_errors': errors, 'steps': sum(e['kind'] == 'model_response' for e in events),
                'latency_seconds': round(elapsed, 6), 'token_usage': None, 'error': error}


def benchmark():
    cases = [run_case(name) for name in CASES]
    return {'schema_version': 1, 'model': 'deterministic scripted responses',
            'token_usage_note': 'Unavailable: scripted model has no provider usage; no estimate is made.',
            'summary': {'successes': sum(c['success'] for c in cases), 'total': len(cases),
                        'tool_errors': sum(c['tool_errors'] for c in cases)}, 'cases': cases}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, help='write JSON report to this path')
    args = parser.parse_args()
    report = benchmark()
    data = json.dumps(report, indent=2) + '\n'
    print(data, end='')
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data, encoding='utf8')
    return 0 if all(c['success'] for c in report['cases']) else 1

if __name__ == '__main__':
    sys.exit(main())
