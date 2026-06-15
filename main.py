#!/usr/bin/env python3
"""LTSOP — Lost The Saved Ones Project.

Local Instagram Saved Reels Organizer. Reads a local Instagram data export and
organizes manually-downloaded reel media into category folders.

Commands:
    python main.py scan         Parse the export -> saved_items.json/csv + folders
    python main.py organize     Match Inbox media -> category folders (copy by default)
    python main.py build-index  Rebuild the HTML dashboard from the database

This tool never logs into, scrapes, or contacts Instagram. It only reads local
files that already exist in the project folder.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

from ig_organizer import parser as ig_parser
from ig_organizer import store
from ig_organizer.categorize import categorize_all
from ig_organizer.covers import generate_covers
from ig_organizer.indexer import build_index
from ig_organizer.organize import organize_media

PROJECT = os.path.dirname(os.path.abspath(__file__))


def _resolve_export(arg: str | None, log) -> str | None:
    if arg:
        if os.path.isdir(arg):
            return arg
        log(f"ERROR: --export path not found: {arg}")
        return None
    log("Searching for Instagram export…")
    return ig_parser.find_export(PROJECT)


def cmd_scan(args) -> int:
    log = store.Logger(PROJECT, "scan")
    try:
        store.ensure_library(PROJECT)
        export = _resolve_export(args.export, log)
        if not export:
            # Build a friendly empty dashboard so the user has something to open.
            build_index(PROJECT, [])
            log("")
            log("No Instagram export found yet.")
            log("  1. Request your data export from Instagram (Settings → Your")
            log("     information and permissions → Download your information).")
            log("  2. Unzip it and drop the 'instagram-...' folder into this directory.")
            log("  3. Run this again:  python3 main.py scan")
            log("")
            log("Opened the dashboard? It now shows these same steps. Path:")
            log(f"  {os.path.relpath(os.path.join(store.metadata_dir(PROJECT), 'index.html'), PROJECT)}")
            return 1
        log(f"Using export: {export}")

        items = ig_parser.parse_export(export, log=log)
        if not items:
            build_index(PROJECT, [])
            log("Found the export, but no saved items in it. Built an empty dashboard.")
            log("Make sure 'Saved' activity was included when you requested the export.")
            return 1

        # Preserve any human-set final_category / notes from a previous scan.
        prev = {i["id"]: i for i in store.load_database(PROJECT)}
        for it in items:
            old = prev.get(it["id"])
            if old:
                if old.get("final_category") and old["final_category"] != old.get("suggested_category"):
                    it["final_category"] = old["final_category"]
                if old.get("local_file_path"):
                    it["local_file_path"] = old["local_file_path"]
                if old.get("notes"):
                    it["notes"] = old["notes"]

        categorize_all(items, seed_final=True)
        paths = store.save_database(PROJECT, items)
        build_index(PROJECT, items)

        cats = Counter(i["suggested_category"] for i in items)
        log("")
        log(f"Parsed {len(items)} saved items.")
        log("Suggested category breakdown:")
        for cat, n in cats.most_common():
            log(f"  {cat:20s} {n}")
        log("")
        log("Wrote:")
        for p in paths:
            log(f"  {os.path.relpath(p, PROJECT)}")
        log(f"  {os.path.relpath(os.path.join(store.metadata_dir(PROJECT), 'index.html'), PROJECT)}")
        log(f"Log: {os.path.relpath(log.path, PROJECT)}")
        return 0
    finally:
        log.close()


def cmd_organize(args) -> int:
    log = store.Logger(PROJECT, "organize")
    try:
        store.ensure_library(PROJECT)
        items = store.load_database(PROJECT)
        if not items:
            log("ERROR: No database found. Run `python main.py scan` first.")
            return 1
        mode = "MOVE" if args.move else "COPY"
        log(f"Organize mode: {mode} (originals are preserved unless --move).")
        organize_media(PROJECT, items, move=args.move, log=log)

        store.save_database(PROJECT, items)
        build_index(PROJECT, items)
        log("Database and dashboard updated.")
        log(f"Log: {os.path.relpath(log.path, PROJECT)}")
        return 0
    finally:
        log.close()


def cmd_covers(args) -> int:
    log = store.Logger(PROJECT, "covers")
    try:
        store.ensure_library(PROJECT)
        items = store.load_database(PROJECT)
        if not items:
            log("ERROR: No database found. Run `python main.py scan` first.")
            return 1
        generate_covers(PROJECT, items, log=log)
        build_index(PROJECT, items)
        log("Generated unique watercolor covers and rebuilt the dashboard.")
        return 0
    finally:
        log.close()


def cmd_build_index(args) -> int:
    log = store.Logger(PROJECT, "build-index")
    try:
        store.ensure_library(PROJECT)
        items = store.load_database(PROJECT)
        if not items:
            log("ERROR: No database found. Run `python main.py scan` first.")
            return 1
        out = build_index(PROJECT, items)
        log(f"Built dashboard: {os.path.relpath(out, PROJECT)} ({len(items)} items)")
        return 0
    finally:
        log.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="main.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Parse export into database + folders")
    p_scan.add_argument("--export", help="Path to the export folder (auto-detected if omitted)")
    p_scan.set_defaults(func=cmd_scan)

    p_org = sub.add_parser("organize", help="File Inbox media into category folders")
    p_org.add_argument("--move", action="store_true", help="Move files instead of copying")
    p_org.set_defaults(func=cmd_organize)

    p_cov = sub.add_parser("covers", help="Generate a unique watercolor cover per saved item")
    p_cov.set_defaults(func=cmd_covers)

    p_idx = sub.add_parser("build-index", help="Rebuild the HTML dashboard")
    p_idx.set_defaults(func=cmd_build_index)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
