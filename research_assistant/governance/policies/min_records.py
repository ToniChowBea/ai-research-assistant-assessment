from research_assistant.config import get_settings
from research_assistant.governance.engine import AnalyticalResult, PolicyDecision


class MinRecordsPolicy:
    name = "min_records"

    def check(self, result: AnalyticalResult, context: dict) -> PolicyDecision:
        threshold = get_settings().governance_min_records
        if 0 < result.record_count < threshold:
            return PolicyDecision(
                action="suppress",
                policy=self.name,
                reason=(
                    f"Suppressed by the '{self.name}' policy: the result is based "
                    f"fewer than {threshold} records which is below the platform's "
                    "disclosure threshold"
                ),
            )
        return PolicyDecision(action="allow", policy=self.name)
