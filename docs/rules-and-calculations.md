# Rules and calculations

Each recurring rule has a `rule_type` and `parameters`. The full list of rules is in the
[generated rules page](generated/rules.md).

| `rule_type` | Parameters | Meaning |
|---|---|---|
| `fixed_date` | `month`, `day` | The same calendar date every year (e.g. 25 December) |
| `nth_weekday` | `month`, `weekday`, `n` | The n-th given weekday of the month (first Monday of May) |
| `last_weekday` | `month`, `weekday` | The last given weekday of the month (last Monday of August) |
| `easter_offset` | `days` | Easter Sunday plus or minus a number of days (Good Friday is -2, Easter Monday +1, Whit Monday +50) |
| `weekday_after_last_weekday` | `month`, `after_weekday`, `weekday` | First `weekday` after the last `after_weekday` of the month (1965-1970 August bank holiday) |

## Easter

Easter Sunday uses the Anonymous Gregorian algorithm (Meeus/Jones/Butcher), a port of the T-SQL function from the
original blog post (`src/uk_bank_holidays/easter.py`; the MSSQL script `03_easter_function.sql` carries the T-SQL
version). It is valid for the Gregorian calendar (1583 onwards), so it covers the whole dataset.

References:

- [Computus: Anonymous Gregorian algorithm](https://en.wikipedia.org/wiki/Computus#Anonymous_Gregorian_algorithm)
- Jean Meeus, *Astronomical Algorithms* (2nd ed., 1998), chapter 8

## Moved dates

An entry in `overrides.json` replaces the calculated date of one rule in one year (for example May Day 1995, moved to
8 May for the 50th anniversary of VE Day). The generated row has `holiday_type = moved`. The old date is not emitted.

## Substitute days

From 1971, a fixed-date holiday that falls on a Saturday or Sunday moves to the next weekday that is not already a
holiday in that region (so Christmas on a Saturday and Boxing Day on a Sunday become Monday 27th and Tuesday 28th).
Rows get `is_substitute = true`. Easter-based and weekday-based holidays are never on weekends. Before 1971 nothing is
moved. Pass `--no-substitutes` to turn this off.

This follows the Banking and Financial Dealings Act 1971 as understood from GOV.UK's published dates; confirm with
`validate --compare-govuk`.

## Authoritative references

- [Banking and Financial Dealings Act 1971](https://www.legislation.gov.uk/ukpga/1971/80) and its
  [Schedule 1](https://www.legislation.gov.uk/ukpga/1971/80/schedule/1) (the holidays and the power to proclaim extra ones)
- [UK bank holidays on GOV.UK](https://www.gov.uk/bank-holidays) and its
  [JSON feed](https://www.gov.uk/bank-holidays.json)

Archive.org links for these live in the [sources page](generated/sources.md) once `archive-links` has been run.
