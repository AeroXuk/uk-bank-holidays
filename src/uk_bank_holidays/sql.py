"""Render re-runnable SQL scripts (create table, upsert load) for several SQL engines."""

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .data import PACKAGE_DIR, REGIONS

TEMPLATE_DIR = PACKAGE_DIR / "templates" / "sql"

# (column, type key, length, nullable)
COLUMNS = [
    ("holiday_date", "date", None, False),
    ("rule_id", "string", 100, False),
    ("holiday_key", "string", 100, False),
    ("holiday_name", "string", 200, False),
    ("holiday_type", "string", 20, False),
    *[(region, "bool", None, False) for region in REGIONS],
    ("is_substitute", "bool", None, False),
    ("notes", "string", 500, True),
    ("source_ids", "string", 500, True),
]
KEY = ("holiday_date", "rule_id")


@dataclass(frozen=True)
class Dialect:
    name: str
    quote_open: str
    quote_close: str
    types: dict
    date_literal: str  # format string with {}
    true: str
    false: str
    default_schema: str | None = None
    batch_size: int = 1000
    backslash_escapes: bool = False
    batch_separator: str | None = None
    schemas: bool = True
    easter_function: bool = False
    stage_prefix: str = ""  # makes sure we only ever touch the temporary staging table

    def quote(self, name: str) -> str:
        return f"{self.quote_open}{name}{self.quote_close}"

    def qualified(self, schema: str | None, table: str) -> str:
        parts = ([schema] if schema else []) + [table]
        return ".".join(self.quote(p) for p in parts)

    def column_type(self, kind: str, length: int | None) -> str:
        template = self.types[kind]
        return template.format(n=length) if length else template

    def literal(self, value) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return self.true if value else self.false
        text = str(value)
        if self.backslash_escapes:
            text = text.replace("\\", "\\\\")
        text = text.replace("'", "''")
        return f"{'N' if self.name == 'mssql' else ''}'{text}'"

    def date_value(self, iso: str) -> str:
        return self.date_literal.format(iso)


DIALECTS = {
    "mssql": Dialect(
        "mssql",
        "[",
        "]",
        {"date": "date", "string": "nvarchar({n})", "bool": "bit"},
        "CAST('{}' AS date)",
        "1",
        "0",
        default_schema="dbo",
        batch_separator="GO",
        easter_function=True,
    ),
    "snowflake": Dialect(
        "snowflake",
        '"',
        '"',
        {"date": "DATE", "string": "VARCHAR({n})", "bool": "BOOLEAN"},
        "DATE '{}'",
        "TRUE",
        "FALSE",
        backslash_escapes=True,
    ),
    "postgres": Dialect(
        "postgres",
        '"',
        '"',
        {"date": "date", "string": "varchar({n})", "bool": "boolean"},
        "DATE '{}'",
        "TRUE",
        "FALSE",
        stage_prefix="pg_temp.",
    ),
    "mysql": Dialect(
        "mysql",
        "`",
        "`",
        {"date": "DATE", "string": "VARCHAR({n})", "bool": "BOOLEAN"},
        "DATE '{}'",
        "TRUE",
        "FALSE",
        backslash_escapes=True,
    ),
    "bigquery": Dialect(
        "bigquery",
        "`",
        "`",
        {"date": "DATE", "string": "STRING", "bool": "BOOL"},
        "DATE '{}'",
        "TRUE",
        "FALSE",
        backslash_escapes=True,
    ),
    "sqlite": Dialect(
        "sqlite",
        '"',
        '"',
        {"date": "TEXT", "string": "TEXT", "bool": "INTEGER"},
        "'{}'",
        "1",
        "0",
        batch_size=500,
        schemas=False,
        stage_prefix="temp.",
    ),
}

