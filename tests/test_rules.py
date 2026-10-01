from datetime import date

import pytest

from uk_bank_holidays.easter import easter_sunday
from uk_bank_holidays.rules import occurrence

from .conftest import dates


@pytest.mark.parametrize(
    "year,expected",
    [
        (1871, date(1871, 4, 9)),
        (1961, date(1961, 4, 2)),
        (2000, date(2000, 4, 23)),
        (2019, date(2019, 4, 21)),
        (2024, date(2024, 3, 31)),
        (2025, date(2025, 4, 20)),
        (2038, date(2038, 4, 25)),
    ],
)
def test_easter_sunday(year, expected):
    assert easter_sunday(year) == expected


def rule(**kwargs):
    return {"rule_id": "x", "parameters": {}, **kwargs}


def test_rule_types():
    assert occurrence(rule(rule_type="fixed_date", parameters={"month": 12, "day": 25}), 2019) == date(2019, 12, 25)
    assert occurrence(
        rule(rule_type="nth_weekday", parameters={"month": 5, "weekday": "monday", "n": 1}), 2019
    ) == date(2019, 5, 6)
    assert occurrence(rule(rule_type="last_weekday", parameters={"month": 5, "weekday": "monday"}), 2019) == date(
        2019, 5, 27
    )
    assert occurrence(rule(rule_type="easter_offset", parameters={"days": -2}), 2019) == date(2019, 4, 19)
    assert occurrence(rule(rule_type="easter_offset", parameters={"days": 50}), 1970) == date(1970, 5, 18)
    after_last_saturday = rule(
        rule_type="weekday_after_last_weekday",
        parameters={"month": 8, "after_weekday": "saturday", "weekday": "monday"},
    )
    assert occurrence(after_last_saturday, 1965) == date(1965, 8, 30)  # last Saturday 28 Aug
    assert occurrence(after_last_saturday, 1966) == date(1966, 8, 29)  # last Saturday 27 Aug
    assert occurrence(after_last_saturday, 1968) == date(1968, 9, 2)  # last Saturday is 31 Aug


def test_unknown_rule_type():
    with pytest.raises(ValueError):
        occurrence(rule(rule_type="nope"), 2000)


def test_moved_dates(rows):
    assert "1995-05-08" in dates(rows, "england_and_wales", "may_day")
    assert "1995-05-01" not in dates(rows, "england_and_wales")
    assert "2002-06-04" in dates(rows, "scotland", "spring_bank_holiday")
    assert "2002-05-27" not in dates(rows, "scotland")
    assert "2002-06-03" in dates(rows, "scotland", "golden_jubilee_2002")
    assert "2022-06-02" in dates(rows, "northern_ireland", "spring_bank_holiday")
    assert "2022-09-19" in dates(rows, "england_and_wales", "state_funeral_2022")


def test_regional_holidays(rows):
    assert all(
        r["northern_ireland"] and not r["scotland"] and not r["england_and_wales"]
        for r in rows
        if r["rule_id"] == "st_patricks_day"
    )
    scotland_only = {
        r["holiday_key"] for r in rows if r["scotland"] and not r["england_and_wales"] and not r["northern_ireland"]
    }
    assert {"st_andrews_day", "new_year_holiday"} <= scotland_only
    assert min(r["holiday_date"] for r in rows if r["rule_id"] == "st_andrews_day") >= "2007"


def test_substitute_days(rows):
    # 2021: 25 and 26 December were Saturday and Sunday
    christmas_2021 = {r["holiday_date"]: r for r in rows if r["holiday_date"].startswith("2021-12-2")}
    assert set(christmas_2021) == {"2021-12-27", "2021-12-28"}
    assert all(r["is_substitute"] for r in christmas_2021.values())
    # 2022: 1 January was a Saturday, 2 January a Sunday
    new_year = [r for r in rows if r["holiday_date"].startswith("2022-01")]
    assert {(r["holiday_date"], r["rule_id"]) for r in new_year if r["scotland"]} == {
        ("2022-01-03", "new_years_day"),
        ("2022-01-04", "new_year_holiday"),
    }
    # 2023: 1 January was a Sunday. England/Wales get Monday 2nd; Scotland gets the 3rd as the 2nd is taken
    jan_2023 = {
        (r["holiday_date"], r["rule_id"], r["england_and_wales"], r["scotland"])
        for r in rows
        if r["holiday_date"].startswith("2023-01")
    }
    assert ("2023-01-02", "new_years_day", True, False) in jan_2023
    assert ("2023-01-03", "new_years_day", False, True) in jan_2023
    # Before 1971 nothing is moved
    assert all(not r["is_substitute"] for r in rows if r["holiday_date"] < "1971")


def test_no_substitutes_option(data):
    from uk_bank_holidays.generate import build_rows

    plain = build_rows(data, 2021, 2021, substitutes=False)
    assert "2021-12-25" in dates(plain, "england_and_wales")
    assert not any(r["is_substitute"] for r in plain)


def test_one_holiday_per_region_per_day(rows):
    from uk_bank_holidays.validate import check_output

    assert check_output(rows) == []


def test_future_easter_holidays_are_weekdays(rows):
    import datetime

    for r in rows:
        if r["rule_id"] in ("good_friday", "easter_monday", "may_day", "spring_bank_holiday"):
            assert datetime.date.fromisoformat(r["holiday_date"]).weekday() < 5
