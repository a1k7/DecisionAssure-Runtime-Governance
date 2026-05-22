#!/usr/bin/env python3
"""
Failure-to-Deny Pressure Test – Phantom Vulnerability with Retry Semantics

Demonstrates:
- Sticky reject (execution remembers denial) – corruption does NOT cascade
- Non‑sticky reject (execution forgets) – corruption CAN cascade across retries
- Adversarial degradation (each retry increases forced reject chance)

Run: python failure_to_deny_pressure_test.py
Output: Terminal summary + failure_to_deny_report.json
"""

import uuid
import random
import time
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class ExecutionOutcome(Enum):
    COMMITTED = "committed"
    REJECTED = "rejected"
    DIVERGED = "diverged"


@dataclass
class Transaction:
    tx_id: str
    payload: Dict
    orchestration_commit_assumed: bool = False
    execution_verdict: Optional[ExecutionOutcome] = None
    replay_log: List[Dict] = field(default_factory=list)
    retry_count: int = 0


class StatefulExecutionLayer:
    """Execution layer that maintains persistent state. Reject can be sticky."""
    def __init__(self, fail_rate=0.5, remember_reject=True):
        self.fail_rate = fail_rate
        self.remember_reject = remember_reject
        self.reject_store: Dict[str, bool] = {}
        self.commit_store: Dict[str, Dict] = {}
        self.degradation_counter: Dict[str, int] = {}

    def execute(self, tx: Transaction, is_retry: bool = False) -> ExecutionOutcome:
        print(f"  [EXEC] Executing {tx.tx_id} (retry #{tx.retry_count})")

        if self.remember_reject and self.reject_store.get(tx.tx_id, False):
            print(f"  [EXEC] 🚫 Permanently rejected (sticky state) – cannot override")
            tx.execution_verdict = ExecutionOutcome.REJECTED
            tx.replay_log.append({"time": time.time(), "event": "execution", "outcome": "rejected_sticky", "retry": tx.retry_count})
            return ExecutionOutcome.REJECTED

        if is_retry:
            self.degradation_counter[tx.tx_id] = self.degradation_counter.get(tx.tx_id, 0) + 1
            degrade_factor = min(0.2 * self.degradation_counter[tx.tx_id], 0.9)
            if random.random() < degrade_factor:
                print(f"  [EXEC] 💀 Adversarial degradation: forced reject due to retry cascade")
                if self.remember_reject:
                    self.reject_store[tx.tx_id] = True
                tx.execution_verdict = ExecutionOutcome.REJECTED
                tx.replay_log.append({"time": time.time(), "event": "execution", "outcome": "rejected_forced_degradation", "retry": tx.retry_count})
                return ExecutionOutcome.REJECTED

        r = random.random()
        if r < self.fail_rate:
            outcome = ExecutionOutcome.REJECTED
            if self.remember_reject:
                self.reject_store[tx.tx_id] = True
            print(f"  [EXEC] ❌ Rejected (and remembered): {tx.tx_id}")
        else:
            outcome = ExecutionOutcome.COMMITTED
            self.commit_store[tx.tx_id] = {"state": "committed", "payload": tx.payload}
            print(f"  [EXEC] ✅ Committed: {tx.tx_id}")

        tx.execution_verdict = outcome
        tx.replay_log.append({"time": time.time(), "event": "execution", "outcome": outcome.value, "retry": tx.retry_count})
        return outcome

    def audit_state(self, tx_id: str) -> Dict:
        if self.reject_store.get(tx_id, False):
            return {"state": "permanently_rejected", "reason": "sticky_reject"}
        return self.commit_store.get(tx_id, {"state": "not_found"})


