"""Build a self-contained local HTML dashboard from the saved-items database.

The data is embedded directly into the page as JSON, so the dashboard works by
double-clicking the file — no server, no network, no external assets.

Layout follows the Gamma / Craft "content library" pattern: a left sidebar that
lists your categories and saved folders, and a spacious card grid (with a
grid/list toggle) in the main area. Light by default, with a dark toggle.

The dashboard is interactive: create your own categories and move any saved reel
between categories. Edits persist in the browser (localStorage) and can be
exported back to saved_items.json.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone

from .config import CATEGORY_FOLDERS
from .covers import cover_svg
from .store import metadata_dir


def _stats(items: list[dict]) -> dict:
    by_cat = Counter(i.get("final_category") or "Uncategorized" for i in items)
    by_type = Counter(i.get("type") or "unknown" for i in items)
    with_media = sum(1 for i in items if i.get("local_file_path"))
    return {
        "total": len(items),
        "with_media": with_media,
        "by_category": dict(by_cat),
        "by_type": dict(by_type),
    }


def build_index(project: str, items: list[dict]) -> str:
    """Write _metadata/index.html and return its path."""
    stats = _stats(items)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    categories = list(CATEGORY_FOLDERS.keys())

    # Escape "</" so a literal "</script>" inside any caption can't terminate
    # the embedded <script> block and break the page.
    def _safe(obj) -> str:
        return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

    html = _TEMPLATE.replace("__GENERATED__", generated)
    html = html.replace("__TOTAL__", str(stats["total"]))
    html = html.replace("__WITHMEDIA__", str(stats["with_media"]))
    covers = os.path.join(metadata_dir(project), "covers")
    has_covers = os.path.isdir(covers) and any(f.endswith(".svg") for f in os.listdir(covers))

    html = html.replace("/*__DATA__*/", _safe(items))
    html = html.replace("/*__STATS__*/", _safe(stats))
    html = html.replace("/*__CATS__*/", _safe(categories))
    html = html.replace("/*__COVERS__*/", "true" if has_covers else "false")
    # floral artwork for each onboarding step (inline, self-contained)
    onboard = [cover_svg(f"posy-welcome-{n}") for n in range(1, 6)]
    html = html.replace("/*__ONBOARD__*/", _safe(onboard))

    out = os.path.join(metadata_dir(project), "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    with open(os.path.join(os.path.dirname(out), "favicon.svg"), "w", encoding="utf-8") as fh:
        fh.write(_FAVICON)
    return out


# A flower mark (cream on a dark rounded square) used as the browser tab icon.
_FAVICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<rect width="32" height="32" rx="8" fill="#1b1b1f"/>'
    '<g transform="translate(4 4)" fill="none" stroke="#f3ead9" stroke-width="1.7" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="3"/>'
    '<path d="M12 16.5A4.5 4.5 0 1 1 7.5 12 4.5 4.5 0 1 1 12 7.5a4.5 4.5 0 1 1 4.5 4.5 4.5 4.5 0 1 1-4.5 4.5"/>'
    '<path d="M12 7.5V9"/><path d="M7.5 12H9"/><path d="M16.5 12H15"/><path d="M12 16.5V15"/>'
    '<path d="m8 8 1.88 1.88"/><path d="M14.12 9.88 16 8"/><path d="m8 16 1.88-1.88"/><path d="M14.12 14.12 16 16"/>'
    "</g></svg>"
)


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Posy · Saved Library</title>
<link rel="icon" type="image/svg+xml" href="favicon.svg" />
<meta name="description" content="Posy turns your Instagram 'Saved' data export into a calm, organized, searchable, 100% local library. No login, no scraping." />
<meta name="author" content="Anand Chauhan" />
<meta property="og:type" content="website" />
<meta property="og:site_name" content="Posy" />
<meta property="og:title" content="Posy · your Instagram saves, finally organized" />
<meta property="og:description" content="Turn your Instagram 'Saved' data export into a calm, organized, searchable, 100% local library. No login, no scraping." />
<meta property="og:url" content="https://github.com/theacmajor/posy" />
<meta property="og:image" content="https://raw.githubusercontent.com/theacmajor/posy/main/assets/og-image.png" />
<meta property="og:image:width" content="2560" />
<meta property="og:image:height" content="1600" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="Posy · your Instagram saves, finally organized" />
<meta name="twitter:description" content="Turn your Instagram 'Saved' data export into a calm, organized, searchable, 100% local library." />
<meta name="twitter:image" content="https://raw.githubusercontent.com/theacmajor/posy/main/assets/og-image.png" />
<meta name="twitter:creator" content="@xyanandc" />
<style>
  /* ---- Gamma / Craft content-library tokens (light default) ---- */
  :root{
    --bg:#ffffff; --side:#fafafa; --card:#ffffff;
    --fg:#18181b; --fg2:#3f3f46; --mut:#71717a; --faint:#a1a1aa;
    --border:#ececef; --border2:#f1f1f3; --hover:#f4f4f5; --active:#eeeef0;
    --pill:#f4f4f5; --pill-fg:#52525b; --ring:#a1a1aa;
    --radius:12px;
  }
  html.dark{
    --bg:#0f1012; --side:#0b0c0e; --card:#161719;
    --fg:#f3f3f5; --fg2:#d4d4d8; --mut:#9a9ea8; --faint:#6b7079;
    --border:#222428; --border2:#1c1e22; --hover:#1a1c20; --active:#212429;
    --pill:#1e2024; --pill-fg:#b6bac2; --ring:#52555c;
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{margin:0;background:var(--bg);color:var(--fg);
    font:13.5px/1.5 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    -webkit-font-smoothing:antialiased}
  a{color:inherit;text-decoration:none}

  .app{display:flex;min-height:100vh}

  /* ---------- sidebar ---------- */
  .side{width:256px;flex:none;background:var(--side);border-right:1px solid var(--border);
    display:flex;flex-direction:column;height:100vh;position:sticky;top:0}
  .brand{display:flex;align-items:center;gap:9px;padding:18px 16px 12px;font-weight:680;font-size:15px;letter-spacing:-.01em}
  .brand .ic{width:28px;height:28px;border-radius:8px;display:grid;place-items:center;font-size:14px;
    background:var(--fg);color:var(--bg)}
  .brand-name{white-space:nowrap}
  .side-collapse{margin-left:auto;width:28px;height:28px;display:grid;place-items:center;border:0;background:none;
    cursor:pointer;color:var(--mut);border-radius:7px;transition:background .15s,color .15s,transform .15s}
  .side-collapse:hover{background:var(--hover);color:var(--fg)}
  .sideexpand{display:none;width:38px;height:38px;flex:none;place-items:center;border:1px solid var(--border);
    background:var(--card);border-radius:9px;cursor:pointer;color:var(--fg);transition:background .15s}
  .sideexpand:hover{background:var(--hover)}
  .side-scroll{flex:1;overflow-y:auto;padding:6px 10px 10px}
  .sec{margin-top:14px}
  .sec-h{display:flex;align-items:center;justify-content:space-between;padding:6px 8px;color:var(--faint);
    font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase}
  .sec-h button{background:none;border:0;color:var(--mut);cursor:pointer;font-size:15px;line-height:1;padding:0 2px;border-radius:5px}
  .sec-h button:hover{background:var(--hover);color:var(--fg)}
  .sec-h .hint{cursor:help;color:var(--faint);font-size:11px}
  .nav{display:flex;align-items:center;gap:9px;width:100%;padding:7px 9px;border-radius:8px;cursor:pointer;
    color:var(--fg2);font-size:13px;border:0;background:none;text-align:left;transition:background .1s}
  .nav:hover{background:var(--hover)}
  .nav.active{background:var(--active);color:var(--fg);font-weight:600}
  .nav .dot{width:8px;height:8px;border-radius:50%;flex:none}
  .nav .ico{width:15px;flex:none;display:grid;place-items:center;color:var(--mut)}
  .nav .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .nav .ct{color:var(--faint);font-size:12px;font-variant-numeric:tabular-nums}
  .nav.active .ct{color:var(--mut)}
  .side-foot{border-top:1px solid var(--border);padding:10px;display:flex;gap:8px;align-items:center}
  .side-credit{padding:9px 14px 12px;font-size:11px;color:var(--faint)}
  .side-credit a{color:var(--mut)}
  .side-credit a:hover{color:var(--fg);text-decoration:underline}
  .sbtn{flex:1;height:34px;display:inline-flex;align-items:center;justify-content:center;gap:6px;border:1px solid var(--border);
    background:var(--card);border-radius:9px;color:var(--fg2);cursor:pointer;font:inherit;font-size:12.5px;font-weight:550}
  .sbtn:hover{background:var(--hover)}
  .iconbtn{width:34px;height:34px;flex:none;display:grid;place-items:center;border:1px solid var(--border);
    background:var(--card);border-radius:9px;cursor:pointer;font-size:14px}
  .iconbtn:hover{background:var(--hover)}

  /* ---------- main ---------- */
  .main{flex:1;min-width:0;display:flex;flex-direction:column}
  .topbar{position:sticky;top:0;z-index:10;background:var(--bg);border-bottom:1px solid var(--border);
    display:flex;align-items:center;gap:12px;padding:14px 26px}
  .search{flex:1;max-width:560px;position:relative}
  .search svg{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--faint)}
  .search input{width:100%;height:38px;background:var(--side);border:1px solid var(--border);border-radius:10px;
    padding:0 12px 0 35px;font:inherit;color:var(--fg);outline:none}
  .search input:focus{border-color:var(--ring);box-shadow:0 0 0 3px rgba(120,120,130,.18);background:var(--card)}
  .spacer{flex:1}
  .ddl{position:relative}
  .ddl select{height:38px;appearance:none;-webkit-appearance:none;background:var(--card);border:1px solid var(--border);
    border-radius:9px;padding:0 30px 0 12px;font:inherit;color:var(--fg2);font-weight:550;cursor:pointer;outline:none}
  .ddl select:hover{background:var(--hover)}
  .ddl .cv{position:absolute;right:10px;top:50%;transform:translateY(-50%);pointer-events:none;color:var(--faint);font-size:11px}
  .ddl-btn{height:38px;display:inline-flex;align-items:center;gap:7px;background:var(--card);border:1px solid var(--border);
    border-radius:9px;padding:0 11px 0 13px;font:inherit;color:var(--fg2);font-weight:550;cursor:pointer}
  .ddl-btn:hover{background:var(--hover)}
  .ddl-btn.menu-open{border-color:var(--ring);background:var(--hover)}
  .ddl-btn .lbl-cat{white-space:nowrap}
  .ddl-btn .cv{display:grid;place-items:center;color:var(--faint);transition:transform .22s cubic-bezier(.2,.8,.25,1)}
  .ddl-btn.menu-open .cv,.cat-trigger.menu-open .cv{transform:rotate(180deg)}
  .seg{display:inline-flex;border:1px solid var(--border);border-radius:9px;overflow:hidden;background:var(--card)}
  .seg button{width:36px;height:38px;border:0;background:none;cursor:pointer;color:var(--mut);display:grid;place-items:center}
  .seg button.active{background:var(--active);color:var(--fg)}
  .seg button+button{border-left:1px solid var(--border)}

  .content{padding:22px 26px 80px}
  .head{display:flex;align-items:baseline;gap:10px;margin-bottom:4px}
  .head h2{margin:0;font-size:19px;font-weight:680;letter-spacing:-.01em}
  .head .cnt{color:var(--mut);font-size:13px}
  .head .dot{width:9px;height:9px;border-radius:50%;align-self:center}
  .head-sub{color:var(--faint);font-size:12.5px;margin:0 0 18px}

  /* grid + cards */
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,280px),1fr));gap:14px}
  .card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
    overflow:hidden;display:flex;flex-direction:column;
    transition:border-color .18s ease,box-shadow .25s ease,transform .25s cubic-bezier(.2,.7,.25,1)}
  .card:hover{border-color:#cdced3;box-shadow:0 10px 26px rgba(20,20,30,.11);transform:translateY(-3px)}
  html.dark .card:hover{border-color:#363b45;box-shadow:0 10px 26px rgba(0,0,0,.5)}
  .cover{position:relative;height:156px;background:#efe7d6;border-bottom:1px solid var(--border);overflow:hidden}
  .cover img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .6s cubic-bezier(.2,.7,.25,1)}
  .card:hover .cover img{transform:scale(1.06)}
  /* frosted "glass" controls sitting on the cover (covers are always light cream,
     so glass text stays dark in both themes) */
  .glass{backdrop-filter:blur(9px) saturate(1.4);-webkit-backdrop-filter:blur(9px) saturate(1.4);
    background:rgba(255,255,255,.42);border:1px solid rgba(255,255,255,.6);
    box-shadow:0 2px 10px rgba(40,30,20,.14);color:#1d1d1f}
  .ov-open{position:absolute;top:10px;right:10px;width:32px;height:32px;border-radius:50%;display:grid;place-items:center;
    color:#1d1d1f;font-size:14px;cursor:pointer;transition:transform .12s,background .15s}
  .ov-open:hover{transform:translateY(-1px);background:rgba(255,255,255,.72)}
  .ov-user{position:absolute;left:10px;bottom:10px;max-width:calc(100% - 20px);height:26px;border-radius:999px;
    display:inline-flex;align-items:center;padding:0 11px;color:#1d1d1f;font-size:12px;font-weight:600;
    overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .ov-user:hover{background:rgba(255,255,255,.66)}
  /* category trigger — a fully-clickable button (no native select) */
  .cat-trigger{font:inherit;cursor:pointer}
  .ov-cat{position:absolute;left:10px;top:10px;max-width:calc(100% - 54px);height:30px;border-radius:999px;
    display:inline-flex;align-items:center;gap:5px;padding:0 9px 0 12px;color:#1d1d1f;font-size:13px;font-weight:650}
  .ov-cat:hover{background:rgba(255,255,255,.62)}
  .ov-cat .lbl-cat{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .ov-cat .cv{display:grid;place-items:center;color:#3a3a3a;flex:none}
  /* glass dropdown menu (shared, themed because it floats over the page) */
  .cat-menu{position:fixed;z-index:90;display:none;min-width:172px;max-height:330px;overflow-y:auto;overscroll-behavior:contain;padding:6px;
    border-radius:13px;background:rgba(255,255,255,.74);backdrop-filter:blur(18px) saturate(1.5);
    -webkit-backdrop-filter:blur(18px) saturate(1.5);border:1px solid rgba(255,255,255,.6);
    box-shadow:0 14px 44px rgba(30,25,20,.24);
    opacity:0;transform:translateY(-7px) scale(.96);transform-origin:top left;
    transition:opacity .15s ease,transform .17s cubic-bezier(.2,.8,.25,1)}
  .cat-menu.open{opacity:1;transform:none}
  html.dark .cat-menu{background:rgba(22,23,27,.7);border-color:rgba(255,255,255,.12);box-shadow:0 14px 44px rgba(0,0,0,.55)}
  .cat-opt{display:flex;align-items:center;justify-content:space-between;gap:10px;width:100%;text-align:left;border:0;
    background:none;cursor:pointer;padding:8px 10px;border-radius:9px;font:inherit;font-size:13px;color:var(--fg)}
  .cat-opt:hover{background:var(--hover)}
  .cat-opt.sel{font-weight:650}
  .cat-opt .ck{color:var(--mut)}
  .body{padding:13px 14px 14px;display:flex;flex-direction:column;gap:8px}
  .caption{font-size:13px;line-height:1.5;color:var(--fg);font-weight:550}
  .caption .ct{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .caption.expanded .ct{-webkit-line-clamp:unset;overflow:visible}
  .caption.empty{color:var(--mut);font-style:italic;font-weight:400}
  .caption .more{display:none;background:none;border:0;color:var(--mut);font:inherit;font-size:12px;font-weight:600;
    cursor:pointer;padding:3px 0 0;text-decoration:underline;text-underline-offset:2px}
  .caption .more:hover{color:var(--fg)}
  .c-head{display:flex;align-items:center;gap:8px}
  .catwrap{flex:1;min-width:0;position:relative;display:flex;align-items:center}
  .catsel{max-width:100%;appearance:none;-webkit-appearance:none;background:transparent;border:0;
    font:inherit;font-size:15px;font-weight:650;letter-spacing:-.01em;color:var(--fg);cursor:pointer;
    padding:3px 22px 3px 6px;margin-left:-6px;border-radius:7px;outline:none;text-overflow:ellipsis}
  .catsel:hover{background:var(--hover)}
  .catsel:focus{box-shadow:0 0 0 3px rgba(120,120,130,.22)}
  .catwrap .cv{position:absolute;right:5px;pointer-events:none;color:var(--faint);font-size:11px}
  .c-open{width:30px;height:30px;flex:none;display:grid;place-items:center;border-radius:8px;color:var(--mut);border:1px solid transparent}
  .c-open:hover{background:var(--hover);color:var(--fg);border-color:var(--border)}
  .c-sub{display:flex;align-items:center;flex-wrap:wrap;gap:6px;color:var(--mut);font-size:12px;padding-left:1px}
  .c-sub .u{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:140px}
  .tag{display:inline-flex;align-items:center;height:20px;padding:0 8px;border-radius:6px;background:var(--pill);
    color:var(--pill-fg);font-size:11px;font-weight:600;text-transform:capitalize}
    .dotsep{color:var(--faint)}
  .divider{height:1px;background:var(--border2)}
  .c-foot{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
  .c-foot .fdate{color:var(--mut);font-size:11.5px;font-variant-numeric:tabular-nums;margin-right:2px}
  .pill{display:inline-flex;align-items:center;gap:5px;height:24px;padding:0 9px;border-radius:7px;background:var(--pill);
    color:var(--pill-fg);font-size:12px;font-weight:500;max-width:100%}
  .pill svg{opacity:.6;flex:none}
  .pill.none{color:var(--faint);font-style:italic;background:transparent;border:1px dashed var(--border)}

  /* list view */
  .list{display:flex;flex-direction:column;gap:7px}
  .row{display:flex;align-items:center;gap:13px;background:var(--card);border:1px solid var(--border);
    border-radius:10px;padding:9px 13px;transition:border-color .12s}
  .row:hover{border-color:#d4d4d8}
  html.dark .row:hover{border-color:#30343d}
  .row .thumb{width:52px;height:38px;border-radius:7px;overflow:hidden;flex:none;border:1px solid var(--border);background:#efe7d6}
  .row .thumb img{width:100%;height:100%;object-fit:cover;display:block}
  .rowcat{flex:0 0 auto;width:186px;height:32px;border:1px solid var(--border);background:var(--card);border-radius:8px;
    padding:0 9px 0 12px;display:inline-flex;align-items:center;gap:6px;justify-content:flex-start;text-align:left;
    color:var(--fg);font-size:13px;font-weight:600}
  .rowcat:hover{background:var(--hover);border-color:#d4d4d8}
  html.dark .rowcat:hover{border-color:#363b45}
  .rowcat .lbl-cat{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:left}
  .rowcat .cv{color:var(--faint);flex:none;display:grid;place-items:center;margin-left:auto;transition:transform .22s cubic-bezier(.2,.8,.25,1)}
  .row .rtitle{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--fg);font-weight:550}
  .row .rtitle.muted{color:var(--mut);font-weight:400}
  .row .ruser{flex:none;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--mut);font-size:12.5px}
  .row .ruser:hover{color:var(--fg);text-decoration:underline}
  .row .rdate{color:var(--mut);font-size:12px;flex:none;font-variant-numeric:tabular-nums;width:96px;text-align:right}

  .empty{padding:70px;text-align:center;color:var(--mut)}
  /* first-run / empty state */
  .firstrun{display:flex;justify-content:center;padding:36px 0 60px}
  .fr-card{width:560px;max-width:100%;background:var(--card);border:1px solid var(--border);border-radius:18px;
    overflow:hidden;box-shadow:0 10px 40px rgba(20,20,30,.07);animation:obIn .4s cubic-bezier(.2,.8,.25,1)}
  .fr-img{height:180px;background:#efe7d6;border-bottom:1px solid var(--border);overflow:hidden}
  .fr-img svg{width:100%;height:100%;display:block}
  .fr-body{padding:22px 24px 24px}
  .fr-eyebrow{font-size:11px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--faint);margin-bottom:9px}
  .fr-body h2{margin:0 0 10px;font-size:22px;font-weight:680;letter-spacing:-.01em}
  .fr-body p{margin:0 0 14px;color:var(--fg2);font-size:14px;line-height:1.6}
  .fr-sub{color:var(--mut) !important;font-size:12.5px !important}
  .fr-code{display:flex;align-items:center;gap:10px;background:var(--side);border:1px solid var(--border);
    border-radius:10px;padding:11px 12px;margin:0 0 16px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
  .fr-code code{flex:1;font-size:13px;color:var(--fg)}
  .fr-copy{border:1px solid var(--border);background:var(--card);border-radius:7px;padding:5px 10px;cursor:pointer;
    font:inherit;font-size:12px;font-weight:600;color:var(--fg2)}
  .fr-copy:hover{background:var(--hover)}
  .fr-actions{display:flex;gap:9px;flex-wrap:wrap}
  .more{grid-column:1/-1;text-align:center;padding:18px}
  .btn{height:36px;display:inline-flex;align-items:center;gap:6px;padding:0 14px;border-radius:9px;border:1px solid var(--border);
    background:var(--card);color:var(--fg);cursor:pointer;font:inherit;font-weight:550}
  .btn:hover{background:var(--hover)}

  /* modal + toast */
  .modal-bg{position:fixed;inset:0;background:rgba(20,20,28,.45);backdrop-filter:blur(3px);display:none;align-items:center;justify-content:center;z-index:60}
  .modal-bg.show{display:flex}
  .modal{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:22px;width:360px;box-shadow:0 20px 50px rgba(0,0,0,.25)}
  .modal h3{margin:0 0 5px;font-size:16px;font-weight:650}
  .modal p{margin:0 0 16px;color:var(--mut);font-size:12.5px}
  .modal input{width:100%;height:40px;background:var(--side);border:1px solid var(--border);color:var(--fg);border-radius:10px;padding:0 12px;outline:none;margin-bottom:16px}
  .modal input:focus{border-color:var(--ring)}
  .modal .row{display:flex;gap:8px;justify-content:flex-end;border:0;padding:0;background:none}
  .modal .row:hover{border:0}
  .modal .btn.primary{background:var(--fg);color:var(--bg);border-color:transparent}
  .toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(18px);background:var(--fg);color:var(--bg);
    padding:11px 17px;border-radius:10px;box-shadow:0 8px 30px rgba(0,0,0,.25);opacity:0;transition:.22s;font-size:13px;font-weight:550;z-index:70;pointer-events:none}
  .toast.show{opacity:1;transform:translateX(-50%) translateY(0)}

  /* topbar guide button */
  .guidebtn{height:38px;display:inline-flex;align-items:center;gap:6px;border:1px solid var(--border);background:var(--card);
    border-radius:9px;padding:0 12px;cursor:pointer;color:var(--fg2);font:inherit;font-weight:550}
  .guidebtn:hover{background:var(--hover);color:var(--fg)}
  .guidebtn svg{color:var(--mut)}

  /* onboarding modal (Reddit-style) */
  .ob-bg{position:fixed;inset:0;z-index:100;display:none;align-items:center;justify-content:center;padding:20px;
    background:rgba(15,15,20,.5);backdrop-filter:blur(4px)}
  .ob-bg.show{display:flex}
  .ob-bg.show{animation:obBgIn .25s ease}
  @keyframes obBgIn{from{opacity:0}to{opacity:1}}
  .ob{position:relative;width:452px;max-width:100%;max-height:calc(100vh - 40px);overflow:hidden;display:flex;flex-direction:column;
    background:var(--card);border:1px solid var(--border);border-radius:18px;box-shadow:0 30px 80px rgba(0,0,0,.45)}
  .ob-bg.show .ob{animation:obIn .36s cubic-bezier(.2,.8,.25,1)}
  @keyframes obIn{from{opacity:0;transform:translateY(18px) scale(.96)}to{opacity:1;transform:none}}
  .ob-x{position:absolute;top:13px;right:13px;z-index:3;width:30px;height:30px;border-radius:50%;border:0;cursor:pointer;
    display:grid;place-items:center;color:#1d1d1f;font-size:12px;background:rgba(255,255,255,.55);
    backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);transition:background .15s,transform .15s}
  .ob-x:hover{background:rgba(255,255,255,.8);transform:rotate(90deg)}
  .ob-img{height:204px;background:#efe7d6;overflow:hidden;border-bottom:1px solid var(--border)}
  .ob-img svg{width:100%;height:100%;display:block}
  .ob-body{padding:20px 22px 4px}
  .ob-eyebrow{font-size:11px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--faint);margin-bottom:9px}
  .ob-title{margin:0 0 9px;font-size:20px;font-weight:680;letter-spacing:-.01em;color:var(--fg)}
  .ob-desc{margin:0;color:var(--fg2);font-size:14px;line-height:1.56}
  .ob-tip{margin:13px 0 0;color:var(--mut);font-size:12.5px;line-height:1.5;padding:2px 0 2px 12px;border-left:2px solid var(--border)}
  .ob-credit{margin:14px 0 0;font-size:12px;color:var(--mut)}
  .ob-credit a{color:var(--fg);text-decoration:underline;text-underline-offset:2px;font-weight:550}
  .ob-foot{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:18px 22px 20px}
  .ob-dots{display:flex;gap:7px}
  .ob-dot{width:7px;height:7px;border-radius:50%;background:var(--border2);cursor:pointer;transition:width .25s ease,background .25s ease}
  .ob-dot.active{background:var(--fg);width:22px;border-radius:4px}
  .ob-btns{display:flex;gap:8px}
  @keyframes obSlide{from{opacity:0;transform:translateX(14px)}to{opacity:1;transform:none}}
  .ob-slide.anim{animation:obSlide .32s cubic-bezier(.2,.7,.25,1)}

  /* ---------- desktop collapsible sidebar ---------- */
  @media(min-width:861px){
    .side{transition:width .3s cubic-bezier(.2,.8,.25,1),opacity .22s ease}
    .app.side-collapsed .side{width:0;min-width:0;opacity:0;border-right-color:transparent;overflow:hidden;pointer-events:none}
    .app.side-collapsed .sideexpand{display:grid}
  }

  /* ---------- responsive ---------- */
  .navtoggle{display:none}
  .side-backdrop{display:none}
  @media(max-width:860px){ .side-collapse{display:none} }
  @media(max-width:1024px){
    .side{width:212px}
    .content{padding:20px 20px 80px}
    .topbar{padding:13px 20px}
  }
  /* tablet & mobile: sidebar becomes an off-canvas drawer */
  @media(max-width:860px){
    .side{position:fixed;z-index:60;left:0;top:0;width:270px;height:100dvh;transform:translateX(-100%);
      transition:transform .28s cubic-bezier(.2,.8,.25,1)}
    .side.open{transform:none;box-shadow:0 24px 70px rgba(0,0,0,.35)}
    .side-backdrop{display:block;position:fixed;inset:0;z-index:55;background:rgba(10,10,14,.45);
      opacity:0;visibility:hidden;transition:opacity .25s ease,visibility .25s ease;backdrop-filter:blur(2px)}
    .side-backdrop.show{opacity:1;visibility:visible}
    .navtoggle{display:grid;place-items:center;width:38px;height:38px;flex:none;border:1px solid var(--border);
      background:var(--card);border-radius:9px;cursor:pointer;color:var(--fg)}
    .navtoggle:hover{background:var(--hover)}
    .main{min-width:0}
    .topbar{padding:12px 16px;gap:9px}
    .content{padding:18px 16px 80px}
    .search{max-width:none}
    .head h2{font-size:18px}
  }
  /* phones: stack the toolbar, simplify list rows */
  @media(max-width:560px){
    .topbar{flex-wrap:wrap}
    .search{order:5;flex:1 1 100%}
    .spacer{display:none}
    .guidebtn span{display:none}
    .guidebtn{padding:0 10px}
    .grid{grid-template-columns:1fr;gap:12px}
    .row{flex-wrap:wrap;gap:9px 11px}
    .rowcat{order:2;width:auto;min-width:140px;flex:1 1 auto}
    .row .rtitle{order:1;flex:1 1 100%}
    .row .ruser{display:none}
    .row .rdate{display:none}
    .ob-img{height:172px}
    .ob-title{font-size:18px}
  }

  /* ---------- motion ---------- */
  @keyframes cardIn{from{opacity:0;transform:translateY(12px) scale(.985)}to{opacity:1;transform:none}}
  .card.in,.row.in{animation:cardIn .44s cubic-bezier(.2,.7,.25,1) backwards}
  @keyframes cardInFast{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
  .card.in.fast,.row.in.fast{animation:cardInFast .3s ease backwards}
  @keyframes modalIn{from{opacity:0;transform:translateY(12px) scale(.97)}to{opacity:1;transform:none}}
  .modal-bg.show .modal{animation:modalIn .24s cubic-bezier(.2,.8,.25,1) both}
  @keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
  .head h2,.head .cnt,.head-sub{animation:fadeUp .35s ease both}

  /* hover / press micro-interactions */
  .nav,.chip,.btn,.sbtn,.iconbtn,.seg button,.pill,.cat-opt,.ov-open,.ov-cat,.ov-user,.c-open,.rowcat,
  .switch,.cat-trigger,.search input,.ddl select{
    transition:background .16s ease,color .16s ease,border-color .16s ease,transform .14s cubic-bezier(.2,.7,.25,1),box-shadow .16s ease}
  .nav:hover{transform:translateX(3px)}
  .nav:active{transform:translateX(1px) scale(.99)}
  .cat-opt:hover{transform:translateX(2px)}
  .chip:hover{transform:translateY(-1px)}
  .chip:active{transform:translateY(0) scale(.97)}
  .btn:hover,.sbtn:hover,.iconbtn:hover{transform:translateY(-1px)}
  .btn:active,.sbtn:active,.iconbtn:active,.seg button:active{transform:translateY(0) scale(.95)}
  .c-open:hover{transform:translateY(-1px)}
  .pill{transition:transform .14s ease,background .16s ease}
  .card:hover .pill{background:var(--hover)}
  .iconbtn svg{transition:transform .3s cubic-bezier(.2,.7,.25,1)}
  .iconbtn:hover svg{transform:rotate(20deg) scale(1.08)}
  .seg button svg{transition:transform .2s ease}
  .seg button:hover svg{transform:scale(1.12)}
  .ov-open:hover{transform:translateY(-1px) rotate(8deg)}
  .lbl-cat{transition:none}
  .cat-trigger .cv{transition:transform .18s ease}
  .cat-trigger:hover .cv{transform:translateY(1px)}
  .ddl select:focus + .cv,.ddl:focus-within .cv{transform:translateY(1px)}
  .more{transition:color .15s ease,transform .14s ease}
  .more:active{transform:scale(.96)}
  .toast{transition:opacity .25s ease,transform .3s cubic-bezier(.2,.8,.25,1)}

  @media (prefers-reduced-motion: reduce){
    *,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;
      transition-duration:.01ms!important;scroll-behavior:auto!important}
    .card:hover,.cover img,.card:hover .cover img{transform:none!important}
  }
</style>
</head>
<body>
<div class="app">
  <!-- sidebar -->
  <aside class="side">
    <div class="brand"><span class="ic"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 16.5A4.5 4.5 0 1 1 7.5 12 4.5 4.5 0 1 1 12 7.5a4.5 4.5 0 1 1 4.5 4.5 4.5 4.5 0 1 1-4.5 4.5"/><path d="M12 7.5V9"/><path d="M7.5 12H9"/><path d="M16.5 12H15"/><path d="M12 16.5V15"/><path d="m8 8 1.88 1.88"/><path d="M14.12 9.88 16 8"/><path d="m8 16 1.88-1.88"/><path d="M14.12 14.12 16 16"/></svg></span> <span class="brand-name">Posy</span><button class="side-collapse" id="sideCollapse" title="Collapse sidebar" aria-label="Collapse sidebar"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/><path d="m16 15-3-3 3-3"/></svg></button></div>
    <div class="side-scroll">
      <div class="sec">
        <div class="sec-h"><span>Categories</span><button id="addCatTop" title="New category">＋</button></div>
        <div id="navCats"></div>
      </div>
      <div class="sec">
        <div class="sec-h"><span>Collections</span><span class="hint" title="The collections you saved these reels into on Instagram. Click one to see just those reels.">ⓘ</span></div>
        <div id="navFolders"></div>
      </div>
    </div>
    <div class="side-foot">
      <button class="sbtn" id="export">⬇ Export</button>
      <button class="sbtn" id="reset">↺ Reset</button>
      <button class="iconbtn" id="themeSwitch" title="Toggle light / dark"><span id="themeIcon">🌙</span></button>
    </div>
    <div class="side-credit">Made by <a href="https://www.anandis.pro" target="_blank" rel="noopener">Anand Chauhan</a> · <a href="https://x.com/xyanandc" target="_blank" rel="noopener">@xyanandc</a></div>
  </aside>
  <div class="side-backdrop" id="sideBackdrop"></div>

  <!-- main -->
  <div class="main">
    <div class="topbar">
      <button class="navtoggle" id="navToggle" aria-label="Open menu"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg></button>
      <button class="sideexpand" id="sideExpand" title="Show sidebar" aria-label="Show sidebar"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/><path d="m14 9 3 3-3 3"/></svg></button>
      <div class="search">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
        <input type="search" id="q" placeholder="Search reels by folder, caption, username…" />
      </div>
      <button type="button" class="ddl-btn" id="typeBtn"><span class="lbl-cat" id="typeLbl">All types</span><span class="cv"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg></span></button>
      <div class="spacer"></div>
      <div class="seg">
        <button id="viewGrid" class="active" title="Grid view"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg></button>
        <button id="viewList" title="List view"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="9" y1="6" x2="20" y2="6"/><line x1="9" y1="12" x2="20" y2="12"/><line x1="9" y1="18" x2="20" y2="18"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/></svg></button>
      </div>
      <button type="button" class="guidebtn" id="infoGuide" title="Open the welcome guide"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg> Guide</button>
    </div>

    <div class="content">
      <div class="head"><span class="dot" id="headDot" style="display:none"></span><h2 id="headTitle">All reels</h2><span class="cnt" id="headCount"></span></div>
      <p class="head-sub" id="headSub"></p>
      <div id="grid" class="grid"></div>
      <div class="empty" id="empty" style="display:none">No reels match your filters.</div>
      <div class="firstrun" id="firstRun" style="display:none">
        <div class="fr-card">
          <div class="fr-img" id="frImg"></div>
          <div class="fr-body">
            <div class="fr-eyebrow">Nothing here yet</div>
            <h2>Add your Instagram saves 🌸</h2>
            <p>Posy could not find any saved reels. Drop your <b>unzipped</b> Instagram data export into the project folder, then run this in your terminal:</p>
            <div class="fr-code"><code>python3 main.py scan</code><button class="fr-copy" id="frCopy" title="Copy">Copy</button></div>
            <p class="fr-sub">New here? The README walks you through requesting your export from Instagram (Settings → Your information and permissions → Download your information).</p>
            <div class="fr-actions">
              <button class="btn primary" id="frGuide">Open the guide</button>
              <a class="btn" href="https://github.com/theacmajor/posy#readme" target="_blank" rel="noopener">Read the setup guide</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="modal-bg" id="modalBg">
  <div class="modal">
    <h3>New category</h3>
    <p>Name it. It appears in the sidebar and in every card's menu.</p>
    <input id="catName" placeholder="e.g. Brand Inspiration" maxlength="40" />
    <div class="row">
      <button class="btn" id="catCancel">Cancel</button>
      <button class="btn primary" id="catSave">Create</button>
    </div>
  </div>
</div>
<div class="cat-menu" id="catMenu"></div>

<div class="ob-bg" id="obBg" aria-hidden="true">
  <div class="ob" role="dialog" aria-modal="true" aria-labelledby="obTitle">
    <button class="ob-x" id="obClose" aria-label="Close guide">✕</button>
    <div class="ob-slide" id="obSlide">
      <div class="ob-img" id="obImg"></div>
      <div class="ob-body">
        <div class="ob-eyebrow" id="obEye"></div>
        <h2 class="ob-title" id="obTitle"></h2>
        <p class="ob-desc" id="obDesc"></p>
        <p class="ob-tip" id="obTip"></p>
        <p class="ob-credit" id="obCredit"></p>
      </div>
    </div>
    <div class="ob-foot">
      <div class="ob-dots" id="obDots"></div>
      <div class="ob-btns">
        <button class="btn" id="obPrev">Previous</button>
        <button class="btn primary" id="obNext">Next</button>
      </div>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const DATA = /*__DATA__*/;
const STATS = /*__STATS__*/;
const BASE_CATS = /*__CATS__*/;
const HASCOVERS = /*__COVERS__*/;   // true when a unique watercolor cover exists per reel
const ONBOARD_IMAGES = /*__ONBOARD__*/;   // floral SVG art, one per onboarding step

const LS_OVR='ltsop_overrides_v2', LS_CATS='ltsop_custom_cats_v2', LS_THEME='ltsop_theme', LS_VIEW='ltsop_view';
const load=(k,f)=>{ try{ return JSON.parse(localStorage.getItem(k)) ?? f }catch{ return f } };
const save=(k,v)=>localStorage.setItem(k,JSON.stringify(v));
const dedupe=a=>[...new Set(a)];

let overrides=load(LS_OVR,{}), customCats=load(LS_CATS,[]);
let CATS=dedupe([...BASE_CATS,...customCats]);
DATA.forEach(i=>{ if(overrides[i.id]) i.final_category=overrides[i.id]; });

let state={ q:"", type:"", folder:"", cat:"", view:load(LS_VIEW,'grid'), limit:300 };

function esc(s){ return (s==null?"":String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function coverFor(id){ return HASCOVERS ? `covers/${encodeURIComponent(id)}.svg` : null; }
function foldersOf(i){ return (i.collection_name||'').split(';').map(s=>s.trim()).filter(Boolean); }
function toast(m){ const t=document.getElementById('toast'); t.textContent=m; t.classList.add('show'); clearTimeout(t._t); t._t=setTimeout(()=>t.classList.remove('show'),1600); }
function catCounts(){ const c={}; CATS.forEach(x=>c[x]=0); DATA.forEach(i=>{ const k=i.final_category||'Uncategorized'; c[k]=(c[k]||0)+1; }); return c; }
function folderCounts(){ const c={}; DATA.forEach(i=>foldersOf(i).forEach(f=>{ c[f]=(c[f]||0)+1; })); return c; }
function fmtDate(iso){ if(!iso) return ''; const d=new Date(iso); if(isNaN(d.getTime())) return String(iso).slice(0,10);
  return d.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}); }
const FOLDER_SVG='<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7a2 2 0 0 1 2-2h3l2 2h7a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/></svg>';
const CHEVRON='<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>';
// Build a short, readable heading from the caption (strip urls/@/#/emoji),
// falling back to the username or a neutral label.
function headingOf(i){
  let c=(i.caption||'').replace(/https?:\/\/\S+/g,' ').replace(/[#@][\w.]+/g,' ');
  c=c.replace(/[^\p{L}\p{N}\s.,'’&()\-]/gu,' ').replace(/\s+/g,' ').trim();
  if(!c) return { text:(i.username?('@'+i.username):'Untitled reel'), muted:true };
  let first=c.split(/(?<=[.!?])\s/)[0];
  let words=first.split(' ').slice(0,10).join(' ');
  if(words.length>72) words=words.slice(0,72).trim()+'…';
  return { text: words.charAt(0).toUpperCase()+words.slice(1), muted:false };
}

// theme + view
function applyTheme(t){ const dark=t==='dark'; document.documentElement.classList.toggle('dark',dark);
  document.getElementById('themeIcon').textContent=dark?'🌙':'☀️'; }
let theme=load(LS_THEME,null) || (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
applyTheme(theme);
document.getElementById('themeSwitch').onclick=()=>{ theme=(theme==='dark'?'light':'dark'); save(LS_THEME,theme); applyTheme(theme); };
function applyView(){ document.getElementById('viewGrid').classList.toggle('active',state.view==='grid');
  document.getElementById('viewList').classList.toggle('active',state.view==='list'); }

// sidebar
function renderSidebar(){
  const cc=catCounts(), fc=folderCounts();
  const cats=document.getElementById('navCats');
  let h=`<button class="nav ${state.cat===''&&state.folder===''?'active':''}" data-cat=""><span class="ico"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg></span><span class="nm">All reels</span><span class="ct">${DATA.length}</span></button>`;
  h+=CATS.map(c=>`<button class="nav ${state.cat===c?'active':''}" data-cat="${esc(c)}"><span class="dot" style="background:var(--faint)"></span><span class="nm">${esc(c)}</span><span class="ct">${cc[c]||0}</span></button>`).join('');
  cats.innerHTML=h;
  cats.querySelectorAll('.nav').forEach(n=>n.onclick=()=>{ state.cat=n.dataset.cat; state.folder=''; state.limit=300; renderAll(true); closeDrawer(); });

  const folders=Object.keys(fc).sort((a,b)=>a.toLowerCase().localeCompare(b.toLowerCase()));
  const fEl=document.getElementById('navFolders');
  fEl.innerHTML=folders.map(f=>`<button class="nav ${state.folder===f?'active':''}" data-folder="${esc(f)}"><span class="ico">${FOLDER_SVG}</span><span class="nm">${esc(f)}</span><span class="ct">${fc[f]}</span></button>`).join('');
  fEl.querySelectorAll('.nav').forEach(n=>n.onclick=()=>{ state.folder=n.dataset.folder; state.cat=''; state.limit=300; renderAll(true); closeDrawer(); });
}

function filtered(){
  const q=state.q.toLowerCase();
  return DATA.filter(i=>{
    if(state.type && i.type!==state.type) return false;
    if(state.cat && (i.final_category||'Uncategorized')!==state.cat) return false;
    if(state.folder && !foldersOf(i).includes(state.folder)) return false;
    if(q){ const hay=[i.collection_name,i.caption,i.username,(i.hashtags||[]).join(' '),i.url].join(' ').toLowerCase();
      if(!hay.includes(q)) return false; }
    return true;
  });
}

function catTrigger(i,variant){
  const cat=i.final_category||'Uncategorized';
  const cls=variant==='cover'?'cat-trigger ov-cat glass':'cat-trigger rowcat';
  return `<button type="button" class="${cls}" data-id="${esc(i.id)}"><span class="lbl-cat">${esc(cat)}</span><span class="cv">${CHEVRON}</span></button>`;
}
function captionBlock(i){
  const cap=(i.caption||'').trim();
  if(!cap) return `<div class="caption empty">${i.username?'@'+esc(i.username):'Untitled reel'}</div>`;
  return `<div class="caption"><span class="ct">${esc(cap)}</span><button type="button" class="more">more</button></div>`;
}
function animAttrs(kind,idx,animate){
  if(!animate) return {cls:kind,sty:''};
  const fast=animate==='fast';
  const cls=kind+(fast?' in fast':' in');
  const step=fast?9:24, cap=fast?16:28;
  return {cls, sty:` style="animation-delay:${Math.min(idx,cap)*step}ms"`};
}
function cardGrid(i,idx,animate){
  const fs=foldersOf(i);
  const pills=fs.length?fs.map(f=>`<span class="pill">${FOLDER_SVG}${esc(f)}</span>`).join(''):`<span class="pill none">No folder</span>`;
  const cov=coverFor(i.id);
  const meta=`<span class="tag">${esc(i.type)}</span><span class="fdate">${esc(fmtDate(i.saved_at))}</span>`;
  const a=animAttrs('card',idx,animate);
  return `<div class="${a.cls}" data-id="${esc(i.id)}"${a.sty}>
    <div class="cover">
      ${cov?`<img loading="lazy" src="${esc(cov)}" alt="" />`:''}
      ${catTrigger(i,'cover')}
      <a class="ov-open glass" href="${esc(i.url)}" target="_blank" rel="noopener" title="Open on Instagram">↗</a>
      ${i.username?`<a class="ov-user glass" href="https://www.instagram.com/${encodeURIComponent(i.username)}/" target="_blank" rel="noopener" title="Open @${esc(i.username)} on Instagram">@${esc(i.username)}</a>`:''}
    </div>
    <div class="body">
      ${captionBlock(i)}
      <div class="divider"></div>
      <div class="c-foot">${meta}${pills}</div>
    </div>
  </div>`;
}
function cardRow(i,idx,animate){
  const cov=coverFor(i.id);
  const thumb=cov?`<span class="thumb"><img loading="lazy" src="${esc(cov)}" alt="" /></span>`:'';
  const h=headingOf(i);
  const a=animAttrs('row',idx,animate);
  return `<div class="${a.cls}" data-id="${esc(i.id)}"${a.sty}>
    ${thumb}
    ${catTrigger(i,'row')}
    <span class="rtitle${h.muted?' muted':''}">${esc(h.text)}</span>
    ${i.username?`<a class="ruser" href="https://www.instagram.com/${encodeURIComponent(i.username)}/" target="_blank" rel="noopener">@${esc(i.username)}</a>`:''}
    <span class="tag">${esc(i.type)}</span>
    <span class="rdate">${esc(fmtDate(i.saved_at))}</span>
    <a class="c-open" href="${esc(i.url)}" target="_blank" rel="noopener" title="Open on Instagram">↗</a>
  </div>`;
}

function renderHead(){
  let title='All reels', sub='Browse and organize the reels you saved on Instagram';
  if(state.cat){ title=state.cat; sub='Reels you’ve filed under '+state.cat; }
  else if(state.folder){ title=state.folder; sub='Reels from your “'+state.folder+'” saved folder'; }
  document.getElementById('headTitle').textContent=title;
  document.getElementById('headSub').textContent=sub;
}

function renderGrid(animate){
  const rows=filtered(); const grid=document.getElementById('grid');
  document.getElementById('headCount').textContent=`${rows.length} ${rows.length===1?'reel':'reels'}`;
  document.getElementById('empty').style.display=rows.length?'none':'block';
  grid.className=state.view==='list'?'list':'grid';
  const render=state.view==='list'?cardRow:cardGrid;
  const shown=rows.slice(0,state.limit);
  grid.innerHTML=shown.map((it,idx)=>render(it,idx,animate)).join('')+
    (rows.length>shown.length?`<div class="more"><button class="btn" id="loadMore">Show ${rows.length-shown.length} more</button></div>`:'');
  // reveal "more" only on captions that actually overflow two lines
  if(state.view!=='list') grid.querySelectorAll('.caption .ct').forEach(ct=>{
    if(ct.scrollHeight-ct.clientHeight>2){ const b=ct.parentElement.querySelector('.more'); if(b) b.style.display='inline-block'; }
  });
  const lm=document.getElementById('loadMore'); if(lm) lm.onclick=()=>{ state.limit+=300; renderGrid(false); };
}

function renderAll(animate){ renderSidebar(); renderHead(); renderGrid(animate); }

// actions
function moveItem(id,cat){
  const it=DATA.find(x=>x.id===id); if(!it) return;
  it.final_category=cat; overrides[id]=cat; save(LS_OVR,overrides);
  renderSidebar(); renderHead(); renderGrid(false);
  toast(`Moved to “${cat}”`);
}
function addCategory(name){
  name=(name||'').trim(); if(!name) return false;
  if(CATS.some(c=>c.toLowerCase()===name.toLowerCase())){ toast('That category already exists'); return false; }
  customCats.push(name); save(LS_CATS,customCats); CATS=dedupe([...BASE_CATS,...customCats]);
  renderAll(false); toast(`Created “${name}”`); return true;
}
function exportData(){
  const blob=new Blob([JSON.stringify(DATA,null,2)],{type:'application/json'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='saved_items.json'; a.click(); URL.revokeObjectURL(a.href);
  toast('Exported saved_items.json to Downloads');
}
function resetAll(){
  if(!confirm('Undo ALL your category changes and custom categories?')) return;
  localStorage.removeItem(LS_OVR); localStorage.removeItem(LS_CATS); location.reload();
}

// custom glass dropdown — shared by the on-card category pills AND the Type filter
let menuTrigger=null, menuTimer=null;
const menuEl=document.getElementById('catMenu');
const TYPE_OPTIONS=[{value:'',label:'All types'},{value:'reel',label:'Reels'},{value:'post',label:'Posts'},{value:'unknown',label:'Unknown'}];
function optsHTML(options,current){
  return options.map(o=>`<button type="button" class="cat-opt ${o.value===current?'sel':''}" data-v="${esc(o.value)}">${esc(o.label)}${o.value===current?'<span class="ck">✓</span>':''}</button>`).join('');
}
function showMenu(trigger,html,onPick){
  clearTimeout(menuTimer);
  if(menuTrigger) menuTrigger.classList.remove('menu-open');
  menuTrigger=trigger; trigger.classList.add('menu-open');
  menuEl.innerHTML=html; menuEl.classList.remove('open'); menuEl.style.display='block';
  const r=trigger.getBoundingClientRect(), mw=menuEl.offsetWidth, mh=menuEl.offsetHeight;
  let left=r.left, top=r.bottom+6;
  if(left+mw>window.innerWidth-8) left=window.innerWidth-8-mw;
  if(top+mh>window.innerHeight-8) top=Math.max(8,r.top-6-mh);
  menuEl.style.left=Math.max(8,left)+'px'; menuEl.style.top=top+'px';
  void menuEl.offsetWidth;             // reflow so the open transition runs
  menuEl.classList.add('open');
  menuEl.querySelectorAll('.cat-opt').forEach(b=>b.onclick=()=>{ onPick(b.dataset.v); closeMenu(); });
}
function closeMenu(){
  if(!menuTrigger) return;
  menuTrigger.classList.remove('menu-open'); menuTrigger=null;
  menuEl.classList.remove('open'); clearTimeout(menuTimer);
  menuTimer=setTimeout(()=>{ if(!menuTrigger) menuEl.style.display='none'; },180);
}
function openCatMenu(t){
  const id=t.dataset.id; const it=DATA.find(x=>x.id===id); const cur=it?(it.final_category||'Uncategorized'):'';
  showMenu(t, optsHTML(CATS.map(c=>({value:c,label:c})),cur), v=>moveItem(id,v));
}
function openTypeMenu(t){
  showMenu(t, optsHTML(TYPE_OPTIONS,state.type), v=>{
    state.type=v; state.limit=300;
    document.getElementById('typeLbl').textContent=(TYPE_OPTIONS.find(o=>o.value===v)||{}).label||'All types';
    renderGrid(true);
  });
}
document.addEventListener('click',e=>{
  const more=e.target.closest&&e.target.closest('.caption .more');
  if(more){ const cap=more.closest('.caption'); const ex=cap.classList.toggle('expanded'); more.textContent=ex?'less':'more'; return; }
  const typeBtn=e.target.closest&&e.target.closest('#typeBtn');
  if(typeBtn){ e.preventDefault(); (menuTrigger===typeBtn)?closeMenu():openTypeMenu(typeBtn); return; }
  const trig=e.target.closest&&e.target.closest('.cat-trigger');
  if(trig){ e.preventDefault(); (menuTrigger===trig)?closeMenu():openCatMenu(trig); return; }
  if(!(e.target.closest&&e.target.closest('#catMenu'))) closeMenu();
});
// close on page scroll only (capture would also fire for the menu's own scroll)
window.addEventListener('scroll',closeMenu);
window.addEventListener('resize',closeMenu);
document.addEventListener('keydown',e=>{ if(e.key==='Escape') closeMenu(); });

// modal
const modal=document.getElementById('modalBg'), nameInput=document.getElementById('catName');
function openModal(){ modal.classList.add('show'); nameInput.value=''; setTimeout(()=>nameInput.focus(),30); }
function closeModal(){ modal.classList.remove('show'); }
document.getElementById('catCancel').onclick=closeModal;
document.getElementById('catSave').onclick=()=>{ if(addCategory(nameInput.value)) closeModal(); };
nameInput.addEventListener('keydown',e=>{ if(e.key==='Enter'){ if(addCategory(nameInput.value)) closeModal(); } if(e.key==='Escape') closeModal(); });
modal.addEventListener('click',e=>{ if(e.target===modal) closeModal(); });

// mobile drawer
const appEl=document.querySelector('.app');
const sideEl=document.querySelector('.side'), sideBackdrop=document.getElementById('sideBackdrop');
function closeDrawer(){ sideEl.classList.remove('open'); sideBackdrop.classList.remove('show'); }
function toggleDrawer(){ const o=sideEl.classList.toggle('open'); sideBackdrop.classList.toggle('show',o); }
document.getElementById('navToggle').onclick=toggleDrawer;
sideBackdrop.onclick=closeDrawer;

// desktop collapse / expand
function setSideCollapsed(c){ appEl.classList.toggle('side-collapsed',c); save('posy_side_collapsed',c?1:0); }
document.getElementById('sideCollapse').onclick=()=>setSideCollapsed(true);
document.getElementById('sideExpand').onclick=()=>setSideCollapsed(false);
if(load('posy_side_collapsed',0)) appEl.classList.add('side-collapsed');

// wire
document.getElementById('q').oninput=e=>{ state.q=e.target.value; state.limit=300; renderGrid('fast'); };
document.getElementById('addCatTop').onclick=openModal;
document.getElementById('export').onclick=exportData;
document.getElementById('reset').onclick=resetAll;
document.getElementById('viewGrid').onclick=()=>{ state.view='grid'; save(LS_VIEW,'grid'); applyView(); renderGrid(true); };
document.getElementById('viewList').onclick=()=>{ state.view='list'; save(LS_VIEW,'list'); applyView(); renderGrid(true); };

// ---- onboarding guide (Reddit-style carousel) ----
const OB_STEPS=[
  {eye:'Getting started', title:'Welcome to Posy 🌸',
   desc:'Posy turns the reels and posts you saved on Instagram into a calm, organized library, built entirely from your own data export.',
   tip:'It runs 100% locally in your browser. No logins, no scraping. Your data never leaves your computer.'},
  {eye:'Browse', title:'Categories & Collections',
   desc:'The sidebar gives you two ways in. Categories is a tidy scheme like Fitness, Food, Travel. Collections are the original folders you saved into on Instagram. Click either to filter.',
   tip:'“All reels” shows everything, and the count next to each item updates live as you organize.'},
  {eye:'Organize', title:'Categorize in one click',
   desc:'Every card has a category pill on its cover. Click it and pick a new category from the dropdown. The card moves instantly and your choice saves automatically.',
   tip:'Switch to list view to sort a whole collection fast, row by row.'},
  {eye:'Find & read', title:'Search, switch views, read captions',
   desc:'Search by folder, caption or username, toggle between grid and list, expand any caption with “more”, and open the original reel with the ↗ button.',
   tip:'Filter a Collection first, then sort just those reels into Categories.'},
  {eye:'Make it yours', title:'Create, theme & export',
   desc:'Add your own categories with the ＋ button, switch between light and dark mode at the bottom of the sidebar, and Export your organized library to a file whenever you like.',
   tip:'Reopen this guide anytime from the “Guide” button at the top right.'},
];
const obBg=document.getElementById('obBg'), obSlide=document.getElementById('obSlide');
let obStep=0;
function obRender(i){
  obStep=Math.max(0,Math.min(OB_STEPS.length-1,i));
  const s=OB_STEPS[obStep];
  document.getElementById('obImg').innerHTML=ONBOARD_IMAGES[obStep%ONBOARD_IMAGES.length]||'';
  document.getElementById('obEye').textContent=`${s.eye} · ${obStep+1} / ${OB_STEPS.length}`;
  document.getElementById('obTitle').textContent=s.title;
  document.getElementById('obDesc').textContent=s.desc;
  const tip=document.getElementById('obTip'); tip.textContent=s.tip?('Pro tip: '+s.tip):''; tip.style.display=s.tip?'block':'none';
  const credit=document.getElementById('obCredit');
  if(obStep===0){ credit.style.display='block'; credit.innerHTML='Made by <a href="https://www.anandis.pro" target="_blank" rel="noopener">Anand Chauhan</a> · <a href="https://x.com/xyanandc" target="_blank" rel="noopener">@xyanandc</a>'; }
  else credit.style.display='none';
  document.getElementById('obPrev').style.visibility=obStep===0?'hidden':'visible';
  document.getElementById('obNext').textContent=obStep===OB_STEPS.length-1?'Finish':'Next';
  document.getElementById('obDots').innerHTML=OB_STEPS.map((_,k)=>`<span class="ob-dot ${k===obStep?'active':''}" data-k="${k}"></span>`).join('');
  document.getElementById('obDots').querySelectorAll('.ob-dot').forEach(d=>d.onclick=()=>obRender(+d.dataset.k));
  obSlide.classList.remove('anim'); void obSlide.offsetWidth; obSlide.classList.add('anim');
}
function obOpen(){ obBg.classList.add('show'); obBg.setAttribute('aria-hidden','false'); obRender(0); }
function obClose(){ obBg.classList.remove('show'); obBg.setAttribute('aria-hidden','true'); }
function obDone(){ save('posy_onboarded',1); obClose(); }
document.getElementById('obClose').onclick=obDone;
document.getElementById('obPrev').onclick=()=>obRender(obStep-1);
document.getElementById('obNext').onclick=()=>{ if(obStep===OB_STEPS.length-1) obDone(); else obRender(obStep+1); };
obBg.addEventListener('click',e=>{ if(e.target===obBg) obDone(); });
document.getElementById('infoGuide').onclick=obOpen;
document.addEventListener('keydown',e=>{
  if(!obBg.classList.contains('show')) return;
  if(e.key==='Escape') obDone();
  else if(e.key==='ArrowRight') document.getElementById('obNext').click();
  else if(e.key==='ArrowLeft') obRender(obStep-1);
});
// first run / empty state (no saved items in the build)
function wireFirstRun(){
  const copyBtn=document.getElementById('frCopy');
  if(copyBtn) copyBtn.onclick=()=>{ try{ navigator.clipboard.writeText('python3 main.py scan'); }catch(e){}; copyBtn.textContent='Copied'; setTimeout(()=>copyBtn.textContent='Copy',1400); };
  const g=document.getElementById('frGuide'); if(g) g.onclick=obOpen;
}
if(DATA.length===0){
  document.getElementById('firstRun').style.display='flex';
  document.getElementById('frImg').innerHTML=ONBOARD_IMAGES[0]||'';
  document.getElementById('grid').style.display='none';
  document.getElementById('headTitle').textContent='Welcome to Posy';
  document.getElementById('headSub').textContent='Let’s get your saved reels in here.';
  document.getElementById('headCount').textContent='';
  wireFirstRun();
}else{
  applyView(); renderAll(true);
  if(!load('posy_onboarded',0)) setTimeout(obOpen,400);
}
</script>
</body>
</html>
"""
