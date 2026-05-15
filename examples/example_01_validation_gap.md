# Validation vs Execution Gap

## Scenario

A workflow is approved at t1.

At t2:
- context changes
- dependency state mutates
- rollback viability degrades

At t3:
execution proceeds using stale admissibility assumptions.

## Runtime Result

Validation passed earlier.
Execution is no longer admissible.

## Governance Failure

The system validated historical state,
not execution-time state.

## Correct Runtime Behavior

Re-evaluate admissibility at the execution boundary before commit.


