"""Parse a local Instagram data export into normalized saved-item records.

Supports the two shapes Instagram ships:
  * HTML export  -> your_instagram_activity/saved/saved_posts.html (+ collections)
  * JSON export  -> saved_saved_media.json / saved_collections.json

Only local files are read. No network access happens anywhere in this module.
"""
from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime, timezone

# A saved item's canonical id is its Instagram shortcode (the bit after
# /reel/ or /p/ or /tv/ in the url). We use it to merge data across files.
_URL_RE = re.compile(r"https?://(?:www\.)?instagram\.com/(reel|p|tv)/([^/?\"]+)")

# Primary media URL inside the HTML export. Distinct from "Owner" urls, which
# use a two-cell layout without an anchor tag.
_PRIMARY_URL_RE = re.compile(
    r'>URL<div><a target="_blank" href="(https://www\.instagram\.com/(?:reel|p|tv)/[^"]+)"'
)
_CAPTION_RE = re.compile(r'>Caption</td><td class="_2piu _a6_r">(.*?)</td>', re.S)
_USERNAME_RE = re.compile(r'>Username</td><td class="_2piu _a6_r">(.*?)</td>', re.S)
_TIMESTAMP_RE = re.compile(r'<div class="_3-94 _a6-o">([^<]+)</div>')
# Collection header: a "Name" cell immediately followed by a "Type" cell.
_COLLECTION_HDR_RE = re.compile(
    r'>Name</td><td class="_2piu _a6_r">([^<]*)</td></tr><tr><td class="_a6_q">Type</td>'
)
_HASHTAG_RE = re.compile(r"#([A-Za-z0-9_]+)")
_TAG_RE = re.compile(r"<[^>]+>")


def shortcode_of(url: str) -> str | None:
    m = _URL_RE.search(url or "")
    return m.group(2) if m else None


def type_of(url: str) -> str:
    m = _URL_RE.search(url or "")
    if not m:
        return "unknown"
    kind = m.group(1)
    if kind in ("reel", "tv"):
        return "reel"
    if kind == "p":
        return "post"
    return "unknown"


