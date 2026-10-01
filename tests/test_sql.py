import os
import shutil
import sqlite3
import subprocess

import pytest

from uk_bank_holidays import sql
from uk_bank_holidays.generate import build_rows


@pytest.fixture(scope="module")
def rows(data):
    return build_rows(data, 1990, 2030)


@pytest.mark.parametrize("dialect", sorted(sql.DIALECTS))
def test_every_dialect_renders(dialect, rows):
    scripts = sql.render_scripts(dialect, rows, 1990, 2030)
    assert {"01_create_tables.sql", "02_load_data.sql"} <= set(scripts)
    load = scripts["02_load_data.sql"]
    assert "holiday_date" in load and "Christmas Day" in load
    assert "DELETE FROM" not in load  # no pruning unless asked
    assert "DELETE FROM" in sql.render_scripts(dialect, rows, 1990, 2030, prune=True)["02_load_data.sql"]


def test_mssql_specifics(rows):
    scripts = sql.render_scripts("mssql", rows, 1990, 2030, schema="ref", table="uk_holidays")
    assert "IF SCHEMA_ID(N'ref') IS NULL" in scripts["01_create_tables.sql"]
    assert "IF OBJECT_ID(N'[ref].[uk_holidays]', N'U') IS NULL" in scripts["01_create_tables.sql"]
    assert "MERGE INTO [ref].[uk_holidays]" in scripts["02_load_data.sql"]
    assert "CREATE OR ALTER FUNCTION [ref].[CalculateEasterDay]" in scripts["03_easter_function.sql"]
    insert_blocks = scripts["02_load_data.sql"].count("INSERT INTO")
    assert insert_blocks == -(-len(rows) // 1000)  # batches of at most 1000 rows


def test_quotes_are_escaped(rows):
    assert "N'New Year''s Day'" in sql.render_scripts("mssql", rows, 1990, 2030)["02_load_data.sql"]
    assert "'New Year''s Day'" in sql.render_scripts("snowflake", rows, 1990, 2030)["02_load_data.sql"]


def _run_sqlite(db, scripts):
    db.executescript(scripts["01_create_tables.sql"])
    db.executescript(scripts["02_load_data.sql"])


def test_sqlite_scripts_are_repeatable(rows):
    scripts = sql.render_scripts("sqlite", rows, 1990, 2030)
    db = sqlite3.connect(":memory:")
    _run_sqlite(db, scripts)
    count = db.execute("select count(*) from bank_holidays").fetchone()[0]
    assert count == len(rows)
    _run_sqlite(db, scripts)
    assert db.execute("select count(*) from bank_holidays").fetchone()[0] == count  # no duplicates

    db.execute("delete from bank_holidays where holiday_date = '2022-09-19'")
    db.execute("update bank_holidays set holiday_name = 'wrong' where rule_id = 'christmas_day'")
    db.execute("insert into bank_holidays values ('2099-01-01','mine','mine','Mine','recurring',1,1,1,0,NULL,NULL)")
    _run_sqlite(db, scripts)
    assert db.execute("select count(*) from bank_holidays where holiday_date = '2022-09-19'").fetchone()[0] == 1
    assert db.execute("select count(*) from bank_holidays where holiday_name = 'wrong'").fetchone()[0] == 0
    assert db.execute("select count(*) from bank_holidays where rule_id = 'mine'").fetchone()[0] == 1  # kept
    assert db.execute("select count(*) from sqlite_temp_master").fetchone()[0] == 0  # staging dropped


def test_sqlite_prune_only_touches_the_generated_range(rows):
    scripts = sql.render_scripts("sqlite", rows, 1990, 2030, prune=True)
    db = sqlite3.connect(":memory:")
    _run_sqlite(db, scripts)
    db.execute("insert into bank_holidays values ('2000-01-05','in_range','x','X','recurring',1,1,1,0,NULL,NULL)")
    db.execute("insert into bank_holidays values ('2099-01-01','out_of_range','x','X','recurring',1,1,1,0,NULL,NULL)")
    db.executescript(scripts["02_load_data.sql"])
    left = {r[0] for r in db.execute("select rule_id from bank_holidays where rule_id like '%range'")}
    assert left == {"out_of_range"}


@pytest.mark.skipif(
    not (shutil.which("psql") and os.environ.get("UKBH_PG_ARGS")),
    reason="set UKBH_PG_ARGS (psql connection arguments) to test against PostgreSQL",
)
def test_postgres_scripts_are_repeatable(rows, tmp_path):
    scripts = sql.render_scripts("postgres", rows, 1990, 2030, schema="ukbh_test")
    args = ["psql", *os.environ["UKBH_PG_ARGS"].split(), "-v", "ON_ERROR_STOP=1", "-q", "-t", "-A"]

    def psql(command=None, script=None):
        if script is not None:
            path = tmp_path / "script.sql"
            path.write_text(script, encoding="utf-8")
            command_args = ["-f", str(path)]
        else:
            command_args = ["-c", command]
        done = subprocess.run([*args, *command_args], capture_output=True, text=True, check=True)
        return done.stdout.strip()

    try:
        for _ in range(2):
            psql(script=scripts["01_create_tables.sql"])
            psql(script=scripts["02_load_data.sql"])
        assert int(psql("select count(*) from ukbh_test.bank_holidays")) == len(rows)
        psql("delete from ukbh_test.bank_holidays where holiday_date = '2022-09-19'")
        psql(script=scripts["02_load_data.sql"])
        assert int(psql("select count(*) from ukbh_test.bank_holidays")) == len(rows)
    finally:
        psql("drop schema if exists ukbh_test cascade")
