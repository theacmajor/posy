"""Persistence: paths, JSON/CSV read+write, and file logging.

The database is written to two places so both the spec's `/output` location and
the library's `_metadata` folder stay in sync:
  * <project>/output/saved_items.{json,csv}
  * <project>/Instagram Saved Library/_metadata/saved_items.{json,csv}
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone

from .config import (
    ALL_FOLDERS,
    LIBRARY_DIRNAME,
    LOGS_DIRNAME,
    METADATA_DIRNAME,
)

# Column order for both CSV and JSON records.
FIELDS = [
    "id", "type", "url", "username", "caption", "hashtags", "saved_at",
    "collection_name", "source_file", "local_file_path",
    "suggested_category", "final_category", "notes",
]


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
def library_dir(project: str) -> str:
    return os.path.join(project, LIBRARY_DIRNAME)


def metadata_dir(project: str) -> str:
    return os.path.join(library_dir(project), METADATA_DIRNAME)


def logs_dir(project: str) -> str:
    return os.path.join(metadata_dir(project), LOGS_DIRNAME)


def output_dir(project: str) -> str:
    return os.path.join(project, "output")


def inbox_dir(project: str) -> str:
    return os.path.join(library_dir(project), ALL_FOLDERS[0])


def ensure_library(project: str) -> None:
    """Create the full library folder tree (idempotent)."""
    for folder in ALL_FOLDERS:
        os.makedirs(os.path.join(library_dir(project), folder), exist_ok=True)
    os.makedirs(metadata_dir(project), exist_ok=True)
    os.makedirs(logs_dir(project), exist_ok=True)
    os.makedirs(output_dir(project), exist_ok=True)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------
def _to_row(item: dict) -> dict:
    row = {}
    for f in FIELDS:
        v = item.get(f, "")
        if f == "hashtags" and isinstance(v, list):
            v = " ".join(v)
        row[f] = "" if v is None else v
    return row


def _normalize(item: dict) -> dict:
    """Ensure every record has all fields; coerce hashtags to a list."""
    out = {f: item.get(f, "") for f in FIELDS}
    h = out.get("hashtags", [])
    if isinstance(h, str):
        out["hashtags"] = [t for t in h.split() if t]
    elif not isinstance(h, list):
        out["hashtags"] = []
    return out


# ---------------------------------------------------------------------------
# Write / read
# ---------------------------------------------------------------------------
def _write_pair(items: list[dict], directory: str) -> None:
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "saved_items.json"), "w", encoding="utf-8") as fh:
        json.dump([_normalize(i) for i in items], fh, ensure_ascii=False, indent=2)
    with open(os.path.join(directory, "saved_items.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for it in items:
            w.writerow(_to_row(it))


def save_database(project: str, items: list[dict]) -> list[str]:
    """Write the database to both output/ and _metadata/. Returns paths written."""
    targets = [output_dir(project), metadata_dir(project)]
    for d in targets:
        _write_pair(items, d)
    return [os.path.join(d, "saved_items.json") for d in targets]


def load_database(project: str) -> list[dict]:
    """Load the canonical database from _metadata (falls back to output)."""
    for d in (metadata_dir(project), output_dir(project)):
        p = os.path.join(d, "saved_items.json")
        if os.path.isfile(p):
            try:
                return [_normalize(i) for i in json.load(open(p, encoding="utf-8"))]
            except (json.JSONDecodeError, OSError):
                continue
    return []


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
class Logger:
    """Tee log messages to stdout and a timestamped file under _metadata/logs."""

    def __init__(self, project: str, command: str):
        os.makedirs(logs_dir(project), exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        self.path = os.path.join(logs_dir(project), f"{command}-{stamp}.log")
        self._fh = open(self.path, "w", encoding="utf-8")

    def __call__(self, msg: str) -> None:
        line = str(msg)
        print(line)
        self._fh.write(line + "\n")
        self._fh.flush()

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass
