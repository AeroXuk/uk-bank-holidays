# Contributing

## Changing the data

Edit the JSON in `src/uk_bank_holidays/source/`, never the generated files. Then:

```bash
python -m uk_bank_holidays validate
python -m uk_bank_holidays generate
python -m uk_bank_holidays sql --dialect all
python -m uk_bank_holidays docs
pytest
```

### Adding a royal proclamation

1. Add an entry to `proclamations.json` with a readable `proclamation_id` (`coronation_2023`), the date, name, reason and region flags.
2. Add its citation(s) to `sources.json`, **preferring `gov.uk` domains** (legislation.gov.uk, The Gazette, GOV.UK pages), and list the ids in `source_ids`. Fall back to other authoritative sources only if there is no GOV.UK page.
3. Run `python -m uk_bank_holidays archive-links` (add `--save` to request a capture) so every source has a web.archive.org `archive_url`.
4. Set `verified` to `true`. `validate` refuses `verified: true` unless a cited source has an `archive_url`.

If the proclamation moves a recurring holiday (such as the 2022 Spring Bank Holiday), add an entry to `overrides.json`
instead of, or as well as, a proclamation for any extra day.

### Adding or changing a rule

Pick a `rule_type` from [rules and calculations](rules-and-calculations.md), give the rule a readable id
(`<holiday>_<from>_<to>` when a holiday changes over time), set the year range and region flags, cite a source for the
calculation, and add a test if you introduce a new rule type.

## Current gaps

- Nothing is `verified` yet: no archive links have been recorded and the proclamation sources point at the Act that
  grants the power, not at the individual proclamation. The Gazette or legislation.gov.uk notice for each still needs
  to be found.
- The 2012, 2020 and 2022 moved dates and the 2022-2023 proclamations were added from general knowledge rather than from the
  blog post; they are flagged in their `notes`.
- Whit Monday between 1965 and 1970 may have been moved to the last Monday of May (noted in the blog post, not modelled).
- `validate --compare-govuk` has only been tested against a small stand-in for the feed.

## Checks

CI runs `ruff`, `pytest`, and regenerates `data/`, `sql/` and `docs/generated/`, failing if anything changed. A weekly
workflow compares the output with the GOV.UK feed and checks that source and archive links still resolve.
