class AdmissibilityEvaluator:

    def __init__(self):
        self.threshold = 70

    def evaluate(self, context):
        score = 100

        if context["policy_stale"]:
            score -= 25

        if context["rollback_unavailable"]:
            score -= 30

        if context["authority_drift"]:
            score -= 20

        if score < self.threshold:
            return {
                "status": "COMMIT_INELIGIBLE",
                "score": score
            }

        return {
            "status": "ADMISSIBLE",
            "score": score
        }

