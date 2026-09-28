"""Normalized tables as each scorer's input (spec 12 section 3.2)."""

import re
from html import escape
from xml.sax.saxutils import quoteattr

from inkgrid_bench.tables import Box, NCell, NDocument, NPage, NTable

SORIC_HEIGHT = 1000.0  # their page images are this many pixels tall


def _header_rows(table: NTable) -> int:
    """How many leading rows hold only header cells."""
    rows = 0
    for r in range(table.n_rows):
        anchored = [c for c in table.cells if c.row == r]
        if anchored and all(c.header for c in anchored):
            rows += 1
        else:
            break
    return rows


def _cell_html(cell: NCell, tag: str) -> str:
    spans = ""
    if cell.rows > 1:
        spans += f' rowspan="{cell.rows}"'
    if cell.cols > 1:
        spans += f' colspan="{cell.cols}"'
    return f"<{tag}{spans}>{escape(cell.text, quote=False)}</{tag}>"


def table_html(table: NTable, *, header: bool) -> str:
    """The table as HTML, spans kept; with `header`, its header rows in `<thead>` as `<th>`."""
    head = _header_rows(table) if header else 0
    rows: list[list[NCell]] = [[] for _ in range(table.n_rows)]
    for cell in table.cells:
        rows[cell.row].append(cell)
    parts = ["<table>"]
    if head:
        parts.append("<thead>")
        parts += [
            "<tr>" + "".join(_cell_html(c, "th") for c in row) + "</tr>" for row in rows[:head]
        ]
        parts.append("</thead>")
    parts.append("<tbody>")
    parts += ["<tr>" + "".join(_cell_html(c, "td") for c in row) + "</tr>" for row in rows[head:]]
    parts.append("</tbody></table>")
    return "".join(parts)


# Characters XML 1.0 cannot carry: C0 controls but tab, newline and carriage return; surrogates;
# U+FFFE and U+FFFF. A tool's text can hold them (PyMuPDF returns U+0000 on practice us-008).
_NOT_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


def _xml_chars(text: str) -> str:
    """The text without the characters XML 1.0 forbids."""
    return _NOT_XML.sub("", text)


def _user_box(box: Box, page: NPage) -> tuple[int, int, int, int]:
    """A top-left-frame box in PDF user space, rounded outward to whole points."""
    x0, y1 = page.to_user(box[0], box[1])
    x1, y0 = page.to_user(box[2], box[3])
    return (int(x0 // 1), int(y0 // 1), -int(-x1 // 1), -int(-y1 // 1))


def _bbox_xml(box: tuple[int, int, int, int]) -> str:
    x0, y0, x1, y1 = box
    return f'<bounding-box x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}"/>'


def icdar_reg_xml(doc: NDocument, pdf_name: str) -> str:
    """The competition's region file: one region per table, in PDF user space."""
    parts = [f'<?xml version="1.0" encoding="UTF-8"?>\n<document filename={quoteattr(pdf_name)}>']
    for i, t in enumerate(doc.tables, start=1):
        box = _bbox_xml(_user_box(t.bbox, doc.pages[t.page - 1]))
        parts.append(f'<table id="{i}"><region id="1" page="{t.page}">{box}</region></table>')
    parts.append("</document>\n")
    return "\n".join(parts)


def icdar_str_xml(doc: NDocument, pdf_name: str) -> str:
    """The competition's structure file: every non-empty cell with its rows, columns and text."""
    parts = [f'<?xml version="1.0" encoding="UTF-8"?>\n<document filename={quoteattr(pdf_name)}>']
    for i, t in enumerate(doc.tables, start=1):
        parts.append(
            f'<table id="{i}"><region id="1" page="{t.page}" col-increment="0" row-increment="0">'
        )
        box = _bbox_xml(_user_box(t.bbox, doc.pages[t.page - 1]))
        for k, c in enumerate((c for c in t.cells if c.text.strip()), start=1):
            ends = ""
            if c.rows > 1 or c.cols > 1:
                ends = f' end-row="{c.row + c.rows - 1}" end-col="{c.col + c.cols - 1}"'
            parts.append(
                f'<cell id="{k}" start-row="{c.row}" start-col="{c.col}"{ends}>'
                f"{box}<content>{escape(_xml_chars(c.text), quote=False)}</content></cell>"
            )
        parts.append("</region></table>")
    parts.append("</document>\n")
    return "\n".join(parts)


def soric_box(box: Box, page: NPage) -> tuple[float, float, float, float]:
    """A top-left-frame box in Soric et al.'s page-image pixels, as their ground truth is built.

    Their image is SORIC_HEIGHT pixels tall as the page displays; a box's PDF user coordinates
    are scaled by that, x as it is and y from the displayed height (measured on eu-001 and on
    eu-015, whose pages are turned 90 degrees).
    """
    shown = page.height if page.rotation in (0, 180) else page.width
    scale = SORIC_HEIGHT / shown
    x0, y1 = page.to_user(box[0], box[1])
    x1, y0 = page.to_user(box[2], box[3])
    return (x0 * scale, (shown - y1) * scale, x1 * scale, (shown - y0) * scale)
