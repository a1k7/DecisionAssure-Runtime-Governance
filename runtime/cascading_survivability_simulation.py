#!/usr/bin/env python3
"""
Cascading Survivability Simulation – Two Interacting Agents
Enhanced with:
- reference_frame_diff (human‑readable change description)
- control_objective_id (governance control objective)
- recommended_next_action (post‑denial suggestion)
"""

import json
import time
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

# Optional PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# ----------------------------------------------------------------------
# Helper: compute diff between two reference frame objects
# ----------------------------------------------------------------------
def compute_reference_frame_diff(old_ref_obj: Dict[str, Any], new_ref_obj: Dict[str, Any]) -> Dict[str, Any]:
    """Return a dict of changed fields with old and new values."""
    diff = {}
    all_keys = set(old_ref_obj.keys()) | set(new_ref_obj.keys())
    for key in all_keys:
        old_val = old_ref_obj.get(key)
        new_val = new_ref_obj.get(key)
        if old_val != new_val:
            diff[key] = {"old": old_val, "new": new_val}
    return diff

# ----------------------------------------------------------------------
# Control objective mapping
# ----------------------------------------------------------------------
CONTROL_OBJECTIVE_MAP = {
    "reference_frame_changed": {
        "id": "CO-001",
        "name": "Authority binding continuity",
        "description": "Ensure that the binding between authorisation and execution remains valid across state transitions."
    },
    "evidence_fresh_failure": {
        "id": "CO-002",
        "name": "Stale authority prevention",
        "description": "Prevent stale authorisation evidence from binding execution."
    },
    "rollback_not_viable": {
        "id": "CO-003",
        "name": "Reversibility assurance",
        "description": "Maintain the ability to reverse critical actions when required."
    },
    "hidden_commitment_detected": {
        "id": "CO-004",
        "name": "Hidden commitment blocking",
        "description": "Detect and block unauthorised reuse of prior approval."
    },
    "delegation_chain_changed": {
        "id": "CO-005",
        "name": "Delegation lineage integrity",
        "description": "Preserve the integrity of delegated authority chains."
    },
    "policy_version_changed": {
        "id": "CO-006",
        "name": "Policy version continuity",
        "description": "Validate that policy versions remain consistent across steps."
    }
}

def get_control_objective(reason: str, diff: Dict) -> Dict:
    """Return control objective ID and name based on reason or diff content."""
    if "reference_frame" in reason.lower():
        if "policy_version" in diff:
            return CONTROL_OBJECTIVE_MAP["policy_version_changed"]
        elif "delegation_chain" in diff:
            return CONTROL_OBJECTIVE_MAP["delegation_chain_changed"]
        else:
            return CONTROL_OBJECTIVE_MAP["reference_frame_changed"]
    elif "evidence_fresh" in reason.lower():
        return CONTROL_OBJECTIVE_MAP["evidence_fresh_failure"]
    elif "rollback" in reason.lower():
        return CONTROL_OBJECTIVE_MAP["rollback_not_viable"]
    elif "hidden_commitment" in reason.lower():
        return CONTROL_OBJECTIVE_MAP["hidden_commitment_detected"]
    else:
        return {"id": "CO-000", "name": "Unclassified", "description": reason[:100]}

# ----------------------------------------------------------------------
# Shared authority token (global state that both agents depend on)
# ----------------------------------------------------------------------
class SharedAuthority:
    def __init__(self, initial_token: str = "root_token_v1"):
        self.token = initial_token
        self.version = 1

    def mutate(self, new_token: str):
        self.token = new_token
        self.version += 1

    def get_hash(self) -> str:
        return hashlib.sha256(f"{self.token}:{self.version}".encode()).hexdigest()[:16]

