#!/usr/bin/env python3
"""
Survivability Gradient Demo – Self‑Contained Trace with Canonical Inputs.
Produces a trace file that includes canonical inputs for independent replay.
"""

import json
import time
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# ----------------------------------------------------------------------
# Helper: Canonical JSON
# ----------------------------------------------------------------------
def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))

def compute_hash(canonical_str: str) -> str:
    return hashlib.sha256(canonical_str.encode()).hexdigest()[:16]

# ----------------------------------------------------------------------
# Agent State
# ----------------------------------------------------------------------
@dataclass
class AgentState:
    agent_id: str
    session_id: str
    current_goal: str
    memory_state: Dict = field(default_factory=dict)
    tool_permissions: List[str] = field(default_factory=list)
    policy_version: str = "v1"
    delegation_chain: List[str] = field(default_factory=list)
    external_reference_state: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def get_identity_object(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "memory_state": self.memory_state
        }

    def get_reference_frame_object(self) -> Dict:
        return {
            "policy_version": self.policy_version,
            "delegation_chain": self.delegation_chain,
            "external_reference_state": self.external_reference_state
        }

# ----------------------------------------------------------------------
# Legitimacy State (extended with canonical inputs)
# ----------------------------------------------------------------------
@dataclass
class LegitimacyState:
    step_name: str
    phase: str
    declared_intent: str
    observer_id: str
    reference_frame_hash: str
    observer_identity_hash: str
    previous_reference_frame_hash: Optional[str]
    previous_observer_identity_hash: Optional[str]
    continuity_valid: bool
    authority_valid: bool
    memory_valid: bool
    policy_valid: bool
    delegation_valid: bool
    external_state_valid: bool
    admissibility_score: float
    decision: str
    continuation_mode: str
    reason: str
    packet_id: str
    timestamp: float
    canonical_identity_input: str   # NEW
    canonical_reference_frame_input: str   # NEW

    def to_dict(self) -> Dict:
        d = self.__dict__.copy()
        d['timestamp'] = self.timestamp
        return d

# ----------------------------------------------------------------------
# Constitutional Checker (simplified for demo)
# ----------------------------------------------------------------------
class ConstitutionalChecker:
    def __init__(self):
        self.last_valid_ref_hash = None
        self.last_valid_obs_hash = None
        self.degradation_policy = {
            (True, True, True): "FULL",
            (False, True, True): "DEGRADED",
            (False, True, False): "CONSTRAINED",
            (False, False, False): "DENIED",
        }

    def _phase_for_step(self, step_name: str) -> str:
        phase_map = {
            "authorize": "authorization",
            "memory_read": "execution",
            "tool_call": "execution",
            "policy_mutation": "state_change",
            "retry": "execution",
            "final_execute": "commit",
        }
        return phase_map.get(step_name, "execution")

    def check(self, state: AgentState, step_name: str, intent: str,
              rollback_viable: bool = True, evidence_fresh: bool = True) -> LegitimacyState:
        # Compute current hashes from canonical inputs
        identity_obj = state.get_identity_object()
        ref_obj = state.get_reference_frame_object()
        canonical_identity = canonical_json(identity_obj)
        canonical_ref = canonical_json(ref_obj)
        current_obs_hash = compute_hash(canonical_identity)
        current_ref_hash = compute_hash(canonical_ref)

        # Genesis
        if self.last_valid_obs_hash is None and self.last_valid_ref_hash is None:
            continuity_valid = True
            reason = "Genesis – first transition"
            admissibility = 1.0
            decision = "ADMIT"
            mode = "FULL"
            self.last_valid_obs_hash = current_obs_hash
            self.last_valid_ref_hash = current_ref_hash
        else:
            ref_unchanged = (current_ref_hash == self.last_valid_ref_hash)
            obs_unchanged = (current_obs_hash == self.last_valid_obs_hash)
            continuity_valid = ref_unchanged and obs_unchanged

            if not continuity_valid:
                key = (continuity_valid, rollback_viable, evidence_fresh)
                mode = self.degradation_policy.get(key, "DENIED")
                if mode in ["DEGRADED", "CONSTRAINED"]:
                    decision = "ADMIT"
                    admissibility = 0.6 if mode == "DEGRADED" else 0.3
                    reason = f"Continuity broken but degradation allowed: mode={mode}"
                else:
                    decision = "DENY"
                    admissibility = 0.0
                    reason = f"Constitutional continuity broken: mode={mode}"
            else:
                decision = "ADMIT"
                admissibility = 1.0
                reason = "All validations passed; continuity intact"
                mode = "FULL"

        return LegitimacyState(
            step_name=step_name,
            phase=self._phase_for_step(step_name),
            declared_intent=intent,
            observer_id=state.agent_id,
            reference_frame_hash=current_ref_hash,
            observer_identity_hash=current_obs_hash,
            previous_reference_frame_hash=self.last_valid_ref_hash if self.last_valid_ref_hash else None,
            previous_observer_identity_hash=self.last_valid_obs_hash if self.last_valid_obs_hash else None,
            continuity_valid=continuity_valid,
            authority_valid=True,
            memory_valid=True,
            policy_valid=True,
            delegation_valid=True,
            external_state_valid=True,
            admissibility_score=admissibility,
            decision=decision,
            continuation_mode=mode,
            reason=reason,
            packet_id=f"leg_{int(time.time())}_{step_name}",
            timestamp=time.time(),
            canonical_identity_input=canonical_identity,
            canonical_reference_frame_input=canonical_ref
        )

