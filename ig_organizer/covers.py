"""Generate a unique watercolor leaf-sprig cover (SVG) for each saved item.

The look mirrors a soft botanical watercolor: slender muted leaves rising from
the base on a warm cream paper, lots of negative space, irregular "bleeding"
edges (feTurbulence + feDisplacementMap) and a faint paper grain.

Each item's id seeds a small PRNG, so every card gets a distinct composition.
Pure stdlib, no network, no dependencies — generated once into
_metadata/illustrations/.. err _metadata/covers/<id>.svg and served locally.
"""
from __future__ import annotations

import math
import os

from .store import metadata_dir

# Muted, desaturated earth palette taken from the reference image.
PALETTE = [
    "#a9663f", "#90543c", "#9c5a45", "#c39a8b", "#b29a82",
    "#6f5560", "#7d6b74", "#8f9275", "#9aa07f", "#7c5c49", "#9d7b6e",
]


def covers_dir(project: str) -> str:
    return os.path.join(metadata_dir(project), "covers")


def _rng(seed: int):
    """Tiny deterministic LCG in [0,1)."""
    s = seed & 0x7FFFFFFF or 1
    def r() -> float:
        nonlocal s
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        return s / 0x7FFFFFFF
    return r


def _seed_of(text: str) -> int:
    h = 2166136261
    for ch in text:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def _sample(rng, k: int) -> list[str]:
    pool = PALETTE[:]
    out = []
    for _ in range(min(k, len(pool))):
        out.append(pool.pop(int(rng() * len(pool))))
    return out


def _leaf(x: float, y: float, ang: float, L: float, W: float) -> str:
    dx, dy = math.cos(ang), math.sin(ang)
    px, py = -dy, dx
    tx, ty = x + dx * L, y + dy * L
    mx, my = x + dx * L * 0.55, y + dy * L * 0.55
    c1x, c1y = mx + px * W, my + py * W
    c2x, c2y = mx - px * W, my - py * W
    return (f"M{x:.1f},{y:.1f} Q{c1x:.1f},{c1y:.1f} {tx:.1f},{ty:.1f} "
            f"Q{c2x:.1f},{c2y:.1f} {x:.1f},{y:.1f} Z")


def _sprig(rng, bx: float, by: float, color: str, scale: float, op: float) -> str:
    height = (240 + rng() * 150) * scale
    lean = (rng() - 0.5) * 0.38
    dirx, diry = math.sin(lean), -math.cos(lean)
    ax = math.atan2(diry, dirx)
    tipx, tipy = bx + dirx * height, by + diry * height
    cx = bx + dirx * height * 0.5 + (rng() - 0.5) * 26
    cy = by + diry * height * 0.5
    n = 6 + int(rng() * 6)
    parts = [f'<g fill="{color}" opacity="{op:.2f}">',
             f'<path d="M{bx:.1f},{by:.1f} Q{cx:.1f},{cy:.1f} {tipx:.1f},{tipy:.1f}" '
             f'stroke="{color}" stroke-width="{2.4*scale:.1f}" fill="none" stroke-linecap="round"/>']
    for i in range(n):
        t = i / max(n - 1, 1)
        sx = bx + dirx * height * t
        sy = by + diry * height * t
        side = 1 if i % 2 else -1
        ang = ax + side * (0.34 + rng() * 0.34)
        L = (82 + rng() * 74) * scale * (1 - 0.4 * t)
        W = (13 + rng() * 11) * scale * (1 - 0.35 * t)
        parts.append(f'<path d="{_leaf(sx, sy, ang, L, W)}"/>')
    parts.append(f'<path d="{_leaf(tipx, tipy, ax, (55+rng()*34)*scale, (8+rng()*6)*scale)}"/>')
    parts.append("</g>")
    return "".join(parts)


def cover_svg(item_id: str) -> str:
    rng = _rng(_seed_of(item_id))
    W, H = 600, 400
    tseed = _seed_of(item_id) % 97
    pal = _sample(rng, 4)
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice">',
         "<defs>",
         '<linearGradient id="bg" x1="0" y1="0" x2="0.3" y2="1">'
         '<stop offset="0" stop-color="#f5eddf"/><stop offset="1" stop-color="#ece0cc"/></linearGradient>',
         f'<filter id="wc" x="-20%" y="-20%" width="140%" height="140%">'
         f'<feTurbulence type="fractalNoise" baseFrequency="0.011 0.016" numOctaves="2" seed="{tseed}" result="n"/>'
         f'<feDisplacementMap in="SourceGraphic" in2="n" scale="14" xChannelSelector="R" yChannelSelector="G"/>'
         f'<feGaussianBlur stdDeviation="0.7"/></filter>',
         '<filter id="soft"><feGaussianBlur stdDeviation="6"/></filter>',
         '<filter id="paper"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" result="t"/>'
         '<feColorMatrix in="t" type="saturate" values="0"/></filter>',
         "</defs>",
         f'<rect width="{W}" height="{H}" fill="url(#bg)"/>']
    # faint background silhouettes for depth (rise from the bottom edge)
    p.append('<g filter="url(#soft)">')
    for _ in range(2 + int(rng() * 2)):
        p.append(_sprig(rng, rng() * W, H + 12, pal[int(rng() * len(pal))], 1.35, 0.20 + rng() * 0.12))
    p.append("</g>")
    # foreground sprigs with watercolor edges
    p.append('<g filter="url(#wc)">')
    n = 4 + int(rng() * 3)
    for k in range(n):
        x = (k + 0.5) / n * W + (rng() - 0.5) * 80
        p.append(_sprig(rng, x, H + 10, pal[int(rng() * len(pal))], 0.95 + rng() * 0.55, 0.6 + rng() * 0.3))
    p.append("</g>")
    p.append(f'<rect width="{W}" height="{H}" filter="url(#paper)" opacity="0.045"/>')
    p.append("</svg>")
    return "".join(p)


def generate_covers(project: str, items: list[dict], *, log=print) -> dict:
    dest = covers_dir(project)
    os.makedirs(dest, exist_ok=True)
    made = skipped = 0
    for it in items:
        iid = it.get("id")
        if not iid:
            continue
        path = os.path.join(dest, iid + ".svg")
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            skipped += 1
            continue
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(cover_svg(iid))
        made += 1
    log(f"Covers: generated {made}, kept {skipped} existing -> {os.path.relpath(dest, project)}")
    return {"made": made, "skipped": skipped}