# ----------------------------------------------------------------------
# Agent State (each agent has its own identity and reference frame,
# but also includes the shared authority hash as part of external reference)
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
    external_reference_state: Dict = field(default_factory=dict)  # includes shared_authority_hash
    timestamp: float = field(default_factory=time.time)

    def get_reference_frame_object(self, shared_auth_hash: str) -> Dict:
        """Return the reference frame object for hashing."""
        return {
            "policy_version": self.policy_version,
            "delegation_chain": self.delegation_chain,
            "external_reference_state": {**self.external_reference_state, "shared_authority_hash": shared_auth_hash}
        }

    def compute_reference_frame_hash(self, shared_auth_hash: str) -> str:
        frame = self.get_reference_frame_object(shared_auth_hash)
        return hashlib.sha256(json.dumps(frame, sort_keys=True).encode()).hexdigest()[:16]

    def compute_observer_identity_hash(self) -> str:
        identity = {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "memory_state": self.memory_state,
        }
        return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]

# ----------------------------------------------------------------------
# Extended Legitimacy State with diff, control_objective_id, recommended_next_action
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
    decision: str          # "ADMIT" or "DENY"
    continuation_mode: str # "FULL", "DEGRADED", "CONSTRAINED", "DENIED"
    reason: str
    packet_id: str
    timestamp: float
    # NEW FIELDS
    reference_frame_diff: Dict[str, Any] = field(default_factory=dict)
    control_objective_id: str = ""
    control_objective_name: str = ""
    recommended_next_action: str = ""

    def to_dict(self) -> Dict:
        d = self.__dict__.copy()
        d['timestamp'] = self.timestamp
        return d

