#!/usr/bin/env python3
"""
DecisionAssure – Governance Trace Demo (Main Engine)

Demonstrates:
- Hidden commitment propagation
- Authority reconstruction delay
- Rollback survivability decay
- Amplification speed vs governance repair speed
- Pre‑bound governance conditions

Run: python governance_trace_demo.py
Output: Terminal summary + governance_trace_demo.json (replayable trace)
"""

import json
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from enum import Enum


class OrchestrationPhase(Enum):
    INTENT = "intent"
    AUTHORIZATION = "authorization"
    EXECUTION = "execution"
    COMMIT = "commit"


class CommitDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"


@dataclass
class GovernanceState:
    """Runtime governance state evolving across orchestration steps."""
    phase: OrchestrationPhase = OrchestrationPhase.INTENT
    admissibility_score: float = 1.0          # 0.0 → 1.0
    authority_valid: bool = True
    rollback_viable: bool = True
    hidden_commitment_formed: bool = False
    authority_reconstruction_started: bool = False
    reconstruction_time_remaining: float = 0.0
    amplification_factor: float = 1.0
    transition_log: List[Dict] = field(default_factory=list)

    def record(self, event: str, details: Dict = None):
        self.transition_log.append({
            "timestamp": time.time(),
            "phase": self.phase.value,
            "event": event,
            "admissibility": self.admissibility_score,
            "authority_valid": self.authority_valid,
            "rollback_viable": self.rollback_viable,
            "hidden_commitment": self.hidden_commitment_formed,
            "reconstruction_time_left": self.reconstruction_time_remaining,
            "details": details or {}
        })

    def degrade_admissibility(self, amount: float, reason: str):
        self.admissibility_score = max(0.0, self.admissibility_score - amount)
        self.record("admissibility_degraded", {"amount": amount, "reason": reason})

    def trigger_authority_drift(self, reason: str):
        self.authority_valid = False
        self.record("authority_drift", {"reason": reason})
        self.authority_reconstruction_started = True
        self.reconstruction_time_remaining = 2.0
        self.record("reconstruction_started", {"duration": self.reconstruction_time_remaining})

    def tick_reconstruction(self, delta_time: float = 0.5):
        if self.authority_reconstruction_started and self.reconstruction_time_remaining > 0:
            self.reconstruction_time_remaining -= delta_time
            if self.reconstruction_time_remaining <= 0:
                self.authority_valid = True
                self.authority_reconstruction_started = False
                self.record("authority_reconstructed", {})


class PreBoundGovernanceEngine:
    """Evaluates each step against pre‑bound rules, tracks amplification vs repair."""
    def __init__(self, amplification_factor: float = 1.2, repair_rate: float = 0.8):
        self.amplification_factor = amplification_factor
        self.repair_rate = repair_rate
        self.global_trace = []

    def evaluate_step(self, state: GovernanceState, step_context: Dict) -> Tuple[bool, str, float]:
        # Rule 1: Hidden commitment blocks future steps
        if state.hidden_commitment_formed and state.phase != OrchestrationPhase.INTENT:
            return False, "Hidden commitment blocks continuation", 0.0

        # Rule 2: Authority invalid and reconstruction incomplete
        if not state.authority_valid and state.reconstruction_time_remaining > 0:
            if self.amplification_factor > self.repair_rate:
                return False, f"Authority reconstruction in progress ({state.reconstruction_time_remaining:.1f}s) – amplification > repair", 0.1
            else:
                return False, "Authority invalid, awaiting reconstruction", 0.0

        # Rule 3: Hidden commitment formation (assume_approval flag)
        if step_context.get("assume_approval", False) and state.phase == OrchestrationPhase.AUTHORIZATION:
            state.hidden_commitment_formed = True
            state.record("hidden_commitment_formed", {"source": "assume_approval"})
            return True, "Hidden commitment formed (but not yet blocked)", 0.15

        # Rule 4: Policy drift in execution phase
        if state.phase == OrchestrationPhase.EXECUTION and step_context.get("policy_version_changed", False):
            state.trigger_authority_drift("Policy version changed mid‑flight")
            state.degrade_admissibility(0.25, "Policy drift during execution")
            self.amplification_factor += 0.1
            return True, "Authority drift triggered, reconstruction started", 0.1

        # Rule 5: Irreversible effect reduces rollback viability
        if state.phase == OrchestrationPhase.EXECUTION and step_context.get("irreversible_effect", False):
            state.rollback_viable = False
            state.record("rollback_collapsed", {"reason": "irreversible effect"})
            state.degrade_admissibility(0.3, "Irreversible commitment formed")

        # Rule 6: Normal degradation after each allowed step
        degradation = 0.05
        return True, "Step allowed", degradation

    def run_orchestration(self, scenario_name: str, steps: List[Dict]) -> Dict:
        state = GovernanceState()
        state.amplification_factor = self.amplification_factor
        state.record("orchestration_start", {"scenario": scenario_name})

        for i, step in enumerate(steps):
            state.phase = step["phase"]
            step_context = step.get("context", {})
            state.tick_reconstruction(delta_time=0.5)

            allowed, reason, degradation = self.evaluate_step(state, step_context)
            if not allowed:
                state.record("step_blocked", {"step_index": i, "reason": reason})
                break

            if degradation > 0:
                state.degrade_admissibility(degradation, reason)

            if not state.authority_valid and state.reconstruction_time_remaining > 0:
                extra_degradation = 0.05 * (self.amplification_factor - self.repair_rate)
                if extra_degradation > 0:
                    state.degrade_admissibility(min(extra_degradation, 0.2),
                                                "Amplification exceeds governance repair")

            state.record("step_completed", {"step_index": i, "outcome": "allowed"})

        # Final commit decision
        state.phase = OrchestrationPhase.COMMIT
        if state.admissibility_score < 0.3:
            decision = CommitDecision.DENY
        elif not state.authority_valid:
            decision = CommitDecision.ESCALATE
        elif state.hidden_commitment_formed:
            decision = CommitDecision.DENY
        else:
            decision = CommitDecision.ALLOW
        state.record("final_commit", {"decision": decision.value})

        trace = {
            "scenario": scenario_name,
            "final_admissibility": state.admissibility_score,
            "final_authority_valid": state.authority_valid,
            "final_rollback_viable": state.rollback_viable,
            "hidden_commitment_formed": state.hidden_commitment_formed,
            "commit_decision": decision.value,
            "amplification_factor_at_end": state.amplification_factor,
            "transition_log": state.transition_log
        }
        self.global_trace.append(trace)
        return trace

    def export_json(self, filename="governance_trace_demo.json"):
        with open(filename, "w") as f:
            json.dump(self.global_trace, f, indent=2, default=str)
        print(f"\n✅ Forensic trace saved to {filename}")


