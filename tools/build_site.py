#!/usr/bin/env python3
"""Build the iQ-Studio GitHub Pages site.

Reads `site_map.yml` and converts each `source` README (Markdown) into a styled
HTML page under `site/<output>`. Hand-authored landing pages (the Overview and
the 6 category landings) are left untouched — they must exist in `site/` already.

Pipeline:
  1. Read README markdown.
  2. Preprocess GitHub callouts:  > [!NOTE] / [!TIP] / [!WARNING] / [!CAUTION] / [!IMPORTANT]
  3. Render to HTML with python-markdown (fenced_code, tables, toc).
  4. Post-process the HTML:
       - wrap <pre><code> blocks in the .codeblock shell (head bar + copy button)
       - rewrite intra-repo links/images to site paths
       - copy referenced fig/ images into site/<output_dir>/<slug>__fig/
       - mark external links target="_blank" rel="noopener"
       - add IDs to <h2>/<h3> (toc extension does this, but we ensure it)
  5. Wrap in the site chrome (topbar + sidebar + footer) lifted from site/index.html.

Run:
    python tools/build_site.py
"""

from __future__ import annotations

import html as html_lib
import re
import shutil
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "site"
SITE_MAP = REPO / "site_map.yml"
INDEX_HTML = SITE / "index.html"


# ---------------------------------------------------------------------------
# YAML loader — we ship without PyYAML at build-time if needed, but prefer it
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except ImportError:
        print("error: PyYAML is required. install with: pip install pyyaml", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

CALLOUT_KIND = {
    "NOTE": ("callout--note", "Note", "info"),
    "TIP": ("callout--tip", "Tip", "tip"),
    "WARNING": ("callout--warn", "Warning", "warn"),
    "CAUTION": ("callout--caution", "Caution", "warn"),
    "IMPORTANT": ("callout--important", "Important", "warn"),
}

ICON_INFO = (
    "<svg width=\"18\" height=\"18\" viewBox=\"0 0 24 24\" fill=\"none\" "
    "stroke=\"currentColor\" stroke-width=\"2\"><circle cx=\"12\" cy=\"12\" r=\"9\"/>"
    "<path d=\"M12 8v4\"/><circle cx=\"12\" cy=\"16\" r=\"0.5\" fill=\"currentColor\"/></svg>"
)
ICON_TIP = (
    "<svg width=\"18\" height=\"18\" viewBox=\"0 0 24 24\" fill=\"none\" "
    "stroke=\"currentColor\" stroke-width=\"2\"><path d=\"M9 18h6\"/>"
    "<path d=\"M10 22h4\"/><path d=\"M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.3 1 2.1V18h6v-1.2c0-.8.4-1.6 1-2.1A7 7 0 0 0 12 2Z\"/></svg>"
)
ICON_WARN = (
    "<svg width=\"18\" height=\"18\" viewBox=\"0 0 24 24\" fill=\"none\" "
    "stroke=\"currentColor\" stroke-width=\"2\"><path d=\"M12 3 1.5 21h21Z\"/>"
    "<path d=\"M12 10v5\"/><circle cx=\"12\" cy=\"18\" r=\"0.6\" fill=\"currentColor\"/></svg>"
)
ICON_BY_KIND = {"info": ICON_INFO, "tip": ICON_TIP, "warn": ICON_WARN}


def preprocess_callouts(md_text: str) -> str:
    """Convert callout syntax to raw HTML the markdown renderer will pass through.

    Recognizes two forms:

    1. GitHub-style:
       > [!NOTE]
       > body line 1

    2. Plain blockquote prefixed by a recognized label:
       > Note: body
       > Warning: body  /  Tip: body  /  Caution: body  /  Important: body

    Body lines that follow on `>`-prefixed lines are included until a blank line.
    """
    lines = md_text.splitlines()
    out: list[str] = []
    i = 0
    github_re = re.compile(r"^>\s*\[!(NOTE|TIP|WARNING|CAUTION|IMPORTANT)\]\s*$", re.IGNORECASE)
    # Match "> <optional emoji/symbols> [**]Label[:][**] body"
    # Handles all of:
    #   > Note: body
    #   > **Note:** body
    #   > 💡 **Tip:** body
    #   > **Note**: body
    plain_re = re.compile(
        r"^>\s*[^A-Za-z\n]{0,12}\s*\**\s*(Note|Tip|Warning|Caution|Important)\s*\**\s*[:：]\s*\**\s*(.*?)\**\s*$",
        re.IGNORECASE,
    )

    while i < len(lines):
        m_gh = github_re.match(lines[i])
        m_plain = plain_re.match(lines[i]) if not m_gh else None

        if not m_gh and not m_plain:
            out.append(lines[i])
            i += 1
            continue

        if m_gh:
            kind_token = m_gh.group(1).upper()
            first_body: list[str] = []
            i += 1
        else:
            label_token = m_plain.group(1).upper()
            # Map "WARNING"/"WARN" etc. to canonical
            kind_token = {"NOTE": "NOTE", "TIP": "TIP", "WARNING": "WARNING",
                          "CAUTION": "CAUTION", "IMPORTANT": "IMPORTANT"}.get(label_token, "NOTE")
            first_body = [m_plain.group(2)] if m_plain.group(2).strip() else []
            i += 1

        cls, label, icon_key = CALLOUT_KIND[kind_token]

        body: list[str] = list(first_body)
        while i < len(lines) and lines[i].startswith(">"):
            stripped = re.sub(r"^>\s?", "", lines[i])
            body.append(stripped)
            i += 1

        # Ensure a blank line precedes the raw block-level <div> so python-markdown
        # treats it as a top-level HTML block rather than wrapping it in a <p>.
        if out and out[-1].strip() != "":
            out.append("")
        out.append('<div class="callout {0}">'.format(cls))
        out.append('  <div class="callout__icon">{0}</div>'.format(ICON_BY_KIND[icon_key]))
        body_md = "\n".join(body).strip()
        rendered_body = _render_inline_md(body_md)
        out.append('  <div class="callout__body"><strong>{0}</strong>{1}</div>'.format(label, rendered_body))
        out.append('</div>')
        if i < len(lines) and lines[i].strip() == "":
            out.append("")
            i += 1
    return "\n".join(out)


def _render_inline_md(text: str) -> str:
    """Render a small Markdown snippet to HTML (used inside callout bodies)."""
    import markdown  # type: ignore
    return markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "sane_lists"],
        output_format="html5",
    )


def render_markdown(md_text: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Return (body_html, toc_entries). Each toc entry is (level, slug, text)."""
    import markdown  # type: ignore
    from markdown.treeprocessors import Treeprocessor  # type: ignore

    md_text = preprocess_callouts(md_text)
    # Strip the HTML license comment if it appears at the top of the README
    md_text = re.sub(r"^<!--.*?-->\s*", "", md_text, flags=re.DOTALL)

    md = markdown.Markdown(
        extensions=["fenced_code", "tables", "sane_lists", "toc"],
        extension_configs={
            "toc": {"toc_depth": "2-3", "anchorlink": False, "permalink": False},
        },
        output_format="html5",
    )
    html = md.convert(md_text)
    toc_tokens = getattr(md, "toc_tokens", [])
    toc_entries: list[tuple[int, str, str]] = []
    def walk(nodes: list[dict[str, Any]], level: int) -> None:
        for n in nodes:
            toc_entries.append((level, n["id"], n["name"]))
            if n.get("children"):
                walk(n["children"], level + 1)
    walk(toc_tokens, 2)
    return html, toc_entries


# ---------------------------------------------------------------------------
# HTML post-processing
# ---------------------------------------------------------------------------

CODEBLOCK_RE = re.compile(
    r'<pre><code(?P<attrs>[^>]*)>(?P<body>.*?)</code></pre>',
    re.DOTALL,
)


def wrap_codeblocks(html: str) -> str:
    """Wrap each <pre><code>…</code></pre> in the .codeblock shell with header + copy."""
    def repl(m: re.Match) -> str:
        attrs = m.group("attrs") or ""
        body = m.group("body")
        lang_match = re.search(r'class="(?:language-)?([^"\s]+)"', attrs)
        lang = lang_match.group(1) if lang_match else "text"
        return (
            '<div class="codeblock">'
            f'<div class="codeblock__head"><span>{html_lib.escape(lang)}</span>'
            '<button class="codeblock__copy" type="button">Copy</button></div>'
            f'<pre><code{attrs}>{body}</code></pre>'
            '</div>'
        )
    return CODEBLOCK_RE.sub(repl, html)


def wrap_tables(html: str) -> str:
    """Wrap each <table>…</table> in a .table-scroll container so wide tables
    scroll horizontally within their column instead of expanding the page."""
    return re.sub(
        r"(<table\b[\s\S]*?</table>)",
        r'<div class="table-scroll">\1</div>',
        html,
    )


def rewrite_links(html: str, source_md: Path, page_dir: Path, fig_slug: str, fig_files_copied: set[str]) -> str:
    """Rewrite relative href/src to site paths. Returns the new html."""
    # Map README→site for the canonical pages so cross-tutorial links work.
    site_for_readme = _build_readme_to_site_map()

    def resolve_md_link(target: str) -> str | None:
        """If target is a known intra-repo README path, return the site path. Else None."""
        # Normalize: drop leading ./, resolve relative to source_md.parent
        rel = (source_md.parent / target).resolve()
        try:
            rel_to_repo = rel.relative_to(REPO)
        except ValueError:
            return None
        return site_for_readme.get(str(rel_to_repo).replace("\\", "/"))

    def attr_repl(attr: str, val: str) -> str:
        if not val or val.startswith(("http://", "https://", "//", "mailto:", "#", "data:")):
            return f'{attr}="{val}"'
        # README link → mapped site page
        if val.endswith(".md") or "/README.md" in val:
            mapped = resolve_md_link(val)
            if mapped:
                # path from this page's dir to the target site path
                return f'{attr}="{_relpath(mapped, page_dir)}"'
            # README doesn't have a mapped page — link to GitHub source instead
            github = _github_url_for(val, source_md)
            return f'{attr}="{github}"'
        # Image / file from a sibling fig/ directory
        if attr == "src" or val.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
            local_path = (source_md.parent / val).resolve()
            try:
                rel_to_repo = local_path.relative_to(REPO)
            except ValueError:
                return f'{attr}="{val}"'
            # Copy into site/<page_dir>/<fig_slug>/<basename>
            dest_rel = f"{fig_slug}/{local_path.name}"
            dest = page_dir / dest_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest_rel not in fig_files_copied and local_path.exists():
                shutil.copy2(local_path, dest)
                fig_files_copied.add(dest_rel)
            return f'{attr}="{dest_rel}"'
        # Other relative link → GitHub source
        github = _github_url_for(val, source_md)
        return f'{attr}="{github}"'

    return re.sub(
        r'(href|src)="([^"]*)"',
        lambda m: attr_repl(m.group(1), m.group(2)),
        html,
    )


def _build_readme_to_site_map() -> dict[str, str]:
    """Map e.g. 'tutorials/applications/iqs-vlm/README.md' → 'applications/iqs-vlm.html'.
    Includes both the tutorial pages from site_map.yml AND the category READMEs whose
    HTML is hand-authored (so cross-references render correctly).
    """
    data = load_yaml(SITE_MAP)
    m: dict[str, str] = {}
    for page in data.get("pages", []):
        m[page["source"]] = page["output"]
    # Hand-authored category landings: map their underlying README → site landing.
    landings = {
        "tutorials/starting-guides/README.md": "starting-guides/index.html",
        "tutorials/applications/README.md": "applications/index.html",
        "tutorials/avl/README.md": "avl/index.html",
        "tutorials/model-deploy/README.md": "model-deploy/index.html",
        "tutorials/sdks/README.md": "sdks/index.html",
        "benchmarks/README.md": "benchmarks/index.html",
        "README.md": "index.html",
    }
    m.update(landings)
    return m


def _github_url_for(rel_target: str, source_md: Path) -> str:
    """Build a GitHub URL for a relative path that's NOT mapped to a site page."""
    abs_target = (source_md.parent / rel_target).resolve()
    try:
        rel_to_repo = abs_target.relative_to(REPO).as_posix()
    except ValueError:
        return rel_target
    return f"https://github.com/InnoIPA/iQ-Studio/blob/main/{rel_to_repo}"


def _relpath(target: str, page_dir: Path) -> str:
    """site-relative path → relative path from page_dir to target."""
    from os.path import relpath
    target_abs = SITE / target
    return relpath(target_abs, page_dir).replace("\\", "/")


def add_external_attrs(html: str) -> str:
    """Add target=_blank rel=noopener to absolute http(s) links that lack them."""
    def repl(m: re.Match) -> str:
        tag = m.group(0)
        if "target=" in tag:
            return tag
        return tag[:-1] + ' target="_blank" rel="noopener">'
    return re.sub(r'<a\s+[^>]*href="https?://[^"]+"[^>]*>', repl, html)


# ---------------------------------------------------------------------------
# Chrome assembly — extracts topbar/sidebar/footer from site/index.html
# ---------------------------------------------------------------------------

def extract_chrome() -> dict[str, str]:
    src = INDEX_HTML.read_text(encoding="utf-8")

    def block(start: str, end: str) -> str:
        s = src.index(start)
        e = src.index(end, s) + len(end)
        return src[s:e]

    topbar = block('<header class="topbar">', "</header>")
    notice = block('<div class="notice">', "</div>")
    sidebar = block('<aside class="sidebar"', "</aside>")
    footer = block('<footer class="footer">', "</footer>")
    # Clear is-active markers on Overview leaf + Documentation topbar link
    sidebar = sidebar.replace(
        'class="nav-leaf is-active" data-page="overview"',
        'class="nav-leaf" data-page="overview"',
    )
    topbar = topbar.replace('href="index.html" class="is-active"', 'href="index.html"')
    return {"topbar": topbar, "notice": notice, "sidebar": sidebar, "footer": footer}


def rewrite_chrome_paths(chrome_html: str, depth: int) -> str:
    """Rewrite href="X" / src="X" in chrome blocks for depth-N pages."""
    if depth == 0:
        return chrome_html
    prefix = "../" * depth

    def repl(m: re.Match) -> str:
        attr, val = m.group(1), m.group(2)
        if val.startswith(("http://", "https://", "//", "/", "#", "mailto:", "data:")):
            return m.group(0)
        return f'{attr}="{prefix}{val}"'

    return re.sub(r'(href|src)="([^"]+)"', repl, chrome_html)


PAGE_TEMPLATE = """<!DOCTYPE html>
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

    <nav class="crumbs">
      <a href="{root}index.html">Docs</a>
      <span class="sep">/</span>
      <a href="{category_url}">{category}</a>
      <span class="sep">/</span>
      <span class="current">{title}</span>
    </nav>

    <div class="page-title">
      <div class="page-title__eyebrow">{category} <span class="slash">/</span> {title}</div>
      <h1>{title}</h1>
      <div class="page-title__rule"></div>
    </div>

{body}

{pager}

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


def render_pager(order: list[dict], current_path: str) -> str:
    paths = [e["path"] for e in order]
    if current_path not in paths:
        return ""
    idx = paths.index(current_path)
    prev_entry = order[idx - 1] if idx > 0 else None
    next_entry = order[idx + 1] if idx + 1 < len(order) else None
    page_dir = (SITE / current_path).parent

    def link(entry: dict | None, direction: str) -> str:
        if not entry:
            return '<span class="pager__empty"></span>'
        rel = _relpath(entry["path"], page_dir)
        arrow_class = "pager__prev" if direction == "prev" else "pager__next"
        label = "← Previous" if direction == "prev" else "Next →"
        return (
            f'<a class="{arrow_class}" href="{rel}">'
            f'<span class="dir">{label}</span>'
            f'<span class="title">{html_lib.escape(entry["title"])}</span>'
            '</a>'
        )

    return (
        '<div class="pager">'
        + link(prev_entry, "prev")
        + link(next_entry, "next")
        + "</div>"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

LANDING_IMAGES = {
    # site asset path -> source path in repo
    "vlm-demo.gif":                 "tutorials/applications/iqs-vlm/fig/vlm-demo.gif",
    "mpipi.gif":                    "tutorials/avl/mipi-camera/fig/mpipi.gif",
    "octuple_demo.gif":             "tutorials/avl/gmsl-camera/fig/octuple_demo.gif",
    "avl-gmsl.png":                 "tutorials/avl/fig/avl-gmsl.png",
    "avl-mipi.png":                 "tutorials/avl/fig/avl-mipi.png",
    "avl-ep.png":                   "tutorials/avl/fig/avl-ep.png",
    "vlm-demo.png":                 "tutorials/applications/iqs-vlm/fig/vlm-demo.png",
    "ai_on_dragonwing_sw_stack.png":"docs/fig/ai_on_dragonwing_sw_stack.png",
    "sw_development_pipeline.png":  "docs/fig/sw_development_pipeline.png",
    "qcl_roadmap.png":              "docs/fig/qcl_roadmap.png",
    "iqs-struct.png":               "docs/fig/iqs-struct.png",
    "iqs-online-flow.svg":          "docs/fig/iqs-online-flow.svg",
    "iqs-offline-flow.svg":         "docs/fig/iqs-offline-flow.svg",
    "iq-studio-logo.png":           "docs/fig/iq-studio-logo.png",
}


def copy_landing_images() -> None:
    """Copy images referenced by the hand-authored landing pages from their source
    locations under tutorials/ and docs/ into site/assets/img/. Only landing-page
    assets land here; per-tutorial figures are placed into <slug>__fig/ during the
    main render pass.

    The non-GIF logos are small and already shipped checked-in (logo-innodisk.png),
    so this function is a no-op for those. Large GIFs are copied fresh each build
    and gitignored to keep the repo lean.
    """
    img_dir = SITE / "assets" / "img"
    img_dir.mkdir(parents=True, exist_ok=True)
    for asset_name, source_rel in LANDING_IMAGES.items():
        src = REPO / source_rel
        dst = img_dir / asset_name
        if not src.exists():
            print(f"  warning: landing image source missing: {source_rel}")
            continue
        if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
            continue  # already up-to-date
        shutil.copy2(src, dst)


def main() -> None:
    data = load_yaml(SITE_MAP)
    pages: list[dict] = data.get("pages", [])
    order: list[dict] = data.get("order", [])

    copy_landing_images()
    chrome = extract_chrome()

    n_ok = 0
    for page in pages:
        source_md = REPO / page["source"]
        if not source_md.exists():
            print(f"  skip {page['output']}: source missing ({source_md})")
            continue
        md_text = source_md.read_text(encoding="utf-8")
        body_html, _toc = render_markdown(md_text)

        out_path = SITE / page["output"]
        depth = len(Path(page["output"]).parent.parts)
        page_dir = out_path.parent
        page_dir.mkdir(parents=True, exist_ok=True)

        fig_slug = Path(page["output"]).stem + "__fig"
        fig_files_copied: set[str] = set()
        body_html = rewrite_links(body_html, source_md, page_dir, fig_slug, fig_files_copied)
        body_html = wrap_codeblocks(body_html)
        body_html = wrap_tables(body_html)
        body_html = add_external_attrs(body_html)
        body_html = _strip_first_h1(body_html)  # h1 lives in the page-title block

        chrome_dep = {k: rewrite_chrome_paths(v, depth) for k, v in chrome.items()}
        pager_html = render_pager(order, page["output"])
        root = "../" * depth

        html_out = PAGE_TEMPLATE.format(
            title=html_lib.escape(page["title"]),
            description=html_lib.escape(page["description"]),
            current=page["current"],
            category=html_lib.escape(page["category"]),
            category_url=page["category_url"],
            root=root,
            topbar=chrome_dep["topbar"],
            notice=chrome_dep["notice"],
            sidebar=chrome_dep["sidebar"],
            footer=chrome_dep["footer"],
            body=body_html,
            pager=pager_html,
        )
        out_path.write_text(html_out, encoding="utf-8")
        n_ok += 1
        print(f"  wrote {out_path.relative_to(REPO)} ({len(fig_files_copied)} figs copied)")

    print(f"\nbuild_site.py: {n_ok}/{len(pages)} pages written.")


def _strip_first_h1(html: str) -> str:
    """Remove the first <h1>…</h1> from rendered markdown — it's already in .page-title."""
    return re.sub(r"<h1[^>]*>.*?</h1>\s*", "", html, count=1, flags=re.DOTALL)


if __name__ == "__main__":
    main()
