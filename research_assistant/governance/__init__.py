"""Governance policies, in two tiers, all registered here.

- Result policies judge an analytical result during query execution (data_api).
- Response policies judge the finished run before it is returned (workflow).

Adding a policy = one file in policies/ + one line in the relevant list.
"""

from research_assistant.governance.engine import (
    AnalyticalResult,
    GovernedResult,
    Policy,
    run_policies,
)
from research_assistant.governance.policies import grounding, researcher_access
from research_assistant.governance.policies.min_records import MinRecordsPolicy

POLICIES: list[Policy] = [
    MinRecordsPolicy(),
]

RESPONSE_POLICIES = [grounding.apply, researcher_access.apply]


def apply_policies(result: AnalyticalResult, context: dict) -> GovernedResult:
    return run_policies(result, context, POLICIES)


async def apply_response_policies(run: dict, context: dict) -> dict:
    for policy in RESPONSE_POLICIES:
        run = await policy(run, context)
    return run
