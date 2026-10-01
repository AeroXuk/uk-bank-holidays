"""Load the hand-curated source data (rules, proclamations, overrides, sources)."""

import json
from pathlib import Path

REGIONS = ("england_and_wales", "scotland", "northern_ireland")
DEFAULT_START_YEAR = 1871
DEFAULT_END_YEAR = 2035
PACKAGE_DIR = Path(__file__).parent
DEFAULT_SOURCE_DIR = PACKAGE_DIR / "source"
SCHEMA_DIR = PACKAGE_DIR / "schemas"
SOURCE_FILES = ("rules", "proclamations", "overrides", "sources")


def load_json(path: Path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_source(source_dir: Path | None = None) -> dict:
    source_dir = Path(source_dir) if source_dir else DEFAULT_SOURCE_DIR
    return {name: load_json(source_dir / f"{name}.json") for name in SOURCE_FILES}
