"""Pure Markdown formatting of block text (docs/specs/05-read-and-inspector.md section 2).

This module imports nothing from `document.py`, so `Document.to_markdown()` adds no import cycle:
the document dispatches over its block kinds and calls these formatters.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from html import escape

MAX_HEADING_LEVEL = 6
STRUCTURE_OPENERS = ("#", ">", "-", "+", "*")
ORDINAL = re.compile(r"\d+(?=[.)])")
TAG_OPEN = re.compile(r"<(?=[A-Za-z/!?])")


def _tags(text: str) -> str:
    """A `<` that would open an HTML tag, escaped: printed text never becomes markup."""
    return TAG_OPEN.sub(r"\\<", text)


def _opening(text: str) -> str:
    """The text with a leading block marker escaped, so it is not read as structure."""
    if text.startswith(STRUCTURE_OPENERS):
        return "\\" + text
    ordinal = ORDINAL.match(text)
    if ordinal is not None:
        return text[: ordinal.end()] + "\\" + text[ordinal.end() :]
    return text


def heading(level: int, text: str) -> str:
    """`#` x min(level, 6), a space, then the text."""
    return "#" * min(level, MAX_HEADING_LEVEL) + " " + _tags(text)


def paragraph(text: str) -> str:
    """The text, escaped so Markdown never reads printed text as structure."""
    return _opening(_tags(text))


def _after_first_word(text: str) -> str:
    return text.partition(" ")[2]


def list_item(text: str, *, bullet: bool) -> str:
    """A bullet item as `- ` and its text; an enumerated item as printed."""
    if not bullet:
        return _tags(text)
    rest = _opening(_tags(_after_first_word(text)))
    return f"- {rest}" if rest else "-"


def footnote(label: str, text: str) -> str:
    """`[^label]:`, then the note's text without its printed label."""
    rest = _opening(_tags(_after_first_word(text)))
    return f"[^{label}]: {rest}" if rest else f"[^{label}]:"


def definition(term: str, body: str) -> str:
    """The term in bold, then the body."""
    return f"**{_tags(term)}** {_tags(body)}"


@dataclass(frozen=True, slots=True)
class GridCell:
    """A cell as the exporters need it: where it starts, what it spans, and its text."""

    row: int
    col: int
    row_span: int
    col_span: int
    text: str


@dataclass(frozen=True, slots=True)
class DenseCell:
    """One grid position of a dense row. `copy` marks a merged cell's text repeated here (L1)."""

    text: str
    row: int
    col: int
    copy: bool


def _positions(n_rows: int, n_cols: int, cells: Sequence[GridCell]) -> list[list[DenseCell]]:
    grid = [[DenseCell("", r, c, copy=False) for c in range(n_cols)] for r in range(n_rows)]
    for cell in cells:
        for r in range(cell.row, cell.row + cell.row_span):
            for c in range(cell.col, cell.col + cell.col_span):
                grid[r][c] = DenseCell(cell.text, r, c, copy=(r, c) != (cell.row, cell.col))
    return grid


def dense_rows(
    n_rows: int, n_cols: int, cells: Sequence[GridCell]
) -> tuple[tuple[DenseCell, ...], ...]:
    """Every grid position filled; a merged cell's text repeats with `copy=True` (L1)."""
    return tuple(tuple(row) for row in _positions(n_rows, n_cols, cells))


def _gfm(text: str) -> str:
    return _tags(text).replace("|", "\\|")


def table_markdown(n_rows: int, n_cols: int, header_rows: int, cells: Sequence[GridCell]) -> str:
    """A GFM pipe table; a merged cell's text appears once and the positions it covers are empty."""
    rows = [
        [_gfm(c.text) if not c.copy else "" for c in row]
        for row in _positions(n_rows, n_cols, cells)
    ]
    header = rows[0] if header_rows else [""] * n_cols
    body = rows[1:] if header_rows else rows
    lines = [header, ["---"] * n_cols, *body]
    return "\n".join("| " + " | ".join(line) + " |" for line in lines)


def table_html(
    n_rows: int,
    header_rows: int,
    banner_rows: Sequence[int],
    cells: Sequence[GridCell],
) -> str:
    """A `<table>`: header rows in `<thead>`, spans as `colspan`/`rowspan`, all text escaped."""
    parts = ["<table>"]
    for r in range(n_rows):
        if r == 0 and header_rows:
            parts.append("<thead>")
        if r == header_rows:
            parts.append("<tbody>")
        tag = "th" if r < header_rows else "td"
        parts.append('<tr class="banner">' if r in banner_rows else "<tr>")
        for cell in (c for c in cells if c.row == r):
            spans = (f' colspan="{cell.col_span}"' if cell.col_span > 1 else "") + (
                f' rowspan="{cell.row_span}"' if cell.row_span > 1 else ""
            )
            parts.append(f"<{tag}{spans}>{escape(cell.text, quote=False)}</{tag}>")
        parts.append("</tr>")
        if r == header_rows - 1:
            parts.append("</thead>")
    if header_rows < n_rows:
        parts.append("</tbody>")
    parts.append("</table>")
    return "".join(parts)


def join(parts: Iterable[str]) -> str:
    """Blocks separated by one blank line, ending with one newline; nothing renders as `""`."""
    blocks = list(parts)
    return "\n\n".join(blocks) + "\n" if blocks else ""
