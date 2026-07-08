from datetime import date
from decimal import Decimal

from research_assistant.data_api.guardrails import _json_safe, shape_rows


def test_decimal_becomes_float():
    value = _json_safe(Decimal("68.78"))
    assert isinstance(value, float)
    assert value == 68.78


def test_non_finite_floats_become_none():
    assert _json_safe(float("nan")) is None
    assert _json_safe(float("inf")) is None


def test_dates_become_iso_strings():
    assert _json_safe(date(2026, 7, 8)) == "2026-07-08"


def test_shape_rows_is_json_safe():
    rows = shape_rows([{"avg_hba1c": Decimal("1.5"), "sex": "F", "n": 3}])
    assert rows == [{"avg_hba1c": 1.5, "sex": "F", "n": 3}]
