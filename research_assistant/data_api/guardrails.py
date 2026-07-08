import math
from datetime import date, datetime
from decimal import Decimal


def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def shape_rows(records) -> list[dict]:
    """Convert database rows to JSON-safe dicts"""
    return [{k: _json_safe(v) for k, v in dict(r).items()} for r in records]
