import pytest

from uk_bank_holidays.data import load_source
from uk_bank_holidays.generate import build_rows


@pytest.fixture(scope="session")
def data():
    return load_source()


@pytest.fixture(scope="session")
def rows(data):
    return build_rows(data, 1871, 2035)


def dates(rows, region, rule_id=None):
    return [r["holiday_date"] for r in rows if r[region] and (rule_id is None or r["rule_id"] == rule_id)]