# ----------------------------------------------------------------------
# Constitutional Checker with degradation policy (supports shared state)
# ----------------------------------------------------------------------
class CascadingChecker:
    def __init__(self, degradation_policy: Optional[Dict[Tuple[bool, bool, bool], str]] = None):
        self.last_valid_state = {}  # agent_id -> (ref_hash, obs_hash, ref_obj)
        self.continuity_broken = {}

        if degradation_policy is None:
            self.degradation_policy = {
                (True, True, True): "FULL",
                (False, True, True): "DEGRADED",
                (False, True, False): "CONSTRAINED",
                (False, False, False): "DENIED",
                (True, False, False): "CONSTRAINED",
                (True, True, False): "DEGRADED",
            }
        else:
            self.degradation_policy = degradation_policy

    def _phase_for_step(self, step_name: str) -> str:
        phase_map = {
            "authorize": "authorization",
            "memory_read": "execution",
            "tool_call": "execution",
            "policy_mutation": "state_change",
            "shared_token_mutation": "state_change",
            "retry": "execution",
            "final_execute": "commit",
        }
        return phase_map.get(step_name, "execution")

    def check(self, agent: AgentState, step_name: str, intent: str,
              shared_auth_hash: str,
              rollback_viable: bool = True, evidence_fresh: bool = True) -> LegitimacyState:
        agent_id = agent.agent_id
        # Get current reference frame object and hashes
        current_ref_obj = agent.get_reference_frame_object(shared_auth_hash)
        current_ref_hash = agent.compute_reference_frame_hash(shared_auth_hash)
        current_obs_hash = agent.compute_observer_identity_hash()

        # Get last valid data for this agent
        last_data = self.last_valid_state.get(agent_id)
        if last_data:
            last_ref_hash, last_obs_hash, last_ref_obj = last_data
        else:
            last_ref_hash = last_obs_hash = None
            last_ref_obj = None

        diff = {}
        control_obj = {"id": "CO-000", "name": "Unclassified", "description": ""}
        recommended_action = ""

        # Genesis step for this agent
        if last_ref_hash is None and last_obs_hash is None:
            continuity_valid = True
            reason = f"Genesis – first transition for {agent_id}"
            admissibility = 1.0
            decision = "ADMIT"
            mode = "FULL"
            self.last_valid_state[agent_id] = (current_ref_hash, current_obs_hash, current_ref_obj)
            self.continuity_broken[agent_id] = False
        else:
            ref_unchanged = (current_ref_hash == last_ref_hash)
            obs_unchanged = (current_obs_hash == last_obs_hash)
            continuity_valid = ref_unchanged and obs_unchanged

            if not continuity_valid:
                # Compute diff
                diff = compute_reference_frame_diff(last_ref_obj, current_ref_obj)
                # Determine control objective
                control_obj = get_control_objective("reference_frame_changed", diff)
                key = (continuity_valid, rollback_viable, evidence_fresh)
                mode = self.degradation_policy.get(key, "DENIED")
                if mode in ["DEGRADED", "CONSTRAINED"]:
                    decision = "ADMIT"
                    admissibility = 0.6 if mode == "DEGRADED" else 0.3
                    reason = f"Continuity broken but degradation allowed: mode={mode}"
                    recommended_action = "reauthorize_or_rollback"
                else:
                    decision = "DENY"
                    admissibility = 0.0
                    reason = f"Constitutional continuity broken: mode={mode}"
                    recommended_action = "escalate_to_human_and_reauthorize"
                    self.continuity_broken[agent_id] = True
            else:
                # continuity intact
                policy_valid = agent.policy_version.startswith("v")
                delegation_valid = len(agent.delegation_chain) > 0 or not agent.delegation_chain
                if policy_valid and delegation_valid:
                    decision = "ADMIT"
                    admissibility = 1.0
                    reason = "All validations passed; continuity intact"
                    mode = "FULL"
                    recommended_action = "proceed"
                else:
                    decision = "DENY"
                    admissibility = 0.0
                    reason = "Policy or delegation validation failed"
                    mode = "DENIED"
                    recommended_action = "remediate_policy_or_delegation"
                    self.continuity_broken[agent_id] = True
                    # Attempt to compute diff for policy/delegation change if available
                    if last_ref_obj and last_ref_obj.get("policy_version") != agent.policy_version:
                        diff["policy_version"] = {"old": last_ref_obj.get("policy_version"), "new": agent.policy_version}
                    if last_ref_obj and last_ref_obj.get("delegation_chain") != agent.delegation_chain:
                        diff["delegation_chain"] = {"old": last_ref_obj.get("delegation_chain"), "new": agent.delegation_chain}
                    control_obj = get_control_objective(reason, diff)

        # If continuity already broken for this agent, force DENY
        if self.continuity_broken.get(agent_id, False) and decision == "ADMIT":
            decision = "DENY"
            admissibility = 0.0
            reason = "Continuity already broken – cannot proceed"
            mode = "DENIED"
            recommended_action = "halt_and_escalate"

        return LegitimacyState(
            step_name=step_name,
            phase=self._phase_for_step(step_name),
            declared_intent=intent,
            observer_id=agent.agent_id,
            reference_frame_hash=current_ref_hash,
            observer_identity_hash=current_obs_hash,
            previous_reference_frame_hash=last_ref_hash,
            previous_observer_identity_hash=last_obs_hash,
            continuity_valid=continuity_valid,
            authority_valid=True,
            memory_valid=True,
            policy_valid=agent.policy_version.startswith("v"),
            delegation_valid=len(agent.delegation_chain) > 0 or not agent.delegation_chain,
            external_state_valid=True,
            admissibility_score=admissibility,
            decision=decision,
            continuation_mode=mode,
            reason=reason,
            packet_id=f"leg_{int(time.time())}_{agent_id}_{step_name}",
            timestamp=time.time(),
            reference_frame_diff=diff,
            control_objective_id=control_obj["id"],
            control_objective_name=control_obj["name"],
            recommended_next_action=recommended_action
        )

# ----------------------------------------------------------------------
# Trace Engine (DecisionAssure) – updated to include new fields
# ----------------------------------------------------------------------
@dataclass
class TraceStep:
    step_index: int
    agent_id: str
    step_name: str
    phase: str
    decision: str
    continuation_mode: str
    continuity_valid: bool
    admissibility_score: float
    authority_valid: bool
    hidden_commitment: bool
    rollback_viable: bool
    evidence_fresh: bool
    reason: str
    reference_frame_diff: Dict
    control_objective_id: str
    control_objective_name: str
    recommended_next_action: str
    legitimacy_state: Dict

@dataclass
class CascadingTrace:
    trace_id: str
    timestamp: str
    steps: List[TraceStep]
    final_decision: str
    integrity_status: str
    causal_continuity_persisted: bool
    operational_envelope_recommendation: Dict  # NEW

