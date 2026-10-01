# SQL scripts

`python -m uk_bank_holidays sql --dialect <name>` writes scripts into `sql/<dialect>/` (change with `--output-dir`).

| Dialect | Notes |
|---|---|
| `mssql` | `GO` batch separators, `MERGE`, temp table `#bank_holidays_stage`; also `03_easter_function.sql` |
| `snowflake` | `MERGE`, temporary staging table |
| `postgres` | `INSERT ... ON CONFLICT DO UPDATE`, temporary staging table |
| `mysql` | `INSERT ... ON DUPLICATE KEY UPDATE` (uses `VALUES()`, deprecated but still supported in MySQL 8) |
| `bigquery` | `MERGE`, temp table (run as a script); the primary key is `NOT ENFORCED` |
| `sqlite` | `INSERT ... ON CONFLICT DO UPDATE` (SQLite 3.24+) |

Options: `--schema`, `--table` (default `bank_holidays`), `--region`, `--start-year`, `--end-year`,
`--no-substitutes`, `--prune`.

## Files

1. `01_create_tables.sql`: creates the schema (if you set one) and the table if they do not exist.
2. `02_load_data.sql`: loads the rows into a temporary staging table, upserts them into the table, drops the staging table.
3. `03_easter_function.sql` (MSSQL only): `CREATE OR ALTER FUNCTION CalculateEasterDay(@Year int)`.

## Re-running is safe

- Tables are created with `IF NOT EXISTS` (or the MSSQL `OBJECT_ID` equivalent), so existing data is untouched.
- Rows are upserted on the primary key `(holiday_date, rule_id)`: missing rows are added, changed rows are updated,
  nothing is duplicated.
- Rows that are not in the script are **not** deleted, so rows you added yourself survive. Use `--prune` to also delete
  rows inside the script's year range that are no longer in the generated data. Rows outside the range are always left
  alone. If you combine `--prune` with `--region`, rows for the other regions inside the range are removed too.
- The staging table is temporary and only ever referenced by its temp name (`pg_temp.`, `temp.`, `#`).

## Table

| Column | MSSQL | Snowflake / Postgres / MySQL | BigQuery | SQLite |
|---|---|---|---|---|
| `holiday_date` | `date` | `DATE` | `DATE` | `TEXT` (ISO date) |
| `rule_id`, `holiday_key` | `nvarchar(100)` | `VARCHAR(100)` | `STRING` | `TEXT` |
| `holiday_name` | `nvarchar(200)` | `VARCHAR(200)` | `STRING` | `TEXT` |
| `holiday_type` | `nvarchar(20)` | `VARCHAR(20)` | `STRING` | `TEXT` |
| region flags, `is_substitute` | `bit` | `BOOLEAN` | `BOOL` | `INTEGER` |
| `notes`, `source_ids` | `nvarchar(500)` NULL | `VARCHAR(500)` NULL | `STRING` NULL | `TEXT` NULL |

## Testing status

The SQLite and PostgreSQL scripts are exercised by the test suite (SQLite always; PostgreSQL when `UKBH_PG_ARGS` is
set, e.g. `UKBH_PG_ARGS="-h localhost -U postgres"`). The MSSQL, Snowflake, MySQL and BigQuery scripts are rendered
and checked for structure but have **not** been run against a real server yet. Treat them as untested until you have
run them, and please report problems.

## Adding a dialect

Add a `Dialect` entry in `src/uk_bank_holidays/sql.py` (quoting, types, literals, batch size) and a branch in
`templates/sql/load_data.sql.j2` for its staging and upsert syntax. Add a case to `tests/test_sql.py`.
