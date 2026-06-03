# Getting Started with DecisionAssure Runtime Governance

## What is DecisionAssure?

DecisionAssure is a runtime governance trace engine that produces deterministic, replayable traces for multi-step orchestration workflows. It helps operators, auditors, and researchers analyze governance decisions across execution stages such as intent, authorization, execution, and commit. By generating verifiable traces and supporting independent replay, DecisionAssure makes it easier to detect governance failures such as hidden commitments, authority drift, rollback survivability collapse, and commit-boundary violations.

## Prerequisites

Before getting started, ensure you have:

* Python 3.9 or later
* Git installed
* A terminal (PowerShell, Command Prompt, Bash, etc.)

Clone the repository:

```bash
git clone https://github.com/a1k7/DecisionAssure-Runtime-Governance.git
```

Navigate to the runtime folder:

```bash
cd DecisionAssure-Runtime-Governance/runtime
```

## Generate a Sample Trace

Run the self-contained survivability demo:

```bash
python survivability_gradient_demo_selfcontained.py
```
```text
selfcontained_survivability_trace.json
```

Expected output:
```text
Saved selfcontained_survivability_trace.json
Trace includes canonical inputs. Ready for independent verification.
```
## Verify the Generated Trace

After generating the trace, run:

```bash
python verify_trace_selfcontained.py selfcontained_survivability_trace.json
```

Expected output:

```text
Verifying 6 steps...

Step 1: PASS
Step 2: PASS
Step 3: PASS
Step 4: PASS
Step 5: PASS
Step 6: PASS

All hash checks passed. Trace is replayable and canonical.
```
## More Examples

Additional examples are available in the `examples/` folder, including:

- Governance trace demonstrations
- Aviation release examples
- Validation gap scenarios
- Runtime drift scenarios
- Rollback collapse scenarios
- Commit eligibility examples

## Next Steps

After successfully generating and verifying a trace, explore the examples folder and review the runtime scripts to better understand governance admissibility, replay integrity, survivability analysis, and execution-boundary verification in DecisionAssure.