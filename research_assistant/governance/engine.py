from dataclasses import dataclass
from typing import Protocol

# One voice for suppression everywhere. Prevents agent loooping.
SUPPRESSION_NOTICE = (
    "FINAL GOVERNED OUTCOME: this result was suppressed by governance policy. "
    "Retrying this or any other tool will not change the outcome for this "
    "dataset. Report the suppression and its reason to the researcher as the "
    "answer."
)


@dataclass(frozen=True)
class AnalyticalResult:
    """What governance inspects.
    record_count is the number of underlying records the result is built on.
    """

    rows: list[dict]
    record_count: int


@dataclass(frozen=True)
class PolicyDecision:
    action: str  # "allow" | "suppress"
    policy: str
    reason: str | None = None


@dataclass(frozen=True)
class GovernedResult:
    rows: list[dict]
    suppressed: bool
    decisions: list[PolicyDecision]


class Policy(Protocol):
    name: str

    def check(self, result: AnalyticalResult, context: dict) -> PolicyDecision: ...


def run_policies(
    result: AnalyticalResult, context: dict, policies: list[Policy]
) -> GovernedResult:
    """Run every policy; first suppression withholds the rows. All decisions
    are kept for the audit record either way."""
    decisions: list[PolicyDecision] = []
    for policy in policies:
        decision = policy.check(result, context)
        decisions.append(decision)
        if decision.action == "suppress":
            return GovernedResult(rows=[], suppressed=True, decisions=decisions)
    return GovernedResult(rows=result.rows, suppressed=False, decisions=decisions)
