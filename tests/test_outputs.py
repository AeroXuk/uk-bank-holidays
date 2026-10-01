import csv
import json

from uk_bank_holidays import output
from uk_bank_holidays.data import REGIONS


def test_json_is_master_and_csv_matches(data, tmp_path):
    output.write_all(data, tmp_path, 1990, 2030)
    master = json.loads((tmp_path / "uk_bank_holidays.json").read_text(encoding="utf-8"))
    with open(tmp_path / "uk_bank_holidays.csv", newline="", encoding="utf-8") as handle:
        flat = list(csv.DictReader(handle))
    assert len(master) == len(flat) > 0
    for json_row, csv_row in zip(master, flat, strict=True):
        assert json_row["holiday_date"] == csv_row["holiday_date"]
        assert json_row["rule_id"] == csv_row["rule_id"]
        for region in REGIONS:
            assert csv_row[region] == ("true" if json_row[region] else "false")
        assert csv_row["source_ids"] == ";".join(json_row["source_ids"])
    assert isinstance(master[0]["england_and_wales"], bool)


def test_region_files_only_hold_that_region(data, tmp_path):
    output.write_all(data, tmp_path, 1990, 2030)
    full = json.loads((tmp_path / "uk_bank_holidays.json").read_text(encoding="utf-8"))
    for region in REGIONS:
        regional = json.loads((tmp_path / f"uk_bank_holidays_{region}.json").read_text(encoding="utf-8"))
        assert [r["holiday_date"] for r in regional] == [r["holiday_date"] for r in full if r[region]]
        assert not any(set(REGIONS) & set(r) for r in regional)
        assert (tmp_path / f"uk_bank_holidays_{region}.csv").exists()


def test_region_option_only_writes_that_region(data, tmp_path):
    written = output.write_all(data, tmp_path, 2020, 2022, regions=["scotland"])
    assert {p.name for p in written} == {"uk_bank_holidays_scotland.json", "uk_bank_holidays_scotland.csv"}


def test_generation_is_deterministic(data, tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    output.write_all(data, first, 1871, 2035)
    output.write_all(data, second, 1871, 2035)
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes()


def test_custom_range(data, tmp_path):
    output.write_all(data, tmp_path, 2024, 2024)
    rows = json.loads((tmp_path / "uk_bank_holidays.json").read_text(encoding="utf-8"))
    assert {r["holiday_date"][:4] for r in rows} == {"2024"}
