#!/usr/bin/env python3
"""
TDT Public Sample Trace – Phrase-level drift, reviewer divergence, commit mismatch

Based on: https://tdt-saas-beta.vercel.app/sample-audit-review
Source: NetSuite user access review with missing approvals.
AI draft adds framing language ("Objective", "Scope & Methodology").

Run: python tdt_public_trace.py
Output: Terminal log + tdt_public_trace.json
"""

import json
import time
import difflib
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class CheckpointPhase(Enum):
    SOURCE_RETRIEVAL = "source_retrieval"
    AI_DRAFT_GENERATION = "ai_draft_generation"
    REVIEWER_INTERPRETATION = "reviewer_interpretation"
    APPROVAL_ISSUANCE = "approval_issuance"
    EXECUTION_HANDOFF = "execution_handoff"


class DriftSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class SourceContext:
    text: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class AIDraft:
    text: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class DriftReport:
    similarity_score: float
    added_phrases: List[str]
    missing_phrases: List[str]
    severity: DriftSeverity
    details: Dict = field(default_factory=dict)


@dataclass
class ReviewCheckpoint:
    phase: CheckpointPhase
    timestamp: float
    source: SourceContext
    draft: AIDraft
    drift_report: Optional[DriftReport]
    reviewer_notes: str
    divergence_detected: bool
    commit_assumption_made: bool
    suggested_actions: List[str]
    final_decision: str  # PASS, DRIFT_DETECTED, REQUIRES_REVIEW, MISMATCH, RECOMMEND_HALT


def detect_drift(source_text: str, draft_text: str) -> DriftReport:
    source_words = source_text.split()
    draft_words = draft_text.split()
    matcher = difflib.SequenceMatcher(None, source_words, draft_words)
    similarity = matcher.ratio()

    added = []
    missing = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'insert':
            added.append(' '.join(draft_words[j1:j2]))
        elif tag == 'delete':
            missing.append(' '.join(source_words[i1:i2]))

    severity = DriftSeverity.LOW
    if similarity < 0.7:
        severity = DriftSeverity.HIGH
    elif similarity < 0.85:
        severity = DriftSeverity.MEDIUM

    added_text = ' '.join(added).lower()
    if any(phrase in added_text for phrase in ['objective', 'scope & methodology', 'follow-up', 'ensure appropriate']):
        if severity == DriftSeverity.LOW:
            severity = DriftSeverity.MEDIUM

    return DriftReport(
        similarity_score=similarity,
        added_phrases=added[:5],
        missing_phrases=missing[:5],
        severity=severity,
        details={"source_word_count": len(source_words), "draft_word_count": len(draft_words)}
    )


def simulate_reviewer(draft_text: str, drift: DriftReport):
    if any(phrase in draft_text for phrase in ["Objective", "Scope & Methodology", "follow-up procedures"]):
        notes = (
            "The draft adds formal audit framing ('Objective', 'Scope & Methodology') that is not in the original source. "
            "It also invents follow-up procedures. While the core facts are preserved, the added language creates an impression "
            "of formal audit authority that the source does not provide. Recommend removing or flagging these additions for senior review."
        )
        divergence = True
    else:
        notes = "Draft matches source well."
        divergence = False
    return notes, divergence