def _clean(text: str) -> str:
    """Strip tags, unescape entities, collapse whitespace."""
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_ts(raw: str) -> str:
    """Convert 'Jun 14, 2026 12:12 pm' -> ISO 8601, or return raw on failure."""
    raw = (raw or "").strip()
    for fmt in ("%b %d, %Y %I:%M %p", "%b %d, %Y %I:%M%p"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return raw


# ---------------------------------------------------------------------------
# Export discovery
# ---------------------------------------------------------------------------
def find_export(root: str) -> str | None:
    """Return the export base dir (containing your_instagram_activity) or None.

    Walks `root` looking for a saved/ folder with saved_posts.html or a saved
    media JSON file. Skips the organized library and output dirs.
    """
    candidates = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Don't descend into our own outputs.
        dirnames[:] = [
            d for d in dirnames
            if d not in ("Instagram Saved Library", "output", "node_modules")
            and not d.startswith(".")
        ]
        low = {f.lower() for f in filenames}
        if "saved_posts.html" in low or "saved_saved_media.json" in low:
            # The export base is the parent of your_instagram_activity.
            base = dirpath
            if os.path.basename(dirpath).lower() == "saved":
                base = os.path.dirname(os.path.dirname(dirpath))
            candidates.append(base)
    # Prefer the shallowest match (the real export root).
    candidates.sort(key=lambda p: len(p))
    return candidates[0] if candidates else None


def _saved_dir(export_base: str) -> str | None:
    for sub in ("your_instagram_activity/saved", "saved"):
        p = os.path.join(export_base, sub)
        if os.path.isdir(p):
            return p
    # Fall back to a recursive search.
    for dirpath, _dn, _fn in os.walk(export_base):
        if os.path.basename(dirpath).lower() == "saved":
            return dirpath
    return None


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------
def _segment_items(doc: str):
    """Yield (url, segment_html) for each saved item in an HTML doc.

    Items are segmented by primary-URL boundaries: everything from one media
    URL up to the next belongs to that item.
    """
    matches = list(_PRIMARY_URL_RE.finditer(doc))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(doc)
        yield m.group(1), doc[m.start():end]


def _item_from_segment(url: str, seg: str, source_file: str) -> dict:
    cap_m = _CAPTION_RE.search(seg)
    caption = _clean(cap_m.group(1)) if cap_m else ""
    user_m = _USERNAME_RE.search(seg)
    username = _clean(user_m.group(1)) if user_m else ""
    ts_m = _TIMESTAMP_RE.search(seg)
    saved_at = _parse_ts(ts_m.group(1)) if ts_m else ""
    hashtags = sorted({h.lower() for h in _HASHTAG_RE.findall(caption)})
    return {
        "id": shortcode_of(url) or url,
        "type": type_of(url),
        "url": url,
        "username": username,
        "caption": caption,
        "hashtags": hashtags,
        "saved_at": saved_at,
        "collection_name": "",
        "source_file": source_file,
        "local_file_path": "",
        "suggested_category": "",
        "final_category": "",
        "notes": "",
    }


def _parse_html_posts(path: str, items: dict, source_label: str) -> None:
    doc = open(path, encoding="utf-8", errors="replace").read()
    for url, seg in _segment_items(doc):
        sc = shortcode_of(url) or url
        rec = _item_from_segment(url, seg, source_label)
        if sc in items:
            _merge(items[sc], rec)
        else:
            items[sc] = rec


def _parse_html_collections(path: str, items: dict, source_label: str) -> None:
    """Attach collection_name to items, splitting the doc by collection header."""
    doc = open(path, encoding="utf-8", errors="replace").read()
    headers = list(_COLLECTION_HDR_RE.finditer(doc))
    for i, h in enumerate(headers):
        name = html.unescape(h.group(1)).strip()
        start = h.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(doc)
        block = doc[start:end]
        for url, seg in _segment_items(block):
            sc = shortcode_of(url) or url
            if sc not in items:
                items[sc] = _item_from_segment(url, seg, source_label)
            _add_collection(items[sc], name)


def _add_collection(item: dict, name: str) -> None:
    if not name:
        return
    existing = [c.strip() for c in item["collection_name"].split(";") if c.strip()]
    if name not in existing:
        existing.append(name)
    item["collection_name"] = "; ".join(existing)


def _merge(dst: dict, src: dict) -> None:
    """Fill empty fields in dst from src; keep richer values."""
    for k in ("username", "caption", "saved_at"):
        if not dst.get(k) and src.get(k):
            dst[k] = src[k]
    if src.get("hashtags"):
        dst["hashtags"] = sorted(set(dst.get("hashtags", [])) | set(src["hashtags"]))


# ---------------------------------------------------------------------------
# JSON parsing (fallback for JSON-format exports)
# ---------------------------------------------------------------------------
def _walk_json_saved(obj, items: dict, source_label: str, collection_name: str = "") -> None:
    """Recursively pull saved entries out of an Instagram JSON export."""
    if isinstance(obj, dict):
        # A typical saved entry: {"title": user, "string_map_data": {"Saved on": {"href":url,"timestamp":...}}}
        smd = obj.get("string_map_data") or obj.get("string_list_data")
        url = None
        ts = None
        if isinstance(smd, dict):
            for key in ("Saved on", "Saved On"):
                if key in smd and isinstance(smd[key], dict):
                    url = smd[key].get("href")
                    ts = smd[key].get("timestamp")
        if isinstance(smd, list):
            for entry in smd:
                if isinstance(entry, dict) and entry.get("href"):
                    url = entry.get("href")
                    ts = entry.get("timestamp")
        if url and _URL_RE.search(url):
            sc = shortcode_of(url) or url
            rec = items.get(sc) or {
                "id": sc, "type": type_of(url), "url": url,
                "username": _clean(obj.get("title", "")), "caption": "",
                "hashtags": [], "saved_at": "", "collection_name": "",
                "source_file": source_label, "local_file_path": "",
                "suggested_category": "", "final_category": "", "notes": "",
            }
            if ts and not rec["saved_at"]:
                try:
                    rec["saved_at"] = datetime.fromtimestamp(int(ts), timezone.utc).isoformat()
                except (ValueError, TypeError, OSError):
                    pass
            if collection_name:
                _add_collection(rec, collection_name)
            items[sc] = rec
        for v in obj.values():
            _walk_json_saved(v, items, source_label, collection_name)
    elif isinstance(obj, list):
        for v in obj:
            _walk_json_saved(v, items, source_label, collection_name)


def _parse_json_file(path: str, items: dict) -> None:
    try:
        data = json.load(open(path, encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError):
        return
    _walk_json_saved(data, items, os.path.basename(path))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def parse_export(export_base: str, log=print) -> list[dict]:
    """Parse all saved-related files under an export base into item records."""
    items: dict[str, dict] = {}
    saved = _saved_dir(export_base)
    parsed_any = False

    if saved:
        posts = os.path.join(saved, "saved_posts.html")
        colls = os.path.join(saved, "saved_collections.html")
        if os.path.isfile(posts):
            log(f"Parsing {posts}")
            _parse_html_posts(posts, items, "saved/saved_posts.html")
            parsed_any = True
        if os.path.isfile(colls):
            log(f"Parsing {colls}")
            _parse_html_collections(colls, items, "saved/saved_collections.html")
            parsed_any = True

    # JSON exports (and any stray saved_*.json) as a fallback / supplement.
    for dirpath, dirnames, filenames in os.walk(export_base):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")
                       and d not in ("Instagram Saved Library", "output")]
        for f in filenames:
            fl = f.lower()
            if fl.endswith(".json") and ("saved" in fl or "collection" in fl):
                log(f"Parsing {os.path.join(dirpath, f)}")
                _parse_json_file(os.path.join(dirpath, f), items)
                parsed_any = True

    if not parsed_any:
        log("WARNING: no saved_posts.html or saved JSON found in export.")

    return list(items.values())