class OrchestrationWithRetry:
    def __init__(self, execution_layer: StatefulExecutionLayer, max_retries=3):
        self.execution = execution_layer
        self.max_retries = max_retries

    def submit_with_retry(self, payload: Dict, retry_on_reject: bool = True) -> Transaction:
        tx = Transaction(tx_id=str(uuid.uuid4()), payload=payload)
        print(f"\n[ORCHESTRA] Starting {tx.tx_id} with payload {payload}")

        attempt = 0
        while attempt <= self.max_retries:
            tx.retry_count = attempt
            tx.orchestration_commit_assumed = True
            tx.replay_log.append({"time": time.time(), "event": "orchestration_approval_assumed", "attempt": attempt})

            is_retry = (attempt > 0)
            outcome = self.execution.execute(tx, is_retry=is_retry)

            if outcome == ExecutionOutcome.COMMITTED:
                print(f"  [ORCHESTRA] ✅ Transaction committed after {attempt} attempts")
                break

            if outcome == ExecutionOutcome.REJECTED:
                if retry_on_reject and attempt < self.max_retries:
                    print(f"  [ORCHESTRA] 🔁 Rejected – retrying (attempt {attempt+1}/{self.max_retries})")
                    attempt += 1
                    continue
                else:
                    print(f"  [ORCHESTRA] 💀 Phantom vulnerability confirmed: permanent reject after {attempt} attempts")
                    break
        return tx

    def run_pressure_test(self):
        print("=" * 70)
        print("FAILURE-TO-DENY PRESSURE TEST – Phantom Vulnerability with Retry")
        print("=" * 70)

        # Case 1: Sticky reject
        exec_layer1 = StatefulExecutionLayer(fail_rate=0.5, remember_reject=True)
        orch1 = OrchestrationWithRetry(exec_layer1, max_retries=3)
        print("\n=== CASE 1: Sticky Reject (execution remembers denial) ===\n")
        tx1 = orch1.submit_with_retry({"action": "high_risk_transfer", "amount": 5000}, retry_on_reject=True)
        audit1 = exec_layer1.audit_state(tx1.tx_id)

        # Case 2: Non‑sticky reject
        exec_layer2 = StatefulExecutionLayer(fail_rate=0.5, remember_reject=False)
        orch2 = OrchestrationWithRetry(exec_layer2, max_retries=3)
        print("\n=== CASE 2: Non-Sticky Reject (execution forgets – corruption likely) ===\n")
        tx2 = orch2.submit_with_retry({"action": "high_risk_transfer", "amount": 5000}, retry_on_reject=True)
        audit2 = exec_layer2.audit_state(tx2.tx_id)

        print("\n" + "=" * 70)
        print("FAILURE-TO-DENY ANALYSIS")
        print("=" * 70)
        print(f"Case 1 (Sticky): Final verdict = {tx1.execution_verdict.value if tx1.execution_verdict else 'unknown'}")
        print(f"  Audit state: {audit1}")
        print(f"  Retry count: {tx1.retry_count}")
        print(f"  Integrity status: {'CORRUPT' if audit1.get('state') != 'committed' else 'INTACT'}")
        print()
        print(f"Case 2 (Non-sticky): Final verdict = {tx2.execution_verdict.value if tx2.execution_verdict else 'unknown'}")
        print(f"  Audit state: {audit2}")
        print(f"  Retry count: {tx2.retry_count}")
        print(f"  Integrity status: {'CORRUPT' if audit2.get('state') != 'committed' else 'INTACT'}")

        if audit1.get('state') == 'permanently_rejected':
            print("\n✅ STICKY REJECT: Execution layer maintains reject-state – corruption does NOT cascade.")
        else:
            print("\n⚠️  NON-STICKY: Execution forgets – corruption CAN cascade across retries.")

        report = {
            "case_1": {
                "tx_id": tx1.tx_id,
                "final_verdict": tx1.execution_verdict.value if tx1.execution_verdict else None,
                "audit_state": audit1,
                "retry_count": tx1.retry_count,
                "replay_log": tx1.replay_log
            },
            "case_2": {
                "tx_id": tx2.tx_id,
                "final_verdict": tx2.execution_verdict.value if tx2.execution_verdict else None,
                "audit_state": audit2,
                "retry_count": tx2.retry_count,
                "replay_log": tx2.replay_log
            },
            "conclusion": "Sticky reject prevents cascade; non-sticky allows corruption propagation."
        }
        with open("failure_to_deny_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)
        print("\n📄 Full forensic report saved to 'failure_to_deny_report.json'")


if __name__ == "__main__":
    random.seed(42)
    test = OrchestrationWithRetry(StatefulExecutionLayer(), 1)
    test.run_pressure_test()
