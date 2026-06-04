# DecisionAssure Failure → Business Risk Mapping

This document provides a template for mapping technical continuity failures to enterprise risk categories and regulatory obligations. Institutions should adapt this mapping to their specific risk framework.

## Failure Classes and Risk Categories

| Failure Class / Reason | Risk Category | Example Business Impact | Regulatory Reference |
|------------------------|---------------|------------------------|----------------------|
| `EVIDENCE_EXPIRED` (evidence_fresh = false) | Regulatory exposure, invalid consent | Execution based on stale approval may violate data protection or financial regulations. | EU AI Act Art. 14 (Human oversight), Art. 10 (Data governance); GDPR Art. 7 (Consent) |
| `REFERENCE_FRAME_CHANGED` (policy_version, delegation_chain, or external_state changed) | Unauthorised policy drift, delegation break | Agent acts under outdated or unauthorised rules, leading to compliance breach or financial loss. | ISO 42001 Clause 6.1 (Actions to address risks); NIST AI RMF (Govern, Map) |
| `HIDDEN_COMMITMENT` (hidden_commitment = true) | Unauthorised reuse of approval | Prior approval is reused for a different action or scope, bypassing governance. | EU AI Act Art. 14(2) – human oversight to prevent automation bias |
| `ROLLBACK_VIABLE = false` | Irreversible action, financial or operational loss | System commits a change that cannot be undone (e.g., fund transfer, data deletion). | SOX (financial controls); SOC2 (change management) |
| `DELEGATION_CHAIN_CHANGED` | Authority lineage broken | Delegation chain altered without reauthorisation, creating accountability gap. | NIST AI RMF (Manage function – accountability) |
| `POLICY_VERSION_CHANGED` | Policy continuity failure | Agent continues using old policy version after policy update, leading to non‑compliance. | ISO 42001 Clause 9.1 (Monitoring, measurement, analysis) |
| `CONTINUITY_BROKEN` (generic) | Operational disruption | Agent’s legitimacy cannot be proven; execution blocked. | Enterprise risk appetite – availability and reliability |

## How to Use This Mapping

1. When a DecisionAssure trace returns a `DENY` with a specific `reason` or `control_objective_id`, look up the corresponding risk category.
2. Use the “Example Business Impact” to populate incident reports and risk registers.
3. Reference the “Regulatory Reference” when preparing compliance evidence for auditors.

## Example: Trace with `EVIDENCE_EXPIRED`

```json
{
  "decision": "DENY",
  "reason": "evidence_fresh = false",
  "control_objective_id": "CO-002"
}


Business narrative:
The agent attempted to execute using an approval that had expired (e.g., KYC token older than 3600 seconds). This could lead to unauthorised processing of personal data, violating GDPR Article 7 (consent freshness) and EU AI Act human oversight requirements.

Recommended action:
Reauthorisation with fresh evidence. Log the denial as a control failure in the GRC system.

Next Steps

Customise this mapping to your organisation’s risk taxonomy (e.g., financial, privacy, operational, compliance).
Integrate the mapping into your incident response playbooks.
For each trace denial, generate a compliance artifact linking the control_objective_id to a specific policy clause.
Note: DecisionAssure provides the technical evidence. The mapping to business risk and regulatory obligations is the responsibility of the institution using the trace.