def run_trace() -> List[ReviewCheckpoint]:
    checkpoints = []

    # 1. Source retrieval
    source_text = (
        "The auditor tested 40 sampled users from a population of 1,842 active NetSuite users. "
        "For 36 sampled users, access was reviewed and approved. For 3 sampled users, manager approval was not documented. "
        "For 1 sampled user, Billing Administrator access was retained without documented business justification. "
        "Management stated that missing approvals were due to manager turnover and that Billing Administrator access is being reviewed by IT and Finance. "
        "Follow-up is expected next quarter."
    )
    source = SourceContext(text=source_text, metadata={"source": "TDT public sample"})
    checkpoints.append(ReviewCheckpoint(
        phase=CheckpointPhase.SOURCE_RETRIEVAL,
        timestamp=time.time(),
        source=source,
        draft=AIDraft(text="", metadata={}),
        drift_report=None,
        reviewer_notes="Source retrieved correctly.",
        divergence_detected=False,
        commit_assumption_made=False,
        suggested_actions=[],
        final_decision="PASS"
    ))

    # 2. AI draft generation
    draft_text = (
        "Objective\n"
        "The purpose of this audit was to evaluate user access provisioning and review controls in NetSuite.\n\n"
        "Scope & Methodology\n"
        "The auditor tested 40 sampled users from a population of 1,842 active NetSuite users. Attributes tested included access review approvals, documented business justification, and manager sign-off.\n\n"
        "Results\n"
        "For 36 sampled users, access was reviewed and approved. For 3 sampled users, manager approval was not documented. For 1 sampled user, Billing Administrator access was retained without documented business justification.\n\n"
        "Management Response\n"
        "Management stated that missing approvals were due to manager turnover and that Billing Administrator access is being reviewed by IT and Finance. "
        "Audit will perform follow-up procedures next quarter to ensure appropriate documentation is retained."
    )
    draft = AIDraft(text=draft_text, metadata={"model": "gpt-4", "temperature": 0.6})
    drift = detect_drift(source_text, draft_text)
    checkpoints.append(ReviewCheckpoint(
        phase=CheckpointPhase.AI_DRAFT_GENERATION,
        timestamp=time.time() + 0.1,
        source=source,
        draft=draft,
        drift_report=drift,
        reviewer_notes="Draft generated by AI.",
        divergence_detected=False,
        commit_assumption_made=False,
        suggested_actions=["Compare against source for added phrasing"],
        final_decision="DRIFT_DETECTED"
    ))

    # 3. Reviewer interpretation
    reviewer_notes, divergence = simulate_reviewer(draft_text, drift)
    checkpoints.append(ReviewCheckpoint(
        phase=CheckpointPhase.REVIEWER_INTERPRETATION,
        timestamp=time.time() + 0.2,
        source=source,
        draft=draft,
        drift_report=drift,
        reviewer_notes=reviewer_notes,
        divergence_detected=divergence,
        commit_assumption_made=False,
        suggested_actions=["Flag added framing language", "Request removal or justification"],
        final_decision="REQUIRES_REVIEW" if divergence else "PASS"
    ))

    # 4. Approval issuance (mismatch)
    approver_notes = "Approved for reporting. The added formatting is fine for internal use."
    mismatch = divergence
    checkpoints.append(ReviewCheckpoint(
        phase=CheckpointPhase.APPROVAL_ISSUANCE,
        timestamp=time.time() + 0.3,
        source=source,
        draft=draft,
        drift_report=drift,
        reviewer_notes=approver_notes,
        divergence_detected=False,
        commit_assumption_made=True,
        suggested_actions=["Re-validate against source policy", "Require second signature"] if mismatch else [],
        final_decision="MISMATCH" if mismatch else "PASS"
    ))

    # 5. Execution handoff
    checkpoints.append(ReviewCheckpoint(
        phase=CheckpointPhase.EXECUTION_HANDOFF,
        timestamp=time.time() + 0.4,
        source=source,
        draft=draft,
        drift_report=drift,
        reviewer_notes="Handing off to audit report generator.",
        divergence_detected=False,
        commit_assumption_made=True,
        suggested_actions=["Halt until policy alignment confirmed"] if mismatch else [],
        final_decision="RECOMMEND_HALT" if mismatch else "EXECUTION_PROCEEDS"
    ))

    return checkpoints


def export_checkpoints(checkpoints: List[ReviewCheckpoint], filename="tdt_public_trace.json"):
    def serialize(cp):
        return {
            "phase": cp.phase.value,
            "timestamp": cp.timestamp,
            "source": {"text": cp.source.text, "metadata": cp.source.metadata},
            "draft": {"text": cp.draft.text, "metadata": cp.draft.metadata},
            "drift_report": {
                "similarity_score": cp.drift_report.similarity_score if cp.drift_report else None,
                "added_phrases": cp.drift_report.added_phrases if cp.drift_report else [],
                "missing_phrases": cp.drift_report.missing_phrases if cp.drift_report else [],
                "severity": cp.drift_report.severity.value if cp.drift_report else None,
                "details": cp.drift_report.details if cp.drift_report else {}
            } if cp.drift_report else None,
            "reviewer_notes": cp.reviewer_notes,
            "divergence_detected": cp.divergence_detected,
            "commit_assumption_made": cp.commit_assumption_made,
            "suggested_actions": cp.suggested_actions,
            "final_decision": cp.final_decision
        }
    data = [serialize(cp) for cp in checkpoints]
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n✅ Replayable trace saved to {filename}")


def main():
    print("=" * 70)
    print("TDT PUBLIC SAMPLE TRACE – Phrase-level drift, reviewer divergence, commit mismatch")
    print("Source: https://tdt-saas-beta.vercel.app/sample-audit-review")
    print("=" * 70)

    trace = run_trace()
    for cp in trace:
        print(f"\n[{cp.phase.value.upper()}]")
        print(f"  Decision: {cp.final_decision}")
        if cp.drift_report:
            print(f"  Drift similarity: {cp.drift_report.similarity_score:.2f}")
            print(f"  Added phrases: {cp.drift_report.added_phrases[:2]}...")
        print(f"  Divergence: {cp.divergence_detected}")
        print(f"  Assumption made: {cp.commit_assumption_made}")
        if cp.suggested_actions:
            print(f"  Suggested actions: {cp.suggested_actions}")

    export_checkpoints(trace)

    print("\n" + "=" * 70)
    print("Summary: The trace captures how added framing language creates drift,")
    print("reviewer flags it (divergence), but an approver ignores it (mismatch).")
    print("Execution handoff then proceeds on potentially invalid assumptions.")
    print("=" * 70)


if __name__ == "__main__":
    main()