def main():
    print("=" * 70)
    print("DECISIONASSURE – Governance Trace Demo")
    print("Concepts: amplification vs repair, hidden commitment, authority reconstruction")
    print("=" * 70)

    engine = PreBoundGovernanceEngine(amplification_factor=1.2, repair_rate=0.8)

    # Scenario 1: Normal workflow
    steps_normal = [
        {"phase": OrchestrationPhase.INTENT, "context": {}},
        {"phase": OrchestrationPhase.AUTHORIZATION, "context": {}},
        {"phase": OrchestrationPhase.EXECUTION, "context": {"irreversible_effect": False}},
    ]
    trace1 = engine.run_orchestration("Normal workflow", steps_normal)
    print(f"\n🔹 Normal workflow – commit decision: {trace1['commit_decision']}")

    # Scenario 2: Hidden commitment
    steps_hidden = [
        {"phase": OrchestrationPhase.INTENT, "context": {}},
        {"phase": OrchestrationPhase.AUTHORIZATION, "context": {"assume_approval": True}},
        {"phase": OrchestrationPhase.EXECUTION, "context": {}},
    ]
    trace2 = engine.run_orchestration("Hidden commitment", steps_hidden)
    print(f"🔹 Hidden commitment – commit decision: {trace2['commit_decision']}")

    # Scenario 3: Authority drift
    steps_drift = [
        {"phase": OrchestrationPhase.INTENT, "context": {}},
        {"phase": OrchestrationPhase.AUTHORIZATION, "context": {}},
        {"phase": OrchestrationPhase.EXECUTION, "context": {"policy_version_changed": True}},
    ]
    trace3 = engine.run_orchestration("Authority drift", steps_drift)
    print(f"🔹 Authority drift – commit decision: {trace3['commit_decision']}")

    # Scenario 4: Amplification exceeds repair
    steps_amplify = [
        {"phase": OrchestrationPhase.INTENT, "context": {}},
        {"phase": OrchestrationPhase.AUTHORIZATION, "context": {"assume_approval": True}},
        {"phase": OrchestrationPhase.EXECUTION, "context": {"policy_version_changed": True}},
        {"phase": OrchestrationPhase.EXECUTION, "context": {"irreversible_effect": True}},
    ]
    trace4 = engine.run_orchestration("Amplification > repair", steps_amplify)
    print(f"🔹 Amplification > repair – commit decision: {trace4['commit_decision']}")

    engine.export_json()

    print("\n" + "=" * 70)
    print("Key insight: When amplification speed exceeds governance repair speed,")
    print("authority reconstruction cannot keep up – default outcome is governance collapse.")
    print("=" * 70)


if __name__ == "__main__":
    random.seed(42)
    main()
