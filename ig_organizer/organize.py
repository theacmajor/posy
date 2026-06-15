"""Match Inbox media files to saved items and file them into category folders.

Safety contract:
  * Originals are never deleted. Default mode is COPY.
  * Move only happens when move=True is explicitly passed (`--move`).
  * Unmatched media stays in the Inbox and is reported, never guessed into a
    random category.
"""
from __future__ import annotations

import os
import shutil

from .config import CATEGORY_FOLDERS, MEDIA_EXTENSIONS
from .store import inbox_dir, library_dir

# A manual override file the user can fill in: filename,shortcode
MANUAL_MAP = "manual_mapping.csv"


def _media_files(folder: str) -> list[str]:
    out = []
    if not os.path.isdir(folder):
        return out
    for name in os.listdir(folder):
        full = os.path.join(folder, name)
        if os.path.isfile(full) and os.path.splitext(name)[1].lower() in MEDIA_EXTENSIONS:
            out.append(full)
    return out


def _load_manual_map(project: str, log) -> dict:
    """Read _metadata/manual_mapping.csv (filename -> shortcode) if present."""
    from .store import metadata_dir
    path = os.path.join(metadata_dir(project), MANUAL_MAP)
    mapping = {}
    if not os.path.isfile(path):
        return mapping
    import csv
    try:
        with open(path, encoding="utf-8") as fh:
            for row in csv.reader(fh):
                if len(row) >= 2 and row[0].strip() and not row[0].lower().startswith("filename"):
                    mapping[row[0].strip()] = row[1].strip()
        log(f"Loaded {len(mapping)} manual mapping(s) from {MANUAL_MAP}")
    except OSError:
        pass
    return mapping


def _index_items(items: list[dict]):
    """Build lookup indexes for matching: by shortcode and by username.

    `shorts` is a length-descending list of (lower_shortcode, item) so we can
    substring-match the most specific code first — shortcodes themselves contain
    '_' and '-', so plain token-splitting would break them apart.
    """
    by_short = {}
    by_user = {}
    for it in items:
        if it.get("id"):
            by_short[it["id"].lower()] = it
        u = (it.get("username") or "").lower()
        if u:
            by_user.setdefault(u, []).append(it)
    shorts = sorted(by_short.items(), key=lambda kv: -len(kv[0]))
    return by_short, by_user, shorts


def _match(filename: str, by_short, by_user, shorts, manual_map) -> tuple[dict | None, str]:
    """Return (item, reason) for the best match, or (None, reason)."""
    base = os.path.basename(filename)
    stem = os.path.splitext(base)[0]
    low = stem.lower()

    # 1. Manual mapping wins.
    if base in manual_map:
        it = by_short.get(manual_map[base].lower())
        if it:
            return it, "manual_mapping"

    # 2. A saved item's shortcode appears in the filename (e.g.
    #    "reel_DZgszzuocNc.mp4"). Shortcodes contain '_'/'-', so we substring
    #    match longest-first rather than splitting the filename into tokens.
    for sc, it in shorts:
        if len(sc) >= 6 and sc in low:
            return it, f"shortcode:{sc}"

    # 3. Username appears in the filename.
    for user, lst in by_user.items():
        if len(user) >= 3 and user in low:
            # If exactly one saved item from that user, confident; else ambiguous.
            if len(lst) == 1:
                return lst[0], f"username:{user}"
            return lst[0], f"username-ambiguous:{user}"

    return None, "unmatched"


def _dest_folder(project: str, item: dict) -> str:
    category = item.get("final_category") or item.get("suggested_category") or "Uncategorized"
    folder = CATEGORY_FOLDERS.get(category, CATEGORY_FOLDERS["Uncategorized"])
    return os.path.join(library_dir(project), folder)


def _unique_path(dest_dir: str, filename: str) -> str:
    target = os.path.join(dest_dir, filename)
    if not os.path.exists(target):
        return target
    stem, ext = os.path.splitext(filename)
    i = 1
    while os.path.exists(os.path.join(dest_dir, f"{stem} ({i}){ext}")):
        i += 1
    return os.path.join(dest_dir, f"{stem} ({i}){ext}")


def organize_media(project: str, items: list[dict], *, move: bool = False, log=print) -> dict:
    """Scan the Inbox, match files to items, copy/move into category folders.

    Returns a summary dict and updates matched items' local_file_path in place.
    """
    inbox = inbox_dir(project)
    files = _media_files(inbox)
    log(f"Found {len(files)} media file(s) in Inbox: {inbox}")

    by_short, by_user, shorts = _index_items(items)
    manual_map = _load_manual_map(project, log)

    summary = {"total": len(files), "matched": 0, "unmatched": 0, "actions": []}
    verb = "Moved" if move else "Copied"

    for f in files:
        item, reason = _match(f, by_short, by_user, shorts, manual_map)
        base = os.path.basename(f)
        if item is None:
            summary["unmatched"] += 1
            log(f"  [skip] {base} -> no match ({reason}); left in Inbox")
            summary["actions"].append({"file": base, "matched": False, "reason": reason})
            continue

        dest_dir = _dest_folder(project, item)
        os.makedirs(dest_dir, exist_ok=True)
        dest = _unique_path(dest_dir, base)
        try:
            if move:
                shutil.move(f, dest)
            else:
                shutil.copy2(f, dest)
        except OSError as e:
            log(f"  [error] {base}: {e}")
            summary["actions"].append({"file": base, "matched": True, "error": str(e)})
            continue

        rel = os.path.relpath(dest, project)
        item["local_file_path"] = rel
        if item.get("notes"):
            item["notes"] += f" | media matched via {reason}"
        else:
            item["notes"] = f"media matched via {reason}"
        summary["matched"] += 1
        folder_name = os.path.basename(dest_dir)
        log(f"  [ok] {verb} {base} -> {folder_name}/ (match: {reason}, item {item['id']})")
        summary["actions"].append({
            "file": base, "matched": True, "reason": reason,
            "item_id": item["id"], "dest": rel,
        })

    log(f"Done. matched={summary['matched']} unmatched={summary['unmatched']}")
    return summary
