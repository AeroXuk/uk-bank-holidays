# Data dictionary

## Generated holiday rows

`data/uk_bank_holidays.json` / `.csv` (and the per-region files, which drop the three region columns).
One row per (date, rule). Primary key: `holiday_date` + `rule_id`.

| Column | Type | Description |
|---|---|---|
| `holiday_date` | date (ISO 8601) | The day off |
| `rule_id` | text | The rule (e.g. `christmas_day`) or proclamation (e.g. `coronation_2023`) that produced the row |
| `holiday_key` | text | Groups a holiday across time-limited rules, e.g. `new_years_day` covers `new_years_day_1871_1973` and `new_years_day` |
| `holiday_name` | text | Display name |
| `holiday_type` | text | `recurring`, `moved` (a recurring holiday on a one-off date) or `proclamation` |
| `england_and_wales`, `scotland`, `northern_ireland` | boolean | Whether the day is a bank holiday in that region |
| `is_substitute` | boolean | The date is a substitute day because the usual date fell on a weekend |
| `notes` | text, nullable | Free text: reason for a move or proclamation, substitute explanation, caveats |
| `source_ids` | JSON: array, CSV: `;`-joined | Ids of the citations (see `uk_bank_holiday_sources`) |

The same holiday can appear on two dates in one year when regions differ, e.g. a substitute New Year's Day is
2 January in England & Wales but 3 January in Scotland (where 2 January is already a holiday). Each is its own row
with its own region flags.

## Rules (`uk_bank_holiday_rules`)

| Column | Description |
|---|---|
| `rule_id`, `holiday_key`, `name` | Identification |
| `valid_from_year`, `valid_to_year` | Inclusive. Null from = time immemorial, null to = onwards |
| `rule_type`, `parameters` | How the date is calculated, see [rules and calculations](rules-and-calculations.md) |
| `england_and_wales`, `scotland`, `northern_ireland` | Regions the rule applies to |
| `notes`, `source_ids`, `verified` | Provenance |

## Sources (`uk_bank_holiday_sources`)

`source_id`, `title`, `publisher`, `url`, `archive_url` (web.archive.org snapshot), `accessed` (date the snapshot was recorded).

## Source files

The master files in `src/uk_bank_holidays/source/` are validated against `src/uk_bank_holidays/schemas/*.schema.json`:

- `rules.json`: as above.
- `proclamations.json`: `proclamation_id`, `date`, `name`, `reason`, region flags, `notes`, `source_ids`, `verified`.
- `overrides.json`: `rule_id`, `year`, `date`, `reason`, `notes`, `source_ids`, `verified`. Replaces the calculated date for one rule in one year.
- `sources.json`: citations keyed by id.

Ids are lower-case snake_case and human readable.
