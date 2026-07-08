from research_assistant.governance.engine import AnalyticalResult, run_policies
from research_assistant.governance.policies.min_records import MinRecordsPolicy

_policy = MinRecordsPolicy()


def _check(record_count: int):
    return _policy.check(AnalyticalResult(rows=[], record_count=record_count), {})


def test_below_threshold_suppresses():
    decision = _check(4)
    assert decision.action == "suppress"
    assert decision.policy == "min_records"


def test_at_threshold_allows():
    assert _check(5).action == "allow"


def test_zero_records_allows():
    # an empty result discloses nobody; only small non-zero counts carry risk
    assert _check(0).action == "allow"


def test_run_policies_withholds_rows_on_suppression():
    result = AnalyticalResult(rows=[{"x": 1}], record_count=2)
    governed = run_policies(result, {}, [MinRecordsPolicy()])
    assert governed.suppressed is True
    assert governed.rows == []
