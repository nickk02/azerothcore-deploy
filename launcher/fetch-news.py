#!/usr/bin/env python3
"""
Scrapes the official WoW news page and renders a small HTML page for the
WotLK-era launcher's embedded browser (IE7/8 engine, so: tables, inline
styles, no modern CSS).

Run on a timer; writes index.html into the docroot the launcher hits.
"""

import html
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

SOURCE = "https://worldofwarcraft.blizzard.com/en-us/news"
BASE = "https://worldofwarcraft.blizzard.com"
DOCROOT = Path(__file__).parent
OUT = DOCROOT / "index.html"
MAX_ITEMS = 5
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

TILE_LINK = re.compile(r'<a class="Link[^"]*ArticleTile-link"\s+href="\s*([^"]+?)\s*"', re.I)
TILE_TITLE = re.compile(r'<div class="ArticleTile-title">(.*?)</div>', re.I | re.S)
TILE_SUB = re.compile(r'<div class="ArticleTile-subtitle">(.*?)</div>', re.I | re.S)


def clean(raw):
    """Strip tags/entities out of a scraped fragment."""
    text = re.sub(r"<[^>]+>", "", raw)
    text = html.unescape(text)
    return " ".join(text.split())


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def absolute(href):
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE + href
    return BASE + "/" + href


def parse(page):
    """
    Tile markup order is: subtitle, title, then the tile's <a href>.
    So each title binds to the NEXT link after it, and the subtitle
    immediately before it. Pairing a link to the following title
    silently shifts every headline onto the wrong article.
    """
    items = []
    links = list(TILE_LINK.finditer(page))

    for title_m in TILE_TITLE.finditer(page):
        title = clean(title_m.group(1))
        if not title:
            continue

        link = next((l for l in links if l.start() >= title_m.end()), None)
        if link is None:
            continue

        subtitle = ""
        subs = [s for s in TILE_SUB.finditer(page) if s.end() <= title_m.start()]
        if subs:
            gap = page[subs[-1].end():title_m.start()]
            # Only treat it as this tile's subtitle if it sits directly above.
            if len(gap) < 80:
                subtitle = clean(subs[-1].group(1))

        if any(existing["title"] == title for existing in items):
            continue

        items.append({"title": title, "subtitle": subtitle, "url": absolute(link.group(1))})
        if len(items) >= MAX_ITEMS:
            break
    return items


def render(items, stamp, ok=True):
    rows = []
    for item in items:
        rows.append(
            '<tr><td class="b">&bull;</td>'
            '<td class="i"><a href="{url}" target="_blank">{title}</a>'
            '{sub}</td></tr>'.format(
                url=html.escape(item["url"], quote=True),
                title=html.escape(item["title"]),
                sub=(
                    '<div class="s">{}</div>'.format(html.escape(item["subtitle"]))
                    if item["subtitle"]
                    else ""
                ),
            )
        )

    if not rows:
        rows.append(
            '<tr><td class="b">&bull;</td><td class="i">News feed unavailable.</td></tr>'
        )

    note = "Official World of Warcraft news" if ok else "Showing last cached copy"

    return """<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta http-equiv="X-UA-Compatible" content="IE=EmulateIE8">
<title>News</title>
<style type="text/css">
body {{ margin:0; padding:10px; background:#0a0e14; color:#d8dee9;
        font-family:"Trebuchet MS",Arial,sans-serif; font-size:12px; }}
table {{ width:100%; border-collapse:collapse; }}
td {{ padding:3px 2px 5px 2px; vertical-align:top; }}
td.b {{ width:12px; color:#e8b84b; }}
a {{ color:#e8e2d0; text-decoration:none; }}
a:hover {{ color:#f0c860; text-decoration:underline; }}
div.s {{ color:#8b97a8; font-size:11px; padding-top:1px; }}
div.h {{ color:#e8b84b; font-size:13px; font-weight:bold; letter-spacing:1px;
         border-bottom:1px solid #33445c; padding-bottom:4px; margin-bottom:6px; }}
div.f {{ color:#5c6878; font-size:10px; padding-top:8px; }}
</style>
</head>
<body>
<div class="h">NEWS</div>
<table>
{rows}
</table>
<div class="f">{note} &middot; updated {stamp}</div>
</body>
</html>
""".format(rows="\n".join(rows), note=note, stamp=stamp)


def main():
    stamp = datetime.now().strftime("%b %d, %I:%M %p").replace(" 0", " ")
    try:
        page = fetch(SOURCE)
        items = parse(page)
        if not items:
            raise ValueError("no articles matched the expected markup")
        OUT.write_text(render(items, stamp), encoding="utf-8")
        print("wrote {} items to {}".format(len(items), OUT))
    except Exception as exc:
        # Leave any previously good page in place rather than blanking it.
        print("fetch failed: {}".format(exc), file=sys.stderr)
        if not OUT.exists():
            OUT.write_text(render([], stamp, ok=False), encoding="utf-8")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
