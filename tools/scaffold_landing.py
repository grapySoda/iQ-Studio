#!/usr/bin/env python3
"""One-time helper: assemble the 6 category landing pages from a shared chrome
(topbar + sidebar + footer extracted from site/index.html) plus a per-page main
fragment. The output is committed as static HTML; this script is not run by CI.

Usage:
    python tools/scaffold_landing.py

It reads:
    tools/landings/<slug>.html       (the <main> body fragment for each landing)
    tools/landings/_meta.json        (page metadata: title, description, current, depth)

And writes:
    site/<slug>/index.html
"""

from __future__ import annotations
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "site"

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} · iQ-Studio</title>
<meta name="description" content="{description}">
<link rel="stylesheet" href="{root}assets/css/styles.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='4' fill='%23EC1B23'/><path d='M9 9h3v14H9zm6 0h3v14h-3zm6 0h3v14h-3z' fill='white'/></svg>">
</head>
<body data-current="{current}">

{topbar}

{notice}

<div class="layout">

{sidebar}

  <main class="main">
{content}
  </main>

  <aside class="toc">
    <div class="toc__head">On this page</div>
    <ul id="toc-list"></ul>
  </aside>

</div>

{footer}

<script src="{root}assets/js/site.js" defer></script>
</body>
</html>
"""


def extract_block(html: str, start_marker: str, end_marker: str) -> str:
    """Extract a substring from `start_marker` (inclusive) up to `end_marker` (inclusive)."""
    start = html.index(start_marker)
    end = html.index(end_marker, start) + len(end_marker)
    return html[start:end]


def rewrite_for_depth(html: str, depth: int) -> str:
    """Source uses depth-0 paths (e.g. href='assets/...'). Rewrite to depth-1 (../assets)."""
    if depth == 0:
        return html
    prefix = "../" * depth
    # Rewrite href="X" and src="X" where X doesn't start with http, /, #, mailto:, data:
    def repl(m: re.Match) -> str:
        attr, val = m.group(1), m.group(2)
        if val.startswith(("http://", "https://", "//", "/", "#", "mailto:", "data:")):
            return m.group(0)
        return f'{attr}="{prefix}{val}"'

    return re.sub(r'(href|src)="([^"]+)"', repl, html)


def main() -> None:
    src = (SITE / "index.html").read_text(encoding="utf-8")
    topbar = extract_block(src, "<header class=\"topbar\">", "</header>")
    notice = extract_block(src, "<div class=\"notice\">", "</div>")  # closes at first </div>
    sidebar = extract_block(src, "<aside class=\"sidebar\"", "</aside>")
    footer = extract_block(src, "<footer class=\"footer\">", "</footer>")

    meta = json.loads((REPO / "tools" / "landings" / "_meta.json").read_text())

    for slug, page in meta.items():
        depth = page["depth"]
        root = "../" * depth
        fragment_path = REPO / "tools" / "landings" / f"{slug}.html"
        if not fragment_path.exists():
            print(f"  skip {slug}: missing fragment {fragment_path}")
            continue
        content = fragment_path.read_text(encoding="utf-8")

        # Strip the is-active class from the Overview leaf, since we're not on Overview.
        sidebar_for_page = sidebar.replace(
            'class="nav-leaf is-active" data-page="overview"',
            'class="nav-leaf" data-page="overview"',
        )

        # Topbar: clear is-active class on Documentation link (only Overview keeps it).
        topbar_for_page = topbar.replace(
            'href="index.html" class="is-active"',
            'href="index.html"',
        )

        # Rewrite relative paths in the chrome blocks for the depth of this page.
        chrome = {
            "topbar": rewrite_for_depth(topbar_for_page, depth),
            "notice": rewrite_for_depth(notice, depth),
            "sidebar": rewrite_for_depth(sidebar_for_page, depth),
            "footer": rewrite_for_depth(footer, depth),
        }

        out = TEMPLATE.format(
            title=page["title"],
            description=page["description"],
            root=root,
            current=page["current"],
            content=content,
            **chrome,
        )

        out_path = SITE / page["output"]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out, encoding="utf-8")
        print(f"  wrote {out_path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
