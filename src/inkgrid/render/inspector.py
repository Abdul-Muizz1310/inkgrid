"""The HTML inspector: each page's image with its blocks drawn over it (docs/specs/05 section 4).

It is for looking, not for gates. The page is static: inline CSS, no scripts, no external requests,
and every document string is HTML-escaped.
"""

import base64
from collections.abc import Sequence
from html import escape

from inkgrid.model.canonical import sha256_hex
from inkgrid.model.document import Block, Document, Table
from inkgrid.model.findings import Finding
from inkgrid.model.geometry import unturn_rect
from inkgrid.model.page import PageInfo
from inkgrid.read.pymupdf_reader import render_pages
from inkgrid.read.source import SourceLike, load_source

DPI = 100
STYLE = """
:root { --bg: #ffffff; --fg: #1d2129; --muted: #5d6573; --card: #f4f5f7; --line: #d5d9e0;
  --heading: #7b3fe4; --paragraph: #1f6feb; --list_item: #1a7f37; --footnote: #bf8700;
  --definition: #0a7ea4; --table: #cf222e; --furniture: #8c959f; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #111418; --fg: #e6e8eb; --muted: #9aa3ad; --card: #1b2027; --line: #2f3742; }
}
* { box-sizing: border-box; }
body { margin: 0; padding: 16px; background: var(--bg); color: var(--fg);
  font: 14px/1.45 system-ui, sans-serif; }
h1 { font-size: 18px; margin: 0 0 4px; }
h2 { font-size: 16px; margin: 24px 0 8px; }
.meta, .muted { color: var(--muted); }
.page { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 16px;
  border-top: 1px solid var(--line); padding-top: 8px; }
.page > h2 { grid-column: 1 / -1; }
svg { width: 100%; height: auto; background: #fff; border: 1px solid var(--line); }
rect { fill: none; stroke-width: 1.2; }
rect.cell { stroke: var(--table); stroke-width: 0.4; stroke-dasharray: 2 1; }
text { font: 9px sans-serif; }
.card { background: var(--card); border-left: 4px solid var(--line); padding: 6px 10px;
  margin: 0 0 8px; overflow-wrap: anywhere; }
.card b { font-weight: 600; }
.findings { margin: 0 0 12px; padding-left: 18px; }
.error { color: #cf222e; } .warning { color: #bf8700; }
@media (max-width: 720px) { .page { grid-template-columns: 1fr; } }
@media print { body { padding: 0; } .page { break-inside: avoid; } }
"""
KINDS = ("heading", "paragraph", "list_item", "footnote", "definition", "table", "furniture")
STYLE += "".join(
    f".k-{k} {{ stroke: var(--{k}); fill: var(--{k}); }}"
    f" .c-{k} {{ border-left-color: var(--{k}); }}"
    for k in KINDS
)


def _findings(findings: Sequence[Finding]) -> str:
    if not findings:
        return ""
    items = "".join(
        f'<li class="{f.severity.value}"><b>{escape(f.code.value)}</b> {escape(f.detail)}</li>'
        for f in findings
    )
    return f'<ul class="findings">{items}</ul>'


def _kind_detail(block: Block) -> str:
    match block.kind:
        case "heading":
            return f"level {block.level}"
        case "list_item" | "footnote":
            return f"label {escape(block.label)}"
        case "definition":
            return f"term {escape(block.term)}"
        case "furniture":
            return block.role
        case "paragraph" | "table":
            return ""


def _card(number: int, block: Block) -> str:
    detail = _kind_detail(block)
    markers = f' <span class="muted">markers {escape(" ".join(block.markers))}</span>'
    head = f"<b>{number}. {escape(block.id)}</b> {block.kind}" + (f" ({detail})" if detail else "")
    return (
        f'<div class="card c-{block.kind}">{head}{markers if block.markers else ""}'
        f"<div>{escape(block.text)}</div></div>"
    )


def _sheet(page: PageInfo, png: bytes | None, boxes: str) -> str:
    if png is None:
        return '<p class="muted">This page could not be rendered.</p>'
    data = base64.b64encode(png).decode("ascii")
    return (
        f'<svg viewBox="0 0 {page.width} {page.height}" role="img" '
        f'aria-label="page {page.number}">'
        f'<image href="data:image/png;base64,{data}" width="{page.width}" '
        f'height="{page.height}"/>{boxes}</svg>'
    )


def _cells(table: Table, page: PageInfo) -> str:
    """Each cell of a table as a thin rectangle, back in unrotated page coordinates."""
    out = []
    for cell in table.grid.cells:
        box = unturn_rect(table.grid.cell_rect(cell), table.grid.frame, page.width, page.height)
        out.append(
            f'<rect class="cell" x="{box.x0}" y="{box.y0}" width="{box.x1 - box.x0}" '
            f'height="{box.y1 - box.y0}"/>'
        )
    return "".join(out)


def _page(doc: Document, page: PageInfo, png: bytes | None) -> str:
    boxes: list[str] = []
    cards: list[str] = []
    for number, block in enumerate(doc.blocks, 1):
        for region in block.regions:
            if region.page != page.number:
                continue
            box = region.bbox
            boxes.append(
                f'<rect class="k-{block.kind}" x="{box.x0}" y="{box.y0}" '
                f'width="{box.x1 - box.x0}" height="{box.y1 - box.y0}" fill-opacity="0.08"/>'
                f'<text class="k-{block.kind}" x="{box.x0}" y="{box.y0 - 1}">{number}</text>'
            )
            if isinstance(block, Table):
                boxes.append(_cells(block, page))
            cards.append(_card(number, block))
    findings = [f for f in doc.findings if f.page == page.number]
    return (
        f'<section class="page" id="page-{page.number}"><h2>Page {page.number}</h2>'
        f"<div>{_sheet(page, png, ''.join(boxes))}</div>"
        f"<div>{_findings(findings)}{''.join(cards)}</div></section>"
    )


def inspector_html(doc: Document, pages_png: Sequence[bytes | None]) -> str:
    """A self-contained HTML page for the document, given one rendered image per page."""
    if len(pages_png) != len(doc.pages):
        msg = f"the document has {len(doc.pages)} pages but {len(pages_png)} page images were given"
        raise ValueError(msg)
    name = doc.source.file_name or "PDF"
    title = f"inkgrid inspector: {name}"
    header = (
        f"<h1>{escape(title)}</h1>"
        f'<p class="meta">{len(doc.pages)} pages, {len(doc.blocks)} blocks, sha256 '
        f"{doc.source.sha256[:16]}&hellip;</p>"
        f"{_findings([f for f in doc.findings if f.page is None])}"
    )
    pages = "".join(_page(doc, page, png) for page, png in zip(doc.pages, pages_png, strict=True))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title><style>{STYLE}</style></head>"
        f"<body>{header}{pages}</body></html>\n"
    )


def build_inspector(doc: Document, source: SourceLike, password: str | None = None) -> str:
    """Render the document's own PDF and build the inspector page.

    Raises:
        ValueError: `source` is not the PDF the document was read from.
    """
    loaded = load_source(source)
    digest = sha256_hex(loaded.data)
    if digest != doc.source.sha256:
        msg = (
            f"the PDF's SHA-256 {digest[:16]}... differs from the document's "
            f"{doc.source.sha256[:16]}...; boxes would be drawn over the wrong pages"
        )
        raise ValueError(msg)
    return inspector_html(doc, render_pages(loaded.data, password, DPI))
