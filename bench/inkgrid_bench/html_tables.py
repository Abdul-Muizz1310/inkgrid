"""HTML tables as normalized cells (docs/specs/15-heavy-competitors.md section 2.1), pure.

marker and unstructured hand their tables over as HTML. The first `<table>` is read row by row;
each cell takes the first free column of its row and spans its `rowspan` x `colspan`, clipped to
the table's rows and stopped before any position an earlier cell holds, so the cells never
overlap. A nested table's text belongs to the cell around it.
"""

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

from inkgrid_bench.tables import NCell

_SPACE = re.compile(r"\s+")
_BREAKS = frozenset({"br", "p", "div", "li"})  # tags that separate a cell's words


def _span(value: str | None) -> int:
    """A `rowspan` or `colspan`: missing, non-numeric, or below 1 means 1."""
    try:
        span = int(value or "")
    except ValueError:
        return 1
    return max(span, 1)


@dataclass(slots=True)
class _Cell:
    header: bool
    rows: int
    cols: int
    text: list[str] = field(default_factory=list)


class _Parser(HTMLParser):
    """The first table's rows of cells, nested tables folded into their cell's text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[_Cell]] = []
        self.cell: _Cell | None = None
        self.depth = 0
        self.done = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.done:
            return
        if tag == "table":
            self.depth += 1
        elif self.depth == 1 and tag == "tr":
            self.rows.append([])
            self.cell = None
        elif self.depth == 1 and tag in {"td", "th"}:
            if not self.rows:
                self.rows.append([])
            values = dict(attrs)
            self.cell = _Cell(
                tag == "th", _span(values.get("rowspan")), _span(values.get("colspan"))
            )
            self.rows[-1].append(self.cell)
        elif tag in _BREAKS and self.cell is not None:
            self.cell.text.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if self.done:
            return
        if tag == "table":
            self.depth -= 1
            self.done = self.depth == 0
        elif self.depth == 1 and tag in {"td", "th", "tr"}:
            self.cell = None
        elif tag in _BREAKS and self.cell is not None:
            self.cell.text.append(" ")

    def handle_data(self, data: str) -> None:
        if self.cell is not None and not self.done:
            self.cell.text.append(data)


def cells_from_html(html: str) -> list[NCell]:
    """The first table's cells, in row order; none when it has no cell."""
    parser = _Parser()
    parser.feed(html)
    parser.close()
    rows = parser.rows
    taken: set[tuple[int, int]] = set()
    out: list[NCell] = []
    for r, row in enumerate(rows):
        col = 0
        for cell in row:
            while (r, col) in taken:
                col += 1
            height = min(cell.rows, len(rows) - r)
            width = 1
            while width < cell.cols and not any(
                (r + dr, col + width) in taken for dr in range(height)
            ):
                width += 1
            text = _SPACE.sub(" ", "".join(cell.text)).strip()
            out.append(NCell(r, col, height, width, text, header=cell.header))
            taken |= {(r + dr, col + dc) for dr in range(height) for dc in range(width)}
            col += width
    return out
