#!/usr/bin/env python3
"""
Prompt Injection / Memory Poisoning Test for DecisionAssure
Shows how an attacker can modify agent memory (external_reference_state)
and cause continuity break, leading to DENY.
"""

import json
import time
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Reuse the enhanced checker and agent from cascading_survivability_simulation
# For simplicity, we copy minimal classes here.

def compute_reference_frame_diff(old_ref_obj: Dict, new_ref_obj: Dict) -> Dict:
    diff = {}
    all_keys = set(old_ref_obj.keys()) | set(new_ref_obj.keys())
    for key in all_keys:
        old_val = old_ref_obj.get(key)
        new_val = new_ref_obj.get(key)
        if old_val != new_val:
            diff[key] = {"old": old_val, "new": new_val}
    return diff

CONTROL_OBJECTIVE_MAP = {
    "reference_frame_changed": {"id": "CO-001", "name": "Authority binding continuity"},
    "evidence_fresh_failure": {"id": "CO-002", "name": "Stale authority prevention"},
    "policy_version_changed": {"id": "CO-006", "name": "Policy version continuity"}
}

def get_control_objective(reason: str, diff: Dict) -> Dict:
    if "policy_version" in diff:
        return CONTROL_OBJECTIVE_MAP["policy_version_changed"]
    elif "external_reference_state" in diff:
        return CONTROL_OBJECTIVE_MAP["reference_frame_changed"]
    else:
        return {"id": "CO-000", "name": "Unclassified"}

@dataclass
class AgentState:
    agent_id: str
    session_id: str
    memory_state: Dict
    policy_version: str = "v1"
    delegation_chain: List[str] = field(default_factory=lambda: ["root"])
    external_reference_state: Dict = field(default_factory=dict)

    def get_reference_frame_object(self) -> Dict:
        return {
            "policy_version": self.policy_version,
            "delegation_chain": self.delegation_chain,
            "external_reference_state": self.external_reference_state
        }

    def compute_reference_frame_hash(self) -> str:
        return hashlib.sha256(json.dumps(self.get_reference_frame_object(), sort_keys=True).encode()).hexdigest()[:16]

    def compute_observer_identity_hash(self) -> str:
        identity = {"agent_id": self.agent_id, "session_id": self.session_id, "memory_state": self.memory_state}
        return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]

@dataclass
class LegitimacyState:
    step_name: str
    decision: str
    reason: str
    reference_frame_diff: Dict
    control_objective_id: str
    recommended_next_action: str
    timestamp: float

class SimpleChecker:
    def __init__(self):
        self.last_ref_hash = None
        self.last_ref_obj = None

    def check(self, agent: AgentState, step_name: str) -> LegitimacyState:
        current_ref_obj = agent.get_reference_frame_object()
        current_ref_hash = agent.compute_reference_frame_hash()

        if self.last_ref_hash is None:
            self.last_ref_hash = current_ref_hash
            self.last_ref_obj = current_ref_obj
            return LegitimacyState(step_name, "ADMIT", "Genesis", {}, "", "", time.time())
        else:
            if current_ref_hash != self.last_ref_hash:
                diff = compute_reference_frame_diff(self.last_ref_obj, current_ref_obj)
                control = get_control_objective("reference_frame_changed", diff)
                return LegitimacyState(step_name, "DENY", f"Continuity broken: {diff}", diff, control["id"], "escalate_to_human", time.time())
            else:
                return LegitimacyState(step_name, "ADMIT", "Continuity intact", {}, "", "", time.time())

def main():
    print("="*80)
    print("PROMPT INJECTION / MEMORY POISONING TEST")
    print("Attacker modifies external_reference_state to break continuity")
    print("="*80)

    agent = AgentState(
        agent_id="target_agent",
        session_id="safe_session",
        memory_state={"last_query": "benign"},
        policy_version="v1",
        delegation_chain=["root"],
        external_reference_state={"trusted_config": "value"}
    )

    checker = SimpleChecker()
    steps = []

    # Step 1: Authorize (genesis)
    ls1 = checker.check(agent, "authorize")
    steps.append(ls1)
    print(f"Step 1: {ls1.decision} – {ls1.reason}")

    # Step 2: Normal operation (memory read)
    agent.memory_state["last_query"] = "balance"
    ls2 = checker.check(agent, "memory_read")
    steps.append(ls2)
    print(f"Step 2: {ls2.decision} – {ls2.reason}")

    # Step 3: Attacker injects malicious content into external_reference_state
    print("\n[ATTACK] Injecting malicious payload into external_reference_state...")
    agent.external_reference_state["injected"] = "malicious_pointer"
    ls3 = checker.check(agent, "tool_call")
    steps.append(ls3)
    print(f"Step 3: {ls3.decision} – {ls3.reason}")
    if ls3.reference_frame_diff:
        print(f"  Diff: {ls3.reference_frame_diff}")
    print(f"  Control Objective: {ls3.control_objective_id}")

    # Step 4: Agent tries to commit (should be DENIED)
    ls4 = checker.check(agent, "commit")
    steps.append(ls4)
    print(f"Step 4: {ls4.decision} – {ls4.reason}")
    print(f"  Recommended next action: {ls4.recommended_next_action}")

    # Save trace
    trace = {
        "trace_id": f"prompt_injection_{int(time.time())}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenario": "Memory poisoning via external_reference_state",
        "steps": [
            {
                "step_name": s.step_name,
                "decision": s.decision,
                "reason": s.reason,
                "reference_frame_diff": s.reference_frame_diff,
                "control_objective_id": s.control_objective_id,
                "recommended_next_action": s.recommended_next_action
            } for s in steps
        ],
        "final_decision": steps[-1].decision,
        "integrity_status": "CORRUPT" if any(s.decision == "DENY" for s in steps) else "INTACT",
        "causal_continuity_persisted": not any(s.decision == "DENY" for s in steps)
    }

    with open("prompt_injection_trace.json", "w") as f:
        json.dump(trace, f, indent=2)
    print("\n✅ Saved prompt_injection_trace.json")

    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("The attacker modified external_reference_state, which changed the reference frame.")
    print("Continuity broke → DENY with control objective CO-001 (Authority binding continuity).")
    print("This shows how DecisionAssure detects memory poisoning or config tampering.")
    print("="*80)

if __name__ == "__main__":
    main()