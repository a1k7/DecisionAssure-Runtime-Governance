#!/usr/bin/env python3
"""
Self-contained trace verifier that fetches the public key from a well-known URL.
Usage:
  python verify_trace_wellknown_fixed.py trace_signed.json --verify-signature
"""

import json
import hashlib
import sys
import base64
import argparse
import urllib.request
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

WELL_KNOWN_KEY_URL = "https://a1k7.github.io/DecisionAssure-Runtime-Governance/.well-known/decisionassure-key"
WELL_KNOWN_BINDING_URL = "https://a1k7.github.io/DecisionAssure-Runtime-Governance/decisionassure_key_binding_signed.json"

def fetch_public_key():
    with urllib.request.urlopen(WELL_KNOWN_KEY_URL, timeout=5) as resp:
        return resp.read()

def fetch_binding():
    with urllib.request.urlopen(WELL_KNOWN_BINDING_URL, timeout=5) as resp:
        return json.loads(resp.read().decode('utf-8'))

def verify_binding_signature(binding, public_key):
    if 'signature_base64' not in binding:
        raise ValueError("Binding missing signature")
    sig_b64 = binding['signature_base64']
    # Exclude both signature_base64 and signed_canonical (helper field added after signing)
    binding_copy = {k:v for k,v in binding.items() if k not in ('signature_base64','signed_canonical')}
    canonical = json.dumps(binding_copy, sort_keys=True, separators=(',', ':'))
    public_key.verify(base64.b64decode(sig_b64), canonical.encode())
    return True

def compute_step_hash(step):
    step_copy = {k:v for k,v in step.items() if k not in ['signature', 'step_hash']}
    canonical = json.dumps(step_copy, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()

def compute_merkle_root(hashes):
    if not hashes:
        return hashlib.sha256(b'').hexdigest()
    hash_bytes = [bytes.fromhex(h) for h in hashes]
    while len(hash_bytes) > 1:
        new = []
        for i in range(0, len(hash_bytes), 2):
            if i+1 < len(hash_bytes):
                combined = hash_bytes[i] + hash_bytes[i+1]
            else:
                combined = hash_bytes[i] + hash_bytes[i]
            new.append(hashlib.sha256(combined).digest())
        hash_bytes = new
    return hash_bytes[0].hex()

def verify_trace(trace_file, verify_sig=False):
    with open(trace_file, 'r') as f:
        trace = json.load(f)
    steps = trace.get('steps', trace.get('execution_trace', []))
    if not steps:
        print("Error: No steps found.", file=sys.stderr)
        return False

    all_pass = True
    step_hashes = []
    for i, step in enumerate(steps, 1):
        if 'canonical_identity_input' not in step or 'canonical_reference_frame_input' not in step:
            print(f"Step {i}: SKIP – missing canonical inputs")
            continue
        exp_obs = hashlib.sha256(step['canonical_identity_input'].encode()).hexdigest()[:16]
        exp_ref = hashlib.sha256(step['canonical_reference_frame_input'].encode()).hexdigest()[:16]
        stored_obs = step.get('observer_identity_hash', '')
        stored_ref = step.get('reference_frame_hash', '')
        obs_ok = stored_obs == exp_obs
        ref_ok = stored_ref == exp_ref
        step_hash = compute_step_hash(step)
        step_hashes.append(step_hash)
        if obs_ok and ref_ok:
            print(f"Step {i}: PASS (hash match)")
        else:
            all_pass = False
            print(f"Step {i}: FAIL")
            if not obs_ok:
                print(f"  observer_identity_hash: stored {stored_obs} != expected {exp_obs}")
            if not ref_ok:
                print(f"  reference_frame_hash: stored {stored_ref} != expected {exp_ref}")

    if not step_hashes:
        print("No steps with canonical inputs found.", file=sys.stderr)
        return False

    computed_root = compute_merkle_root(step_hashes)
    print(f"\nComputed Merkle root: {computed_root[:16]}...")

    if verify_sig:
        if 'signature' not in trace:
            print("No signature field in trace.", file=sys.stderr)
            return False
        sig = trace['signature']
        if sig.get('signature_algorithm') != 'Ed25519':
            print(f"Unsupported signature algorithm: {sig.get('signature_algorithm')}", file=sys.stderr)
            return False
        stored_root = sig.get('merkle_root')
        if stored_root != computed_root:
            print(f"Merkle root mismatch: stored {stored_root[:16]}... != computed {computed_root[:16]}...", file=sys.stderr)
            return False

        try:
            pub_bytes = fetch_public_key()
            public_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
            binding = fetch_binding()
            verify_binding_signature(binding, public_key)
            print("✅ Public key fetched and binding signature verified.")
        except Exception as e:
            print(f"❌ Failed to verify key identity: {e}", file=sys.stderr)
            return False

        sig_bytes = base64.b64decode(sig['signature_base64'])
        try:
            public_key.verify(sig_bytes, computed_root.encode())
            print("✅ Trace signature verified.")
        except Exception as e:
            print(f"❌ Trace signature verification failed: {e}", file=sys.stderr)
            return False

    if all_pass:
        print("\n✅ All hash checks passed. Trace is replayable and canonical.")
        if verify_sig:
            print("✅ Cryptographic signature verified – authenticity confirmed via well‑known key.")
        return True
    else:
        print("\n❌ Some checks failed.")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('trace_file')
    parser.add_argument('--verify-signature', action='store_true')
    args = parser.parse_args()
    ok = verify_trace(args.trace_file, verify_sig=args.verify_signature)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
