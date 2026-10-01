# UK Bank Holidays: overview

"Bank holiday" is the everyday term for both bank and public holidays in the UK. Reporting on activity by weekday,
weekend and bank holiday is awkward because the rules differ by nation and have changed many times since 1871.

This project models those rules as data, then generates:

1. a dataset with one row per holiday occurrence, as JSON (master) and CSV,
2. one file per region,
3. re-runnable SQL scripts for common database engines.

## How it fits together

```
src/uk_bank_holidays/source/        hand-curated, cited, schema-validated
  rules.json  proclamations.json  overrides.json  sources.json
            |
            |  python -m uk_bank_holidays generate / sql / docs
            v
data/*.json  ->  data/*.csv         JSON is the master, CSV is derived from it
sql/<dialect>/*.sql                 staged upserts, safe to re-run
docs/generated/*.md                 reference pages built from the same data
```

## Quick start

```bash
pip install -e .
python -m uk_bank_holidays validate          # check the source data
python -m uk_bank_holidays generate --start-year 2024 --end-year 2030 --output-dir out
python -m uk_bank_holidays sql --dialect mssql --start-year 2024 --end-year 2030 --output-dir out/sql
```

Prefer generating your own range to using the committed files in `data/` and `sql/`: you only carry the years and
region you need, and you can regenerate whenever the rules change.

All commands accept `--source-dir` to point at your own copy of the four source JSON files.

## Commands

| Command | Purpose |
|---|---|
| `generate` | Write the JSON/CSV datasets (`--start-year`, `--end-year`, `--region`, `--format`, `--output-dir`, `--no-substitutes`) |
| `sql` | Write SQL scripts (`--dialect`, `--schema`, `--table`, `--region`, `--prune`, plus the range options) |
| `validate` | Schema and consistency checks; `--strict` fails on unverified items; `--compare-govuk [URL_OR_FILE]` diffs against the GOV.UK feed |
| `docs` | Regenerate `docs/generated/` |
| `archive-links` | Fill missing `archive_url` values from the Wayback Machine (`--save` requests new captures) |
| `check-links` | Check that every cited URL and archive link still resolves |

## Further reading

[Data dictionary](data-dictionary.md) | [Regions](regions.md) | [Rules and calculations](rules-and-calculations.md) |
[SQL scripts](sql.md) | [Contributing](contributing.md) | [Changelog](changelog.md)
