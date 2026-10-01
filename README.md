# UK Bank Holidays

Open, cited data for UK bank holidays in England & Wales, Scotland and Northern Ireland, plus the code that
generates it. Rules and royal proclamations live in hand-curated JSON; the dataset (JSON and CSV) and re-runnable
SQL scripts for several database engines are generated from them.

It started life as the blog post [UK Bank Holidays](https://aerox.uk/2019/04/02/UK-Bank-Holidays/).

> **Status: first draft.** The rules were transcribed from the blog post and nothing is marked `verified` yet.
> Every item still needs a primary source with an archive.org link (see [docs/contributing.md](docs/contributing.md)).
> Compare against GOV.UK with `python -m uk_bank_holidays validate --compare-govuk` before relying on it.

## Use the generator for your own date range

The files in [`data/`](data) and [`sql/`](sql) are committed for convenience and cover 1871 to 2035. Most people
need far less. Generating just the years and region you need keeps files and tables small and means you are never
tied to the committed copy:

```bash
pip install git+https://github.com/AeroXuk/uk-bank-holidays      # or: pip install -e . in a clone

# JSON + CSV for 2024 to 2030, Scotland only
uk-bank-holidays generate --start-year 2024 --end-year 2030 --region scotland --output-dir out

# A re-runnable Snowflake script for England & Wales, 2020 to 2030
uk-bank-holidays sql --dialect snowflake --region england_and_wales --start-year 2020 --end-year 2030 \
    --schema reference --output-dir out/sql
```

(`python -m uk_bank_holidays ...` works too.)

## What is in the repository

| Path | What |
|---|---|
| `src/uk_bank_holidays/source/*.json` | The master data: `rules`, `proclamations`, `overrides` (moved dates) and `sources` (citations) |
| `data/uk_bank_holidays.{json,csv}` | Generated: one row per (date, rule) with a true/false flag per region |
| `data/uk_bank_holidays_<region>.{json,csv}` | Generated: the same, for one region (`england_and_wales`, `scotland`, `northern_ireland`) |
| `data/uk_bank_holiday_rules.*`, `uk_bank_holiday_sources.*` | The rules and citations as datasets |
| `sql/<dialect>/` | Generated, re-runnable scripts for `mssql`, `snowflake`, `postgres`, `mysql`, `bigquery`, `sqlite` |
| `docs/` | Documentation, including generated reference pages |

JSON is the master format and carries the detail (`source_ids` per row). The CSV files are derived from it, with
lists joined by `;` and booleans as `true`/`false`, for systems that handle JSON poorly.

## Documentation

- [Overview and quick start](docs/index.md)
- [Data dictionary](docs/data-dictionary.md)
- [Regions](docs/regions.md)
- [Rules and how dates are calculated](docs/rules-and-calculations.md)
- [SQL scripts](docs/sql.md)
- [Contributing](docs/contributing.md)
- Generated: [rules](docs/generated/rules.md), [proclamations](docs/generated/proclamations.md), [sources](docs/generated/sources.md)

## Development

```bash
pip install -e .[dev]
pytest
ruff check . && ruff format --check .
python -m uk_bank_holidays generate && python -m uk_bank_holidays sql --dialect all && python -m uk_bank_holidays docs
```

CI fails if the committed `data/`, `sql/` and `docs/generated/` are out of date with the source data.

## Licence

Code and data in this repository are MIT licensed (see [LICENSE](LICENSE)). The underlying facts come from UK
legislation and government publications, which are Crown copyright and published under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
