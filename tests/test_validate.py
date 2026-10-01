import copy

from uk_bank_holidays import archive, validate


def test_shipped_data_has_no_errors(data):
    errors, _ = validate.validate_source(data)
    assert errors == []


def test_detects_unknown_source_and_bad_override(data):
    broken = copy.deepcopy(data)
    broken["rules"][0]["source_ids"].append("nope")
    broken["overrides"].append(
        {"rule_id": "may_day", "year": 1900, "date": "1901-05-01", "reason": "x", "source_ids": [], "verified": False}
    )
    errors, _ = validate.validate_source(broken)
    assert any("unknown source ids" in e for e in errors)
    assert any("not active" in e for e in errors)


def test_verified_requires_archive_link(data):
    broken = copy.deepcopy(data)
    broken["proclamations"][0]["verified"] = True
    errors, _ = validate.validate_source(broken)
    assert any("no cited source has an archive_url" in e for e in errors)
    broken["sources"]["bfda_1971"]["archive_url"] = "https://web.archive.org/web/2024/https://example.org/"
    errors, _ = validate.validate_source(broken)
    assert errors == []


def test_schema_violation_is_reported(data):
    broken = copy.deepcopy(data)
    broken["rules"][0]["scotland"] = "yes"
    errors, _ = validate.validate_source(broken)
    assert any(e.startswith("rules.json") for e in errors)


def test_compare_with_govuk_feed(data):
    # A tiny stand-in for the GOV.UK feed covering 2019, which our data must match exactly.
    from uk_bank_holidays.generate import build_rows

    rows = build_rows(data, 2019, 2019)
    feed = {
        division: {"events": [{"date": r["holiday_date"], "title": r["holiday_name"]} for r in rows if r[region]]}
        for region, division in validate.GOVUK_DIVISIONS.items()
    }
    assert validate.compare_govuk(data, feed, from_year=2019) == []
    feed["scotland"]["events"].pop()
    feed["england-and-wales"]["events"].append({"date": "2019-02-02", "title": "Extra"})
    differences = validate.compare_govuk(data, feed, from_year=2019)
    assert len(differences) == 2


def test_archive_links_fill_missing_only():
    sources = {
        "a": {"title": "A", "publisher": "", "url": "https://example.org/a", "archive_url": None, "accessed": None},
        "b": {
            "title": "B",
            "publisher": "",
            "url": "https://example.org/b",
            "archive_url": "https://web.archive.org/web/1/https://example.org/b",
            "accessed": "2024-01-01",
        },
        "c": {"title": "C", "publisher": "", "url": None, "archive_url": None, "accessed": None},
    }
    log = archive.update_sources(
        sources, fetch=lambda url: "https://web.archive.org/web/2/" + url, capture=lambda url: None
    )
    assert sources["a"]["archive_url"] == "https://web.archive.org/web/2/https://example.org/a"
    assert sources["b"]["archive_url"].startswith("https://web.archive.org/web/1/")
    assert sources["c"]["archive_url"] is None
    assert len(log) == 1


def test_check_links_reports_failures():
    sources = {
        "ok": {"title": "", "publisher": "", "url": "https://example.org/ok", "archive_url": None, "accessed": None},
        "bad": {"title": "", "publisher": "", "url": "https://example.org/bad", "archive_url": None, "accessed": None},
        "offline": {"title": "", "publisher": "", "url": None, "archive_url": None, "accessed": None},
    }

    def fake(url):
        if url.endswith("bad"):
            raise OSError("404")

    failures = archive.check_links(sources, open_url=fake)
    assert len(failures) == 1 and failures[0].startswith("bad.url")