SCRIPTS = (
    ("01_create_tables.sql", "create_tables.sql.j2"),
    ("02_load_data.sql", "load_data.sql.j2"),
)


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def _merge_parts(d: Dialect, table: str) -> dict:
    q = d.quote
    names = [c[0] for c in COLUMNS]
    non_key = [n for n in names if n not in KEY]
    return {
        "cols": ", ".join(q(n) for n in names),
        "merge_on": " AND ".join(f"tgt.{q(k)} = src.{q(k)}" for k in KEY),
        "merge_on_delete": " AND ".join(f"{q(table)}.{q(k)} = src.{q(k)}" for k in KEY),
        "update_pairs": [f"{q(n)} = src.{q(n)}" for n in non_key],
        "insert_values": ", ".join(f"src.{q(n)}" for n in names),
        "excluded_pairs": [f"{q(n)} = EXCLUDED.{q(n)}" for n in non_key],
        "values_pairs": [f"{q(n)} = VALUES({q(n)})" for n in non_key],
    }


def _column_lines(d: Dialect, table: str) -> list[str]:
    lines = [
        f"{d.quote(name)} {d.column_type(kind, length)} {'NULL' if nullable else 'NOT NULL'}"
        for name, kind, length, nullable in COLUMNS
    ]
    key = ", ".join(d.quote(c) for c in KEY)
    if d.name == "mssql":
        lines.append(f"CONSTRAINT {d.quote('PK_' + table)} PRIMARY KEY ({key})")
    elif d.name == "bigquery":
        lines.append(f"PRIMARY KEY ({key}) NOT ENFORCED")
    else:
        lines.append(f"PRIMARY KEY ({key})")
    return lines


def _csv_like(value):
    return ";".join(value) if isinstance(value, list) else value


def render_scripts(
    dialect_name: str,
    rows: list[dict],
    start_year: int,
    end_year: int,
    schema: str | None = None,
    table: str = "bank_holidays",
    prune: bool = False,
) -> dict[str, str]:
    """Return ``{filename: sql}`` for one dialect."""
    d = DIALECTS[dialect_name]
    if not d.schemas:
        schema = None
    elif schema is None:
        schema = d.default_schema
    env = _environment()
    stage_name = f"{table}_stage"
    context = {
        "d": d,
        "schema": schema,
        "table": table,
        "table_ref": d.qualified(schema, table),
        "stage_name": stage_name,
        "stage_create": d.quote(("#" if d.name == "mssql" else "") + stage_name),
        "stage_ref": d.stage_prefix + d.quote(("#" if d.name == "mssql" else "") + stage_name),
        "columns": COLUMNS,
        "column_names": [c[0] for c in COLUMNS],
        "key_columns": ", ".join(d.quote(c) for c in KEY),
        **_merge_parts(d, table),
        "column_lines": _column_lines(d, table),
        "start_date": d.date_value(f"{start_year:04d}-01-01"),
        "end_date": d.date_value(f"{end_year:04d}-12-31"),
        "start_year": start_year,
        "end_year": end_year,
        "prune": prune,
        "batches": _batches(d, rows),
        "row_count": len(rows),
    }
    scripts = {}
    for filename, template in SCRIPTS:
        scripts[filename] = env.get_template(template).render(**context)
    if d.easter_function:
        scripts["03_easter_function.sql"] = env.get_template("easter_function.sql.j2").render(**context)
    return scripts


def _batches(d: Dialect, rows: list[dict]) -> list[list[str]]:
    rendered = []
    for row in rows:
        values = []
        for name, kind, _length, _nullable in COLUMNS:
            value = _csv_like(row[name])
            values.append(d.date_value(value) if kind == "date" else d.literal(value if value != "" else None))
        rendered.append("(" + ", ".join(values) + ")")
    return [rendered[i : i + d.batch_size] for i in range(0, len(rendered), d.batch_size)]


def write_scripts(dialects, out_dir: Path, rows, start_year, end_year, **kwargs) -> list[Path]:
    written = []
    for name in dialects:
        target = out_dir / name
        target.mkdir(parents=True, exist_ok=True)
        for filename, sql in render_scripts(name, rows, start_year, end_year, **kwargs).items():
            path = target / filename
            path.write_text(sql, encoding="utf-8")
            written.append(path)
    return written
