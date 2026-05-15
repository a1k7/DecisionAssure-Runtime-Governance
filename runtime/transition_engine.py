
from admissibility import AdmissibilityEvaluator

context = {
    "policy_stale": True,
    "rollback_unavailable": False,
    "authority_drift": True
}

engine = AdmissibilityEvaluator()

result = engine.evaluate(context)

print("Runtime Decision:")
print(result)

