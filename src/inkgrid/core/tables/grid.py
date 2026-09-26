"""A proto table as the parts of a `Table` block (docs/specs/06-ruled-tables.md section 6)."""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from inkgrid.core.lines import Line
from inkgrid.core.tables.proto import ProtoTable
from inkgrid.core.text import WordPair, block_text
from inkgrid.model.document import Cell, Grid, Region
from inkgrid.model.geometry import Interval, Rect, unturn_rect
from inkgrid.model.page import PageInfo, Word


@dataclass(frozen=True, slots=True)
class TableParts:
    """What a `Table` block is made of, before its id and key exist."""

    words: tuple[Word, ...]
    text: str
    joins: tuple[WordPair, ...]
    grid: Grid
    region: Region


def _own(lines: Sequence[Line], words: Sequence[Word]) -> tuple[Word, ...]:
    """The lines' words as the reading has them (layout may have turned them)."""
    return tuple(words[w.id] for line in lines for w in line.words)


def table_parts(table: ProtoTable, words: Sequence[Word], page: PageInfo) -> TableParts:
    """The grid, text, joins, and region of a proto table; `words` are the document's, by id."""
    cells: list[Cell] = []
    texts: dict[int, list[str]] = {}
    joins: list[WordPair] = []
    own: list[Word] = []
    for proto in table.cells:
        shape = proto.cell
        text, cell_joins = block_text(proto.lines) if proto.lines else ("", ())
        mine = _own(proto.lines, words)
        cells.append(
            Cell(
                row=shape.row,
                col=shape.col,
                row_span=shape.row_span,
                col_span=shape.col_span,
                text=text,
                word_ids=tuple(w.id for w in mine),
                markers=tuple(w.text for w in mine if w.superscript),
            )
        )
        if text:
            texts.setdefault(shape.row, []).append(text)
        joins.extend(cell_joins)
        own.extend(mine)
    rows, cols = table.shape.row_edges, table.shape.col_edges
    grid = Grid(
        n_rows=len(rows) - 1,
        n_cols=len(cols) - 1,
        row_bands=tuple(Interval(a, b) for a, b in pairwise(rows)),
        col_bands=tuple(Interval(a, b) for a, b in pairwise(cols)),
        header_rows=table.header_rows,
        banner_rows=table.banner_rows,
        source=table.source,
        frame=table.frame,
        cells=tuple(cells),
    )
    outline = unturn_rect(table.bbox, table.frame, page.width, page.height)
    region = Region(page=page.number, bbox=Rect.union_all([outline, *(w.bbox for w in own)]))
    text = "\n".join(" ".join(parts) for _, parts in sorted(texts.items()))
    return TableParts(tuple(own), text, tuple(joins), grid, region)
