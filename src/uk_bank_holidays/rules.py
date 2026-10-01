"""Evaluate a recurring rule for a given year."""

import calendar
from datetime import date, timedelta

from .easter import easter_sunday

WEEKDAYS = {
    name: i for i, name in enumerate(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"])
}


def is_active(rule: dict, year: int) -> bool:
    start, end = rule.get("valid_from_year"), rule.get("valid_to_year")
    return (start is None or year >= start) and (end is None or year <= end)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last = date(year, month, calendar.monthrange(year, month)[1])
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def occurrence(rule: dict, year: int) -> date:
    """The date of ``rule`` in ``year`` before any override or substitution."""
    p = rule["parameters"]
    kind = rule["rule_type"]
    if kind == "fixed_date":
        return date(year, p["month"], p["day"])
    if kind == "nth_weekday":
        return _nth_weekday(year, p["month"], WEEKDAYS[p["weekday"]], p["n"])
    if kind == "last_weekday":
        return _last_weekday(year, p["month"], WEEKDAYS[p["weekday"]])
    if kind == "easter_offset":
        return easter_sunday(year) + timedelta(days=p["days"])
    if kind == "weekday_after_last_weekday":
        anchor = _last_weekday(year, p["month"], WEEKDAYS[p["after_weekday"]])
        return anchor + timedelta(days=(WEEKDAYS[p["weekday"]] - anchor.weekday() - 1) % 7 + 1)
    raise ValueError(f"Unknown rule_type {kind!r} in rule {rule.get('rule_id')!r}")