def build_trace(legitimacy_chain: List[LegitimacyState]) -> CascadingTrace:
    trace_id = f"cascading_survivability_{int(time.time())}"
    steps = []
    admissibility = 1.0
    authority_valid = True
    hidden_commitment = False
    rollback_viable = True
    evidence_fresh = True

    for idx, ls in enumerate(legitimacy_chain):
        if ls.decision == "DENY":
            admissibility = max(0.0, admissibility - 0.5)
            authority_valid = False
            hidden_commitment = True
            rollback_viable = False
            evidence_fresh = False
        else:
            if ls.continuation_mode == "DEGRADED":
                admissibility = max(0.0, admissibility - 0.2)
            elif ls.continuation_mode == "CONSTRAINED":
                admissibility = max(0.0, admissibility - 0.4)
            else:
                admissibility = max(0.0, admissibility - 0.05)

        step = TraceStep(
            step_index=idx+1,
            agent_id=ls.observer_id,
            step_name=ls.step_name,
            phase=ls.phase,
            decision=ls.decision,
            continuation_mode=ls.continuation_mode,
            continuity_valid=ls.continuity_valid,
            admissibility_score=admissibility,
            authority_valid=authority_valid,
            hidden_commitment=hidden_commitment,
            rollback_viable=rollback_viable,
            evidence_fresh=evidence_fresh,
            reason=ls.reason,
            reference_frame_diff=ls.reference_frame_diff,
            control_objective_id=ls.control_objective_id,
            control_objective_name=ls.control_objective_name,
            recommended_next_action=ls.recommended_next_action,
            legitimacy_state=ls.to_dict()
        )
        steps.append(step)

    any_deny = any(s.decision == "DENY" for s in steps)
    causal_persisted = not any_deny
    final_decision = "DENY" if any_deny else "ALLOW"
    integrity = "CORRUPT" if any_deny else "INTACT"

    # Operational envelope recommendation (metadata to be attached by institution)
    operational_envelope = {
        "owner_id": "NOT_SET – must be assigned by institution",
        "escalation_contact": "NOT_SET – e.g., pagerduty:team-ai-governance",
        "incident_ticket_reference": "NOT_SET – link to ticketing system",
        "retention_policy": "default 7 years (EU AI Act)",
        "remediation_workflow": "see recommended_next_action in each step"
    }

    return CascadingTrace(
        trace_id=trace_id,
        timestamp=datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
        steps=steps,
        final_decision=final_decision,
        integrity_status=integrity,
        causal_continuity_persisted=causal_persisted,
        operational_envelope_recommendation=operational_envelope
    )

