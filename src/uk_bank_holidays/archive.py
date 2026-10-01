"""Fill in Wayback Machine (archive.org) links for the cited sources."""

import json
import urllib.parse
import urllib.request
from datetime import date

AVAILABLE_API = "https://archive.org/wayback/available?url="
SAVE_URL = "https://web.archive.org/save/"


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "uk-bank-holidays/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        return response.read()


def latest_snapshot(url: str) -> str | None:
    """The closest existing Wayback snapshot for ``url`` (as an https URL), or ``None``."""
    payload = json.loads(_get(AVAILABLE_API + urllib.parse.quote(url, safe="")))
    closest = payload.get("archived_snapshots", {}).get("closest")
    if closest and closest.get("available"):
        return closest["url"].replace("http://", "https://", 1)
    return None


def request_snapshot(url: str) -> str | None:
    """Ask the Wayback Machine to capture ``url`` now, then return the snapshot link."""
    _get(SAVE_URL + url)
    return latest_snapshot(url)


def update_sources(
    sources: dict, save: bool = False, refresh: bool = False, fetch=latest_snapshot, capture=request_snapshot
) -> list[str]:
    """Fill ``archive_url`` / ``accessed`` in place; returns a log of what happened."""
    log = []
    for source_id, source in sources.items():
        if not source["url"]:
            continue
        if source["archive_url"] and not refresh:
            continue
        snapshot = fetch(source["url"]) or (capture(source["url"]) if save else None)
        if snapshot:
            source["archive_url"] = snapshot
            source["accessed"] = date.today().isoformat()
            log.append(f"{source_id}: {snapshot}")
        else:
            log.append(f"{source_id}: no snapshot found (re-run with --save to request one)")
    return log


def check_links(sources: dict, open_url=_get) -> list[str]:
    """Fetch every ``url`` and ``archive_url``; returns a list of the ones that fail."""
    failures = []
    for source_id, source in sources.items():
        for field in ("url", "archive_url"):
            if not source[field]:
                continue
            try:
                open_url(source[field])
            except Exception as exc:  # noqa: BLE001 - report any failure, whatever the cause
                failures.append(f"{source_id}.{field}: {source[field]} ({exc})")
    return failures
