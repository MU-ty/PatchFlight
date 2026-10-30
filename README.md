# PatchFlight ✈️

**A coding agent with a flight recorder.** Give it a repository and a repair task; it works in a disposable copy, records each decision and test result, and returns a patch for human review. An exhausted run is still inspectable rather than disappearing behind a final answer.

## Quick start

Requires Python 3.10+ and an OpenAI-compatible chat-completions endpoint. No third-party packages.

```bash
export API_KEY='...'
export MODEL='your-model-name'
# Optional: export BASE_URL='https://your-provider/v1'
python patchflight.py run fixtures/buggy 'Fix add so it returns the sum' --trace /tmp/flight.jsonl
python patchflight.py replay /tmp/flight.jsonl
python -m unittest discover -s tests -v
```

The original repository is never modified. A successful run emits a unified diff in its output and trace; inspect it before applying manually. Trace files contain model output, source snippets and patches: treat them as sensitive.

## How it works

1. Copy the repository into a temporary workspace and give the model a file inventory.
2. The model returns JSON actions: `read`, `write`, `test`, or `finish`. The harness executes each and returns the result to the model.
3. A final answer is accepted only after a file change and a passing unittest run following the most recent edit.
4. JSONL events preserve model responses, tool results, test output, and final patch. Replay works even after a failed run.

## Scope and limitations

This is a small prototype, not a security sandbox. Tests execute arbitrary repository code with the current user's privileges and network access. Use only trusted repositories in an isolated environment. The path checks constrain the provided file tools, not code executed by tests; copying a repository does not isolate secrets or system resources. Test discovery currently targets `python -m unittest discover -s tests`; projects requiring dependencies or other test commands need adaptation. Model responses must be strict JSON. No claims of real-model success rates are made: tests use deterministic scripted model responses. There is no crash recovery, parallel execution, or production-grade context compaction.

## Design notes

The harness separates model decisions from deterministic tool execution. The test gate is an explicit state transition: editing invalidates the previous passing result. Recording both actions and observations makes failures inspectable, though replay does not re-execute them. A useful next step is a benchmark across independently authored bug fixtures, with success, tool errors, steps, latency and token usage reported separately.


## Deterministic regression benchmark

```bash
python benchmark/run.py --output /tmp/patchflight-benchmark.json
python -m unittest discover -s tests -v
```

The benchmark runs three small, independent Python bugs (addition, final-element search, and name normalization). Each fixture starts with a failing visible unittest and runs in a fresh disposable workspace. The scripted model supplies a known repair, runs the visible tests, and finishes. A separate oracle outside that workspace checks additional cases; success requires the baseline test to fail, the harness to pass, and the oracle to pass. The oracle is not presented in the agent's workspace, but these fixtures and scripts are public, so this is not a blinded model evaluation. Test commands execute trusted code with your privileges; this is not a security sandbox.

The JSON report includes per-case and aggregate successes and tool errors. `steps` counts model responses (including finish); `tool_errors` counts tool results containing an error and test timeouts, but an ordinary nonzero test result is an observation, not a tool error. `latency_seconds` is measured wall time for the scripted harness run and external oracle, excluding the initial baseline check; it varies by machine and does not represent model API latency. `token_usage` is `null` because the script uses no model provider, and the current real-model adapter does not retain provider usage; it is not zero and is not estimated. A nonzero exit status means at least one case failed.

These results verify a small end-to-end harness workflow, not real-model repair success, generalization, cost, or production reliability. A real-model benchmark needs provider-reported token usage, repeatable model/configuration metadata, more independently sourced tasks, and separately reported runs and failures. The scripts embed the solutions; their success rate must never be presented as a model success rate.
