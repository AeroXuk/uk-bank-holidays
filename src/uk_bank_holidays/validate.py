"""Validate the source data and (optionally) compare the output with the GOV.UK feed."""

import json
import urllib.request
from datetime import date

from jsonschema import Draft202012Validator

from .data import REGIONS, SCHEMA_DIR, SOURCE_FILES, load_json
from .generate import build_rows
from .rules import is_active, occurrence

GOVUK_URL = "https://www.gov.uk/bank-holidays.json"
GOVUK_DIVISIONS = {
    "england_and_wales": "england-and-wales",
    "scotland": "scotland",
    "northern_ireland": "northern-ireland",
}


def validate_source(data: dict) -> tuple[list[str], list[str]]:
    """Return ``(errors, warnings)``. Errors are structural; warnings are missing citations."""
    errors: list[str] = []
    warnings: list[str] = []
    for name in SOURCE_FILES:
        schema = load_json(SCHEMA_DIR / f"{name}.schema.json")
        for err in Draft202012Validator(schema).iter_errors(data[name]):
            path = "/".join(str(p) for p in err.absolute_path)
            errors.append(f"{name}.json: {path}: {err.message}")
    if errors:
        return errors, warnings

    sources = data["sources"]
    rule_ids = [r["rule_id"] for r in data["rules"]]
    proc_ids = [p["proclamation_id"] for p in data["proclamations"]]
    for label, ids in (("rule_id", rule_ids), ("proclamation_id", proc_ids)):
        for dup in sorted({i for i in ids if ids.count(i) > 1}):
            errors.append(f"duplicate {label}: {dup}")
    for dup in sorted(set(rule_ids) & set(proc_ids)):
        errors.append(f"id used for both a rule and a proclamation: {dup}")

    rules = {r["rule_id"]: r for r in data["rules"]}
    for item_type, items in (
        ("rule", data["rules"]),
        ("proclamation", data["proclamations"]),
        ("override", data["overrides"]),
    ):
        for item in items:
            label = f"{item_type} {item.get('rule_id') or item.get('proclamation_id')}"
            if item_type == "override":
                label += f" ({item['year']})"
            missing = [s for s in item["source_ids"] if s not in sources]
            if missing:
                errors.append(f"{label}: unknown source ids {missing}")
            archived = [s for s in item["source_ids"] if sources.get(s, {}).get("archive_url")]
            if item["verified"] and not archived:
                errors.append(f"{label}: marked verified but no cited source has an archive_url")
            if not item["verified"]:
                warnings.append(f"{label}: not yet verified against a primary source")
            elif not item["source_ids"]:
                errors.append(f"{label}: verified but has no sources")

    for o in data["overrides"]:
        if o["rule_id"] not in rules:
            errors.append(f"override for unknown rule {o['rule_id']}")
        elif not is_active(rules[o["rule_id"]], o["year"]):
            errors.append(f"override {o['rule_id']} {o['year']}: rule is not active in that year")
        if date.fromisoformat(o["date"]).year != o["year"]:
            errors.append(f"override {o['rule_id']} {o['year']}: date {o['date']} is in a different year")
    for p in data["proclamations"]:
        try:
            date.fromisoformat(p["date"])
        except ValueError:
            errors.append(f"proclamation {p['proclamation_id']}: invalid date {p['date']}")
    for rule in data["rules"]:
        try:
            occurrence(rule, rule["valid_from_year"] or 1871)
        except (KeyError, ValueError) as exc:
            errors.append(f"rule {rule['rule_id']}: cannot be evaluated ({exc!r})")
    for source_id, source in sources.items():
        if not source["archive_url"] and source["url"]:
            warnings.append(f"source {source_id}: no archive_url (run `archive-links`)")
    return errors, warnings


def check_output(rows: list[dict]) -> list[str]:
    """Sanity checks on generated rows: unique keys and at most one holiday per region per day."""
    errors = []
    seen = set()
    per_region: dict[tuple[str, str], str] = {}
    for row in rows:
        key = (row["holiday_date"], row["rule_id"])
        if key in seen:
            errors.append(f"duplicate row {key}")
        seen.add(key)
        for region in REGIONS:
            if row[region]:
                other = per_region.setdefault((row["holiday_date"], region), row["rule_id"])
                if other != row["rule_id"]:
                    errors.append(f"{row['holiday_date']} {region}: both {other} and {row['rule_id']}")
    return errors


def load_govuk(location: str | None = None) -> dict:
    if location and not location.startswith(("http://", "https://")):
        with open(location, encoding="utf-8") as handle:
            return json.load(handle)
    with urllib.request.urlopen(location or GOVUK_URL, timeout=30) as response:  # noqa: S310
        return json.load(response)


def compare_govuk(data: dict, feed: dict, from_year: int = 2010) -> list[str]:
    """Differences between our generated dates and the GOV.UK feed, per region."""
    differences = []
    for region, division in GOVUK_DIVISIONS.items():
        events = feed[division]["events"]
        theirs = {e["date"] for e in events if int(e["date"][:4]) >= from_year}
        if not theirs:
            continue
        last = max(int(d[:4]) for d in theirs)
        ours = {r["holiday_date"] for r in build_rows(data, from_year, last) if r[region]}
        for d in sorted(ours - theirs):
            differences.append(f"{region}: {d} generated but not in GOV.UK feed")
        for d in sorted(theirs - ours):
            differences.append(f"{region}: {d} in GOV.UK feed but not generated")
    return differences
