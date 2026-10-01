"""Expand the source rules into one row per (date, rule), with a boolean flag per region."""

from datetime import date, timedelta

from .data import DEFAULT_END_YEAR, DEFAULT_START_YEAR, REGIONS
from .rules import is_active, occurrence

# The Banking and Financial Dealings Act 1971 moved holidays that fall on a weekend to the next
# free weekday. Earlier years follow the plain rules.
SUBSTITUTES_FROM_YEAR = 1971

ROW_COLUMNS = [
    "holiday_date",
    "rule_id",
    "holiday_key",
    "holiday_name",
    "holiday_type",
    *REGIONS,
    "is_substitute",
    "notes",
    "source_ids",
]


def _weekend(d: date) -> bool:
    return d.weekday() >= 5


def _year_rows(data: dict, year: int, substitutes: bool) -> list[dict]:
    overrides = {(o["rule_id"], o["year"]): o for o in data["overrides"]}
    # (rule/proclamation, date, {region: ...}) instances before substitution
    instances = []
    for rule in data["rules"]:
        if not is_active(rule, year):
            continue
        override = overrides.get((rule["rule_id"], year))
        when = date.fromisoformat(override["date"]) if override else occurrence(rule, year)
        instances.append({"item": rule, "date": when, "override": override, "kind": "rule"})
    for proc in data["proclamations"]:
        when = date.fromisoformat(proc["date"])
        if when.year == year:
            instances.append({"item": proc, "date": when, "override": None, "kind": "proclamation"})

    rows: dict[tuple[str, str], dict] = {}

    def emit(inst, region, when, substitute_for=None):
        item = inst["item"]
        rule_id = item.get("rule_id") or item["proclamation_id"]
        key = (when.isoformat(), rule_id)
        if inst["kind"] == "proclamation":
            kind, name, holiday_key = "proclamation", item["name"], rule_id
            notes = item["reason"]
            sources = item["source_ids"]
        else:
            kind = "moved" if inst["override"] else "recurring"
            name, holiday_key = item["name"], item["holiday_key"]
            notes = (inst["override"] or {}).get("reason") or item.get("notes")
            sources = list(item["source_ids"]) + list((inst["override"] or {}).get("source_ids", []))
        if substitute_for:
            notes = f"Substitute for {substitute_for.isoformat()}" + (f". {notes}" if notes else "")
        row = rows.setdefault(
            key,
            {
                "holiday_date": when.isoformat(),
                "rule_id": rule_id,
                "holiday_key": holiday_key,
                "holiday_name": name,
                "holiday_type": kind,
                **{r: False for r in REGIONS},
                "is_substitute": substitute_for is not None,
                "notes": notes,
                "source_ids": sorted(set(sources)),
            },
        )
        row[region] = True

    for region in REGIONS:
        regional = [i for i in instances if i["item"][region]]
        occupied = {i["date"] for i in regional if not _weekend(i["date"])}
        for inst in sorted(regional, key=lambda i: (i["date"], i["item"].get("rule_id", ""))):
            can_substitute = (
                substitutes
                and year >= SUBSTITUTES_FROM_YEAR
                and inst["kind"] == "rule"
                and not inst["override"]
                and inst["item"]["rule_type"] == "fixed_date"
            )
            if not _weekend(inst["date"]):
                emit(inst, region, inst["date"])
            elif can_substitute:
                moved = inst["date"] + timedelta(days=1)
                while _weekend(moved) or moved in occupied:
                    moved += timedelta(days=1)
                occupied.add(moved)
                emit(inst, region, moved, substitute_for=inst["date"])
            else:
                emit(inst, region, inst["date"])
    return list(rows.values())


def build_rows(
    data: dict, start_year: int = DEFAULT_START_YEAR, end_year: int = DEFAULT_END_YEAR, substitutes: bool = True
) -> list[dict]:
    """Every bank holiday between ``start_year`` and ``end_year`` inclusive, sorted by date."""
    rows = []
    for year in range(start_year, end_year + 1):
        rows.extend(_year_rows(data, year, substitutes))
    rows.sort(key=lambda r: (r["holiday_date"], r["rule_id"]))
    return rows


def filter_region(rows: list[dict], region: str) -> list[dict]:
    """Rows for one region, without the region flags."""
    out = []
    for row in rows:
        if row[region]:
            out.append({k: v for k, v in row.items() if k not in REGIONS})
    return out