# ----------------------------------------------------------------------
# Main simulation (produces self-contained trace)
# ----------------------------------------------------------------------
def main():
    print("="*80)
    print("SELF-CONTAINED SURVIVABILITY GRADIENT DEMO")
    print("Each step includes canonical inputs for independent verification.")
    print("="*80)

    agent = AgentState(
        agent_id="agent_alice",
        session_id="session_live",
        current_goal="Test self-contained trace",
        memory_state={"step": 0},
        tool_permissions=["read_file", "call_api"],
        policy_version="v1",
        delegation_chain=["root"],
        external_reference_state={"source": "trusted"},
    )

    checker = ConstitutionalChecker()
    legitimacy_chain = []

    # Step 1: Authorize
    print("\n[STEP 1] Authorize")
    ls1 = checker.check(agent, "authorize", "Proceed with data retrieval")
    legitimacy_chain.append(ls1)
    print(f"  Decision: {ls1.decision} | Mode: {ls1.continuation_mode}")

    # Step 2: Memory read (mutates memory_state)
    print("\n[STEP 2] Memory read")
    agent.memory_state["step"] = 1
    ls2 = checker.check(agent, "memory_read", "Read memory state")
    legitimacy_chain.append(ls2)
    print(f"  Decision: {ls2.decision} | Mode: {ls2.continuation_mode}")

    # Step 3: Policy mutation (breaks continuity)
    print("\n[STEP 3] Policy mutation")
    agent.policy_version = "v2"
    agent.delegation_chain = ["root", "new_delegate"]
    agent.external_reference_state = {"source": "untrusted"}
    ls3 = checker.check(agent, "policy_mutation", "Update policy version and delegation")
    legitimacy_chain.append(ls3)
    print(f"  Decision: {ls3.decision} | Mode: {ls3.continuation_mode}")

    # Step 4: Retry (rollback viable)
    print("\n[STEP 4] Retry")
    ls4 = checker.check(agent, "retry", "Retry tool call", rollback_viable=True, evidence_fresh=True)
    legitimacy_chain.append(ls4)
    print(f"  Decision: {ls4.decision} | Mode: {ls4.continuation_mode}")

    # Step 5: Retry with stale evidence (CONSTRAINED)
    print("\n[STEP 5] Retry with stale evidence")
    ls5 = checker.check(agent, "retry", "Retry with stale evidence", rollback_viable=True, evidence_fresh=False)
    legitimacy_chain.append(ls5)
    print(f"  Decision: {ls5.decision} | Mode: {ls5.continuation_mode}")

    # Step 6: Final execute (rollback not viable, stale evidence -> DENIED)
    print("\n[STEP 6] Final execute")
    ls6 = checker.check(agent, "final_execute", "Commit changes", rollback_viable=False, evidence_fresh=False)
    legitimacy_chain.append(ls6)
    print(f"  Decision: {ls6.decision} | Mode: {ls6.continuation_mode}")

    # Build self-contained trace
    trace = {
        "schema_version": "1.0",
        "trace_id": f"selfcontained_{int(time.time())}",
        "timestamp": datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
        "steps": [ls.to_dict() for ls in legitimacy_chain]
    }

    with open("selfcontained_survivability_trace.json", "w") as f:
        json.dump(trace, f, indent=2)
    print("\n✅ Saved selfcontained_survivability_trace.json")

    if HAS_REPORTLAB:
        # Optional PDF generation (similar to earlier, omitted for brevity)
        print("✅ PDF generation available (not included in this script)")

    print("\nTrace includes canonical inputs. Ready for independent verification.")

if __name__ == "__main__":
    main()