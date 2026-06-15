"""Assign a suggested category to a saved item.

Strategy (highest-priority signal first):
  1. Exact match of a user-curated collection name -> that category.
  2. Weighted keyword scoring across collection/hashtags/caption/username/url/file.
  3. Below the confidence floor -> "Uncategorized".

`final_category` is never overwritten here once a human has set it; the caller
decides whether to seed it from the suggestion.
"""
from __future__ import annotations

import re

from .config import (
    CATEGORY_KEYWORDS,
    COLLECTION_CATEGORY,
    MIN_CONFIDENCE,
    WEIGHTS,
)

# Precompile one word-boundary pattern per (category, keyword) so short tokens
# like "ui"/"ux"/"abs"/"rice" don't match inside "building"/"luxury"/"tabs"/"price".
# \b around the keyword; spaces in phrases tolerate one-or-more whitespace.
def _compile(keyword: str) -> re.Pattern:
    parts = [re.escape(p) for p in keyword.split()]
    body = r"\s+".join(parts)
    return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])")


_COMPILED = {
    cat: [(_compile(kw), kw) for kw in kws]
    for cat, kws in CATEGORY_KEYWORDS.items()
}


def _norm(s: str) -> str:
    return (s or "").lower()


def _folder_category(item: dict) -> str | None:
    """Authoritative category from the item's saved folder(s), or None.

    An item can live in several folders (e.g. "Today; Workout"). We prefer a
    real category over an explicit "Uncategorized" mapping, so a useful folder
    always beats a misfit one. Returns None only when no folder is mapped at all
    (i.e. the item is only in "Today" or in no folder), leaving keyword scoring
    to decide.
    """
    mapped = []
    for coll in item.get("collection_name", "").split(";"):
        key = coll.strip().lower()
        if key in COLLECTION_CATEGORY:
            mapped.append(COLLECTION_CATEGORY[key])
    real = [c for c in mapped if c != "Uncategorized"]
    if real:
        return real[0]
    if mapped:  # only misfit folders -> deliberately Uncategorized
        return "Uncategorized"
    return None


def score_item(item: dict) -> tuple[str, dict]:
    """Return (suggested_category, score_breakdown_by_category)."""
    # 1. Saved folder is authoritative — your own labels win over guessing.
    folder_cat = _folder_category(item)
    if folder_cat is not None:
        return folder_cat, {folder_cat: WEIGHTS["collection_name"]}

    # 2. Weighted keyword scoring (only for items with no usable saved folder).
    fields = {
        "collection_name": _norm(item.get("collection_name", "")),
        "hashtags": _norm(" ".join(item.get("hashtags", []))),
        "caption": _norm(item.get("caption", "")),
        "username": _norm(item.get("username", "")),
        "url": _norm(item.get("url", "")),
        "local_file_path": _norm(item.get("local_file_path", "")),
    }

    scores: dict[str, int] = {}
    for category, patterns in _COMPILED.items():
        total = 0
        for field, text in fields.items():
            if not text:
                continue
            weight = WEIGHTS.get(field, 1)
            for pat, _kw in patterns:
                if pat.search(text):
                    total += weight
        if total:
            scores[category] = total

    if not scores:
        return "Uncategorized", {}

    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    best_cat, best_score = ranked[0]
    if best_score < MIN_CONFIDENCE:
        return "Uncategorized", scores
    # Ambiguous: if the top two categories tie, don't guess — leave it for the
    # human (prevents e.g. an address "…Layout" outranking a food signal).
    if len(ranked) > 1 and ranked[1][1] == best_score:
        return "Uncategorized", scores
    return best_cat, scores


def categorize(item: dict, *, seed_final: bool = True) -> dict:
    """Set suggested_category (and final_category if empty) on an item in place."""
    suggested, _scores = score_item(item)
    item["suggested_category"] = suggested
    if seed_final and not item.get("final_category"):
        item["final_category"] = suggested
    return item


def categorize_all(items: list[dict], *, seed_final: bool = True) -> list[dict]:
    for it in items:
        categorize(it, seed_final=seed_final)
    return items
