# DecisionAssure – Runtime Governance Trace Engine

**Replayable, deterministic traces for execution-bound governance.**

DecisionAssure tracks multi-step orchestrations (intent → authorisation → execution → commit) and exposes hidden failures:  
- **Hidden commitment formation** (approval assumes authority not yet granted)  
- **Authority drift** (policy or context changes mid‑flight)  
- **Rollback survivability decay** (irreversible commitments)  
- **Commit‑assumption mismatches** (reviewer ignored, execution proceeds)

Output is a **replayable JSON trace** that operators, auditors, and regulators can inspect after the fact – no observability gaps.

## Quick start

```bash
git clone https://github.com/a1k7/DecisionAssure-Runtime-Governance.git
cd DecisionAssure-Runtime-Governance/examples
python governance_trace_demo.py


Original Research Context & Attribution

DecisionAssure is a runtime governance research project focused on admissibility enforcement, authority-state validation, replay integrity, rollback survivability, and commit-boundary supervision for high-consequence orchestration systems.

Parts of the project’s terminology, transition framing, orchestration survivability modeling, and architectural direction evolved through technical dialogue around runtime timing coherence, interval-state supervision, and orchestration degradation concepts explored within the RedLINE framework developed by Ashley Lenderman.

DecisionAssure and RedLINE differ in primary focus:

RedLINE focuses on runtime timing coherence, interval-layer structural analysis, and temporal degradation detection across orchestration systems.
DecisionAssure focuses on governance admissibility, execution-boundary supervision, replay-aware escalation, rollback survivability enforcement, and deterministic continuation control under degraded orchestration states.
DecisionAssure’s implementation and admissibility framework are being developed within this broader dialogue context, with primary emphasis on governance admissibility rather than timing coherence.

Core Focus

DecisionAssure explores:

runtime authority degradation
execution-boundary supervision
commit-eligibility enforcement
replay-aware escalation
rollback survivability enforcement
evidentiary reconstruction
fail-closed orchestration governance
The framework focuses specifically on:

governance admissibility states
execution authorization continuity
continuation-boundary evaluation
replay integrity under degraded orchestration
rollback viability enforcement
commit-path supervision
reconstruction-safe execution transitions
Runtime Transition Example

FULLY_ADMISSIBLE -> OBSERVABLE_BUT_INADMISSIBLE -> CONTINUE_WITH_ESCALATION -> COMMIT_INELIGIBLE -> FAIL_CLOSED

Core Principle

Validation at t1 does not guarantee admissibility at t2.

DecisionAssure models how orchestration systems may remain operational while progressively losing governability, replay reliability, rollback survivability, or commit eligibility.

The objective is not simply determining whether execution can continue, but whether execution can continue without losing:

governance integrity
attribution continuity
replayability
reconstruction integrity
or admissible authority state
Research Status

DecisionAssure is currently an early-stage research and prototyping initiative exploring deterministic runtime governance for asynchronous orchestration systems, autonomous agents, and high-consequence execution environments.


---

## 📁 Which files to add to your repo for Fort Signal

From your existing files, add **only the clean, executable versions** (not PDFs). Here’s what to include:

| File type | Which file to add | Where to place |
|-----------|------------------|----------------|
| **Main trace engine** | Use the code from `tdt_public_demo.py` (extract the `.py` from the PDF) – or better, use the `governance_trace_martin.py` from earlier | `examples/governance_trace_demo.py` |
| **Aviation demo** | Extract `.py` from `operational_trace_demo.pdf` | `examples/aviation_flight_release.py` |
| **TDT public trace** | Use the JSON output from `tdt_public_trace.json` (already correct) | `outputs/tdt_public_trace.json` |
| **Sample output** | You can also add `operational_trace_aviation.json` from the aviation run | `outputs/aviation_trace.json` |

**Do NOT add**:
- Any PDF files (especially multi‑page PDFs of code) – they look unprofessional and are not executable.
- The `tdt_public_trace2.pdf` – it’s garbled.
- The `tdt_public_demo-2.pdf` – same issue.

---

## 🚀 Action items before sending to Fort Signal

1. **Update `README.md`** on GitHub with the appended content above.
2. **Create `examples/` and `outputs/` folders** in your repo.
3. **Add the `.py` files** (converted from PDFs or copied from previous conversations).
4. **Add the `.json` trace files** to `outputs/`.
5. **Commit and push**.

