# DecisionAssure Trace Operational Envelope

This envelope contains the metadata required to operationalise governance. It is **not** produced by DecisionAssure. It must be attached by the institution that owns the agent or workflow.

## Mandatory Fields

| Field | Description | Example |
|-------|-------------|---------|
| `owner_id` | Person or team accountable for the agent’s behaviour in production. | `"team-ai-governance@example.com"` or `"jane.doe@company.com"` |
| `escalation_contact` | Who to notify (pager, email, Slack) when a `DENY` occurs. | `"pagerduty:ai-governance-escalation"` |
| `incident_ticket_reference` | Link to ticketing system for tracking remediation. | `"https://jira.company.com/browse/INC-12345"` |
| `retention_policy` | How long to keep the trace. | `"7 years (EU AI Act requirement)"` |
| `remediation_workflow` | Pointer to runbook or automation that handles post‑denial actions. | `"https://wiki.company.com/ai-governance/remediation"` |

## Optional Fields (Recommended)

- `review_interval_days`: Frequency of manual review for high‑risk agents.
- `signing_key_id`: If cryptographic signatures are used, the key ID for trace validation.
- `risk_classification`: e.g., `"HIGH"`, `"MEDIUM"`, `"LOW"` based on the agent’s function.

## Example Envelope (JSON)

```json
{
  "owner_id": "team-ai-platform@example.com",
  "escalation_contact": "pagerduty:ai-governance-critical",
  "incident_ticket_reference": "https://jira.example.com/browse/AI-9876",
  "retention_policy": "7 years",
  "remediation_workflow": "runbook: reauthorize_and_rollback",
  "signing_key_id": "kms/arn:aws:kms:us-east-1:123456789012:key/abc123",
  "risk_classification": "HIGH"
}
How to Use

Before deploying an agent, create an operational envelope with all mandatory fields filled.
Store the envelope alongside the DecisionAssure trace (e.g., as a sibling .meta.json file or embedded in a wrapper object).
When a DENY occurs, the governance system retrieves the envelope to know who to notify, where to escalate, and which remediation workflow to trigger.
Legal Note

The operational envelope does not transfer liability. It ensures that accountability is clearly assigned, which is a prerequisite for any governance framework to be considered operational.

DecisionAssure is a verifier. The operational envelope enables the institution to act on the verifier’s output.