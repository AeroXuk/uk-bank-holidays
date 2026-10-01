"""Write the generated datasets (JSON master; CSV derived from it)."""

import csv
import json
from pathlib import Path

from .data import REGIONS
from .generate import build_rows, filter_region

CSV_RULE_COLUMNS = [
    "rule_id",
    "holiday_key",
    "name",
    "valid_from_year",
    "valid_to_year",
    "rule_type",
    "parameters",
    *REGIONS,
    "notes",
    "source_ids",
    "verified",
]


def _csv_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ";".join(str(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    return value


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_csv_value(row.get(c)) for c in columns])


def write_all(
    data: dict,
    out_dir: Path,
    start_year: int,
    end_year: int,
    regions=None,
    substitutes: bool = True,
    formats=("json", "csv"),
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows(data, start_year, end_year, substitutes)
    written = []

    def emit(stem: str, json_payload, csv_rows, csv_columns):
        if "json" in formats:
            write_json(out_dir / f"{stem}.json", json_payload)
            written.append(out_dir / f"{stem}.json")
        if "csv" in formats:
            write_csv(out_dir / f"{stem}.csv", csv_rows, csv_columns)
            written.append(out_dir / f"{stem}.csv")

    all_columns = [c for c in rows[0].keys()] if rows else []
    if regions is None:
        emit("uk_bank_holidays", rows, rows, all_columns)
    for region in regions or REGIONS:
        regional = filter_region(rows, region)
        columns = [c for c in all_columns if c not in REGIONS]
        emit(f"uk_bank_holidays_{region}", regional, regional, columns)
    if regions is None:
        emit("uk_bank_holiday_rules", data["rules"], data["rules"], CSV_RULE_COLUMNS)
        source_rows = [{"source_id": k, **v} for k, v in data["sources"].items()]
        emit(
            "uk_bank_holiday_sources",
            source_rows,
            source_rows,
            ["source_id", "title", "publisher", "url", "archive_url", "accessed"],
        )
    return written
