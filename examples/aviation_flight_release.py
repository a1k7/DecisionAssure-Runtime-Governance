#!/usr/bin/env python3
"""
Operational Trace – Aviation Flight Release Approval

Shows:
- Hidden commitment formation (captain assumes approval)
- Authority drift (weather advisory invalidates clearance)
- Rollback collapse and unsafe execution

Run: python aviation_flight_release.py
Output: Terminal log + aviation_trace.json
"""

import json
import time
import random
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum


class Phase(Enum):
    INTENT = "intent"
    MAINTENANCE_CHECK = "maintenance_check"
    CAPTAIN_REVIEW = "captain_review"
    DISPATCH_APPROVAL = "dispatch_approval"
    EXECUTION = "execution"


class Decision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"


@dataclass
class State:
    phase: Phase = Phase.INTENT
    admissibility_score: float = 1.0
    authority_valid: bool = True
    hidden_commitment_formed: bool = False
    rollback_viable: bool = True
    log: List[Dict] = field(default_factory=list)

    def record(self, event: str, details: Dict = None):
        self.log.append({
            "timestamp": time.time(),
            "phase": self.phase.value,
            "event": event,
            "admissibility": self.admissibility_score,
            "authority_valid": self.authority_valid,
            "hidden_commitment": self.hidden_commitment_formed,
            "rollback_viable": self.rollback_viable,
            "details": details or {}
        })

    def degrade(self, amount: float, reason: str):
        self.admissibility_score = max(0.0, self.admissibility_score - amount)
        self.record("degradation", {"amount": amount, "reason": reason})


def run_workflow():
    state = State()
    state.record("workflow_start", {"context": "Flight UA123 release"})

    # Intent
    state.phase = Phase.INTENT
    state.record("intent_received", {"pilot": "Captain Smith"})

    # Maintenance check – all good
    state.phase = Phase.MAINTENANCE_CHECK
    state.record("maintenance_ok", {})
    state.degrade(0.02, "Normal degradation after check")

    # Captain review – hidden commitment forms (assumes dispatch will approve)
    state.phase = Phase.CAPTAIN_REVIEW
    state.hidden_commitment_formed = True
    state.record("hidden_commitment", {"source": "captain_assumed_approval"})
    state.degrade(0.03, "Hidden commitment adds risk")

    # Dispatch approval – authority drift (new weather advisory)
    state.phase = Phase.DISPATCH_APPROVAL
    state.authority_valid = False
    state.record("authority_drift", {"reason": "New weather advisory not reviewed"})
    state.degrade(0.1, "Authority drift")

    # Execution handoff – unsafe due to hidden commitment + invalid authority
    state.phase = Phase.EXECUTION
    if state.hidden_commitment_formed and not state.authority_valid:
        state.rollback_viable = False
        state.record("unsafe_execution", {"reason": "Hidden commitment + invalid authority"})
        final_decision = Decision.DENY
    else:
        final_decision = Decision.ALLOW
    state.record("final_decision", {"decision": final_decision.value})

    # Output
    print("=" * 60)
    print("OPERATIONAL TRACE – Aviation Flight Release")
    print("=" * 60)
    for entry in state.log:
        print(f"[{entry['phase']}] {entry['event']} – admissibility: {entry['admissibility']:.2f}")
    print(f"\nFinal decision: {final_decision.value}")
    print(f"Hidden commitment formed: {state.hidden_commitment_formed}")
    print(f"Authority valid at end: {state.authority_valid}")
    print(f"Rollback viable: {state.rollback_viable}")

    # Save JSON
    with open("aviation_trace.json", "w") as f:
        json.dump(state.log, f, indent=2, default=str)
    print("\n✅ Replayable JSON saved to aviation_trace.json")


if __name__ == "__main__":
    random.seed(42)
    run_workflow()