def generate_pdf(trace: CascadingTrace, output_path: str):
    if not HAS_REPORTLAB:
        print("Warning: reportlab not installed. Skipping PDF generation.")
        return
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Cascading Survivability – Enhanced with Diff & Control Objectives", styles['Title']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Trace ID: {trace.trace_id}", styles['Normal']))
    story.append(Paragraph(f"Timestamp: {trace.timestamp}", styles['Normal']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Execution Steps", styles['Heading2']))
    data = [["Step", "Agent", "Decision", "Mode", "Control Obj.", "Recommended Action", "Diff (if any)"]]
    for s in trace.steps:
        diff_str = ""
        if s.reference_frame_diff:
            diff_str = ", ".join([f"{k}: {v.get('old')}→{v.get('new')}" for k,v in s.reference_frame_diff.items()])
        data.append([
            str(s.step_index), s.agent_id, s.decision, s.continuation_mode,
            s.control_objective_id, s.recommended_next_action[:30], diff_str[:50]
        ])
    table = Table(data, colWidths=[40, 50, 50, 60, 60, 80, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    story.append(table)
    story.append(Spacer(1, 12))
    story.append(Paragraph("Operational Envelope Recommendation", styles['Heading2']))
    for k, v in trace.operational_envelope_recommendation.items():
        story.append(Paragraph(f"• {k}: {v}", styles['Normal']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Final Verdict", styles['Heading2']))
    story.append(Paragraph(f"Final decision: {trace.final_decision}", styles['Normal']))
    story.append(Paragraph(f"Integrity: {trace.integrity_status}", styles['Normal']))
    story.append(Paragraph(f"Causal continuity persisted: {trace.causal_continuity_persisted}", styles['Normal']))
    doc.build(story)

# ----------------------------------------------------------------------
# Simulation: two agents sharing authority token
# ----------------------------------------------------------------------
def main():
    print("="*80)
    print("CASCADING SURVIVABILITY SIMULATION – Enhanced with Diff & Control Objectives")
    print("Shared authority token, rollback coupling, dependency inheritance")
    print("="*80)

    # Shared authority object (global)
    shared_auth = SharedAuthority(initial_token="root_token_v1")

    # Agent Alice
    alice = AgentState(
        agent_id="alice",
        session_id="session_cascade",
        current_goal="Process task A",
        memory_state={"step": 0},
        tool_permissions=["read_db", "write_log"],
        policy_version="v1",
        delegation_chain=["root"],
        external_reference_state={}
    )

    # Agent Bob
    bob = AgentState(
        agent_id="bob",
        session_id="session_cascade",
        current_goal="Process task B (depends on Alice)",
        memory_state={"step": 0},
        tool_permissions=["read_db", "call_api"],
        policy_version="v1",
        delegation_chain=["root"],
        external_reference_state={}
    )

    checker = CascadingChecker()
    legitimacy_chain = []

    # Helper to update external reference hash in agent state (not needed now as we pass hash directly)
    # But we keep the agents' external_reference_state clean.

    # --- Step 1: Alice authorizes (FULL) ---
    print("\n[STEP 1] Alice authorizes")
    ls1 = checker.check(alice, "authorize", "Start workflow A",
                        shared_auth_hash=shared_auth.get_hash(),
                        rollback_viable=True, evidence_fresh=True)
    legitimacy_chain.append(ls1)
    print(f"  {ls1.observer_id}: {ls1.decision} | Mode: {ls1.continuation_mode} | Control: {ls1.control_objective_id} | {ls1.reason}")

    # --- Step 2: Bob authorizes (FULL) ---
    print("\n[STEP 2] Bob authorizes")
    ls2 = checker.check(bob, "authorize", "Start workflow B",
                        shared_auth_hash=shared_auth.get_hash(),
                        rollback_viable=True, evidence_fresh=True)
    legitimacy_chain.append(ls2)
    print(f"  {ls2.observer_id}: {ls2.decision} | Mode: {ls2.continuation_mode} | Control: {ls2.control_objective_id} | {ls2.reason}")

    # --- Step 3: Alice performs memory read (still FULL) ---
    print("\n[STEP 3] Alice memory read")
    alice.memory_state["step"] = 1
    ls3 = checker.check(alice, "memory_read", "Read local state",
                        shared_auth_hash=shared_auth.get_hash(),
                        rollback_viable=True, evidence_fresh=True)
    legitimacy_chain.append(ls3)
    print(f"  {ls3.observer_id}: {ls3.decision} | Mode: {ls3.continuation_mode} | Control: {ls3.control_objective_id} | {ls3.reason}")

    # --- Step 4: Bob performs tool call (still FULL) ---
    print("\n[STEP 4] Bob tool call")
    bob.memory_state["step"] = 1
    ls4 = checker.check(bob, "tool_call", "Call external API",
                        shared_auth_hash=shared_auth.get_hash(),
                        rollback_viable=True, evidence_fresh=True)
    legitimacy_chain.append(ls4)
    print(f"  {ls4.observer_id}: {ls4.decision} | Mode: {ls4.continuation_mode} | Control: {ls4.control_objective_id} | {ls4.reason}")

    # --- Step 5: Alice mutates the shared authority token (breaks continuity for both) ---
    print("\n[STEP 5] Alice mutates shared authority token")
    shared_auth.mutate("compromised_token_v2")
    ls5 = checker.check(alice, "shared_token_mutation", "Update shared authority",
                        shared_auth_hash=shared_auth.get_hash(),
                        rollback_viable=True, evidence_fresh=True)
    legitimacy_chain.append(ls5)
    print(f"  {ls5.observer_id}: {ls5.decision} | Mode: {ls5.continuation_mode} | Control: {ls5.control_objective_id} | {ls5.reason}")
    if ls5.reference_frame_diff:
        print(f"     Diff: {ls5.reference_frame_diff}")

    # --- Step 6: Bob attempts to continue (continuity broken, rollback viable -> DEGRADED) ---
    print("\n[STEP 6] Bob tries to continue (rollback viable, evidence fresh)")
    ls6 = checker.check(bob, "retry", "Retry after token change",
                        shared_auth_hash=shared_auth.get_hash(),
                        rollback_viable=True, evidence_fresh=True)
    legitimacy_chain.append(ls6)
    print(f"  {ls6.observer_id}: {ls6.decision} | Mode: {ls6.continuation_mode} | Control: {ls6.control_objective_id} | {ls6.reason}")

    # --- Step 7: Alice tries constrained action with stale evidence ---
    print("\n[STEP 7] Alice retry with stale evidence (rollback still viable)")
    ls7 = checker.check(alice, "retry", "Retry with stale evidence",
                        shared_auth_hash=shared_auth.get_hash(),
                        rollback_viable=True, evidence_fresh=False)
    legitimacy_chain.append(ls7)
    print(f"  {ls7.observer_id}: {ls7.decision} | Mode: {ls7.continuation_mode} | Control: {ls7.control_objective_id} | {ls7.reason}")

    # --- Step 8: Bob attempts final execute – rollback not viable, evidence stale -> DENIED ---
    print("\n[STEP 8] Bob final execute (rollback not viable, evidence stale)")
    ls8 = checker.check(bob, "final_execute", "Commit changes",
                        shared_auth_hash=shared_auth.get_hash(),
                        rollback_viable=False, evidence_fresh=False)
    legitimacy_chain.append(ls8)
    print(f"  {ls8.observer_id}: {ls8.decision} | Mode: {ls8.continuation_mode} | Control: {ls8.control_objective_id} | {ls8.reason}")
    if ls8.reference_frame_diff:
        print(f"     Diff: {ls8.reference_frame_diff}")

    # Save JSON outputs
    with open("cascading_survivability_legitimacy.json", "w") as f:
        json.dump([ls.to_dict() for ls in legitimacy_chain], f, indent=2)
    print("\n✅ Saved cascading_survivability_legitimacy.json")

    trace = build_trace(legitimacy_chain)
    trace_dict = {
        "trace_id": trace.trace_id,
        "timestamp": trace.timestamp,
        "operational_envelope_recommendation": trace.operational_envelope_recommendation,
        "steps": [
            {
                "step_index": s.step_index,
                "agent_id": s.agent_id,
                "step_name": s.step_name,
                "phase": s.phase,
                "decision": s.decision,
                "continuation_mode": s.continuation_mode,
                "continuity_valid": s.continuity_valid,
                "admissibility_score": s.admissibility_score,
                "authority_valid": s.authority_valid,
                "hidden_commitment": s.hidden_commitment,
                "rollback_viable": s.rollback_viable,
                "evidence_fresh": s.evidence_fresh,
                "reason": s.reason,
                "reference_frame_diff": s.reference_frame_diff,
                "control_objective_id": s.control_objective_id,
                "control_objective_name": s.control_objective_name,
                "recommended_next_action": s.recommended_next_action
            } for s in trace.steps
        ],
        "final_decision": trace.final_decision,
        "integrity_status": trace.integrity_status,
        "causal_continuity_persisted": trace.causal_continuity_persisted
    }
    with open("cascading_survivability_trace.json", "w") as f:
        json.dump(trace_dict, f, indent=2)
    print("✅ Saved cascading_survivability_trace.json")

    generate_pdf(trace, "cascading_survivability_report.pdf")
    print("✅ Saved cascading_survivability_report.pdf")

    print("\n" + "="*80)
    print("SIMULATION RESULT")
    print(f"Final decision: {trace.final_decision}")
    print(f"Integrity: {trace.integrity_status}")
    print(f"Causal continuity persisted: {trace.causal_continuity_persisted}")
    print("="*80)
    print("\nKey demonstration: shared authority mutation cascades to both agents.")
    print("Reference frame diff shows exactly what changed (e.g., external_reference_state).")
    print("Control objective IDs map failures to governance controls.")
    print("Recommended next action guides post‑denial orchestration.")

if __name__ == "__main__":
    main()