
# AML/KYC Runtime Drift Scenario

## Initial State

A transaction is approved after KYC verification.

State:
- KYC valid
- authority verified
- rollback available
- policy compliant

Status:
ADMISSIBLE

---

## Runtime Evolution

Before execution:

- customer profile changes
- policy updated
- rollback survivability weakens
- downstream dependency commits

---

## Governance Observation

The workflow remains operational.

However:

- authority continuity degraded
- execution context diverged
- admissibility no longer guaranteed

---

## Runtime Outcome

Decision:
COMMIT_INELIGIBLE

Reason Codes:
- EXECUTION_CONTEXT_STALE
- REVALIDATION_REQUIRED
- COMMIT_BOUNDARY_RISK

---

## Key Principle

Validation at t1 does not imply admissibility at t2.

