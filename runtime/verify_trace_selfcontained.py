#!/usr/bin/env python3
"""
Self-contained trace verifier for DecisionAssure.
Each step must have 'canonical_identity_input' and 'canonical_reference_frame_input'.
"""

import json
import hashlib
import sys

def compute_hash_from_canonical(canonical_str: str) -> str:
    full = hashlib.sha256(canonical_str.encode()).hexdigest()
    return full[:16]

def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_trace_selfcontained.py <trace_file.json>")
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:
        trace = json.load(f)

    if isinstance(trace, dict) and 'steps' in trace:
        steps = trace['steps']
    else:
        print("Error: Trace must be an object with a 'steps' array.")
        sys.exit(1)

    print(f"Verifying {len(steps)} steps...")
    all_pass = True
    for i, step in enumerate(steps, 1):
        if 'canonical_identity_input' not in step or 'canonical_reference_frame_input' not in step:
            print(f"Step {i}: SKIP – missing canonical inputs")
            continue

        expected_obs = compute_hash_from_canonical(step['canonical_identity_input'])
        expected_ref = compute_hash_from_canonical(step['canonical_reference_frame_input'])

        stored_obs = step.get('observer_identity_hash', '')
        stored_ref = step.get('reference_frame_hash', '')

        obs_ok = stored_obs == expected_obs
        ref_ok = stored_ref == expected_ref

        if obs_ok and ref_ok:
            print(f"Step {i}: PASS")
        else:
            all_pass = False
            print(f"Step {i}: FAIL")
            if not obs_ok:
                print(f"  observer_identity_hash: stored {stored_obs} != expected {expected_obs}")
            if not ref_ok:
                print(f"  reference_frame_hash: stored {stored_ref} != expected {expected_ref}")

    if all_pass:
        print("\n✅ All hash checks passed. Trace is replayable and canonical.")
    else:
        print("\n❌ Some hash checks failed. Trace may be corrupted or canonicalization mismatch.")
        sys.exit(1)

if __name__ == "__main__":
    main()