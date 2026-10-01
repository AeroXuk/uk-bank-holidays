"""Command line interface: ``python -m uk_bank_holidays <command>``."""

import argparse
import sys
from pathlib import Path

from . import archive, docs_gen, output, sql, validate
from .data import DEFAULT_END_YEAR, DEFAULT_SOURCE_DIR, DEFAULT_START_YEAR, REGIONS, load_json, load_source
from .generate import build_rows


def _add_range(parser):
    parser.add_argument(
        "--start-year",
        type=int,
        default=DEFAULT_START_YEAR,
        help=f"first year to generate (default {DEFAULT_START_YEAR})",
    )
    parser.add_argument(
        "--end-year", type=int, default=DEFAULT_END_YEAR, help=f"last year to generate (default {DEFAULT_END_YEAR})"
    )
    parser.add_argument(
        "--no-substitutes", action="store_true", help="do not move weekend holidays to the next weekday"
    )


def _add_common(parser):
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="directory holding rules/proclamations/overrides/sources JSON "
        f"(default: bundled {DEFAULT_SOURCE_DIR.name}/)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="uk_bank_holidays", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="write the JSON and CSV datasets")
    _add_common(gen)
    _add_range(gen)
    gen.add_argument("--output-dir", type=Path, default=Path("data"))
    gen.add_argument(
        "--region",
        choices=REGIONS,
        action="append",
        help="only write this region's files (repeatable); default writes everything",
    )
    gen.add_argument("--format", choices=("json", "csv", "both"), default="both")

    sq = sub.add_parser("sql", help="write re-runnable SQL scripts")
    _add_common(sq)
    _add_range(sq)
    sq.add_argument("--dialect", choices=sorted(sql.DIALECTS) + ["all"], required=True)
    sq.add_argument("--output-dir", type=Path, default=Path("sql"))
    sq.add_argument("--region", choices=REGIONS, help="only include holidays for this region")
    sq.add_argument("--schema", help="schema/dataset name (default depends on dialect)")
    sq.add_argument("--table", default="bank_holidays")
    sq.add_argument(
        "--prune", action="store_true", help="also delete rows in the date range that are not in the generated data"
    )

    val = sub.add_parser("validate", help="check the source data (and optionally compare with GOV.UK)")
    _add_common(val)
    val.add_argument("-v", "--verbose", action="store_true", help="list every warning")
    val.add_argument("--strict", action="store_true", help="treat warnings (unverified items) as errors")
    val.add_argument(
        "--compare-govuk",
        nargs="?",
        const=validate.GOVUK_URL,
        metavar="URL_OR_FILE",
        help="compare 2010 onwards with the GOV.UK bank-holidays.json feed",
    )

    dc = sub.add_parser("docs", help="regenerate docs/generated from the source data")
    _add_common(dc)
    dc.add_argument("--docs-dir", type=Path, default=Path("docs/generated"))

    ar = sub.add_parser("archive-links", help="fill in missing archive.org links for the cited sources")
    _add_common(ar)
    ar.add_argument("--save", action="store_true", help="ask archive.org to capture pages with no snapshot")
    ar.add_argument("--refresh", action="store_true", help="replace existing archive links")

    cl = sub.add_parser("check-links", help="check that every cited URL and archive link still resolves")
    _add_common(cl)
    return parser


def _rows(args, data):
    return build_rows(data, args.start_year, args.end_year, substitutes=not args.no_substitutes)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    source_dir = args.source_dir
    data = load_source(source_dir)

    if args.command == "generate":
        formats = ("json", "csv") if args.format == "both" else (args.format,)
        paths = output.write_all(
            data, args.output_dir, args.start_year, args.end_year, args.region, not args.no_substitutes, formats
        )
        print(f"Wrote {len(paths)} files to {args.output_dir}")
    elif args.command == "sql":
        rows = _rows(args, data)
        if args.region:
            rows = [r for r in rows if r[args.region]]
        names = sorted(sql.DIALECTS) if args.dialect == "all" else [args.dialect]
        paths = sql.write_scripts(
            names,
            args.output_dir,
            rows,
            args.start_year,
            args.end_year,
            schema=args.schema,
            table=args.table,
            prune=args.prune,
        )
        print(f"Wrote {len(paths)} scripts to {args.output_dir} ({len(rows)} rows each)")
    elif args.command == "validate":
        errors, warnings = validate.validate_source(data)
        if not errors:
            errors += validate.check_output(build_rows(data))
        if args.compare_govuk and not errors:
            errors += validate.compare_govuk(data, validate.load_govuk(args.compare_govuk))
        for line in warnings if args.verbose else []:
            print(f"warning: {line}")
        for line in errors:
            print(f"error: {line}", file=sys.stderr)
        print(
            f"{len(errors)} errors, {len(warnings)} warnings"
            + ("" if args.verbose or not warnings else " (use -v to list)")
        )
        return 1 if errors or (args.strict and warnings) else 0
    elif args.command == "docs":
        paths = docs_gen.write_docs(data, args.docs_dir)
        print(f"Wrote {len(paths)} pages to {args.docs_dir}")
    elif args.command == "archive-links":
        directory = Path(source_dir) if source_dir else DEFAULT_SOURCE_DIR
        sources = load_json(directory / "sources.json")
        for line in archive.update_sources(sources, save=args.save, refresh=args.refresh):
            print(line)
        output.write_json(directory / "sources.json", sources)
    elif args.command == "check-links":
        directory = Path(source_dir) if source_dir else DEFAULT_SOURCE_DIR
        failures = archive.check_links(load_json(directory / "sources.json"))
        for line in failures:
            print(f"error: {line}", file=sys.stderr)
        print(f"{len(failures)} broken links")
        return 1 if failures else 0
    return 0
