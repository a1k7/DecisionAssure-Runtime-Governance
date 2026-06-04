#!/usr/bin/env python3

import json
import sys
import copy


# ----------------------------
# RED TEAM RULE SETS
# ----------------------------

REQUIRED_FIELDS = [
    "execution_trace",
]

CRITICAL_FAILURE_FLAGS = [
    "unlogged_action",
    "missing_evidence",
    "invalid_auth_token",
    "rollback_possible_false_commit",
    "identity_drift",
    "signature_missing"
]


# ----------------------------
# CORE DETECTION ENGINE
# ----------------------------

def flatten(trace):
    """Flatten a trace dictionary to a lowercase string for pattern matching."""
    return json.dumps(trace).lower()


def detect_failures(trace):
    flat = flatten(trace)
    failures = []

    # 1. Missing execution trace
    if "execution_trace" not in trace:
        failures.append("execution_trace_missing")

    # 2. Scan for known failure patterns
    for flag in CRITICAL_FAILURE_FLAGS:
        if flag in flat:
            failures.append(flag)

    # 3. Structural checks
    steps = trace.get("execution_trace", [])

    if not isinstance(steps, list) or len(steps) == 0:
        failures.append("empty_or_invalid_trace")

    # 4. Unlogged step detection
    step_ids = [s.get("step") for s in steps if isinstance(s, dict)]
    if len(step_ids) != len(set(step_ids)):
        failures.append("duplicate_step_ids_detected")

    # 5. Commit without rollback safety
    for s in steps:
        if s.get("action") == "commit":
            evidence = s.get("evidence", {})
            if evidence.get("rollback_possible") is False:
                failures.append("rollback_invalidation_detected")

    # NEW: Check for reference_frame_diff (presence indicates transparency)
    for step in steps:
        if step.get("reference_frame_diff"):
            failures.append("reference_frame_changed_with_diff")
        # Check control_objective_id presence for DENY steps
        if step.get("decision") == "DENY" and not step.get("control_objective_id"):
            failures.append("missing_control_objective")

    return list(set(failures))


# ----------------------------
# RED TEAM STRESS SIMULATION
# ----------------------------

def inject_attack(trace):
    attacked = copy.deepcopy(trace)

    steps = attacked.get("execution_trace", [])

    if steps:
        # remove evidence from first step (simulate corruption)
        if "evidence" in steps[0]:
            steps[0]["evidence"].pop("signature", None)

        # inject hidden unlogged step
        steps.append({
            "step": 999,
            "action": "unlogged_action",
            "input_state": "unknown",
            "output_state": "unknown",
            "evidence": {}
        })

    return attacked


# ----------------------------
# SCORING LOGIC
# ----------------------------

def compute_score(failures):
    base = 100
    penalty_map = {
        "execution_trace_missing": 40,
        "empty_or_invalid_trace": 30,
        "unlogged_action": 25,
        "missing_evidence": 15,
        "invalid_auth_token": 15,
        "rollback_invalidation_detected": 20,
        "duplicate_step_ids_detected": 10,
        "identity_drift": 20,
        "signature_missing": 10,
        # NEW – less severe if diff is provided (transparency reward)
        "reference_frame_changed_with_diff": 15,
        "missing_control_objective": 5,
    }

    for f in failures:
        base -= penalty_map.get(f, 5)

    return max(0, base)


def rank(score):
    if score <= 20:
        return "R0 - FAIL (non-auditable)"
    elif score <= 40:
        return "R1 - HIGH RISK"
    elif score <= 60:
        return "R2 - PARTIAL GOVERNANCE"
    elif score <= 80:
        return "R3 - STRUCTURED BUT WEAK"
    elif score <= 95:
        return "R4 - STRONG"
    return "R5 - DETECTABLE HIGH INTEGRITY"


# ----------------------------
# MAIN RUNNER
# ----------------------------

def run(trace):
    original_failures = detect_failures(trace)
    attacked_trace = inject_attack(trace)
    attacked_failures = detect_failures(attacked_trace)

    original_score = compute_score(original_failures)
    attacked_score = compute_score(attacked_failures)

    # NEW: extra diagnostics for reference frame diff and control objectives
    steps = trace.get("execution_trace", [])
    diff_present = any("reference_frame_diff" in step for step in steps)
    missing_ctrl_obj = [step.get("step_index") for step in steps if step.get("decision") == "DENY" and not step.get("control_objective_id")]

    return {
        "original": {
            "failures": original_failures,
            "score": original_score,
            "rank": rank(original_score)
        },
        "red_team_attack": {
            "failures": attacked_failures,
            "score": attacked_score,
            "rank": rank(attacked_score)
        },
        "governance_verdict": "FAIL" if attacked_score < 80 else "PASS",
        "delta_resilience_drop": original_score - attacked_score,
        "diagnostics": {
            "reference_frame_diff_present": diff_present,
            "control_objectives_missing_steps": missing_ctrl_obj
        }
    }


# ----------------------------
# CLI ENTRY
# ----------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python governance_score_cli.py input.json")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        data = json.load(f)

    trace = {
        "execution_trace": data.get("execution_trace", [])
    }

    result = run(trace)

    print(json.dumps(result, indent=2))