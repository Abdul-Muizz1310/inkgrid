"""Tables and paragraphs that continue across a page (spec 09, sections 4 and 5).

Continuation is strict (L12): the parent is the last block of its page and the child the first
of the next, counting neither furniture nor footnotes; the columns agree; and the child prints no
header of its own (it carries the parent's) or reprints the parent's. Joins never move a word
between two blocks: a carried header cell owns no words.
"""

import statistics
from collections.abc import Sequence
from dataclasses import replace
from itertools import pairwise

from inkgrid.core.order import reading_order
from inkgrid.core.prose import ProtoBlock
from inkgrid.core.tables.proto import ProtoCell, ProtoTable
from inkgrid.core.tables.shape import GridShape, ShapeCell
from inkgrid.core.text import block_text
from inkgrid.model.geometry import Rect

EDGE_TOL_EM = 0.5  # column edges agree within this share of the tables' median word size (L10)
MIN_BAND = 0.05  # pt: a carried header band never has zero height
TERMINAL = (".", ":", ";", "?", "!")  # a sentence that ends in one does not run on


def _flow(
    blocks: Sequence[ProtoBlock], tables: Sequence[ProtoTable]
) -> list[ProtoBlock | ProtoTable]:
    """A page's content in reading order, without its footnotes (they belong to no flow)."""
    return [
        item
        for item in reading_order(blocks, tables)
        if not (isinstance(item, ProtoBlock) and item.kind == "footnote")
    ]


def _cell_text(cell: ProtoCell) -> str:
    return cell.carried or (block_text(cell.lines)[0] if cell.lines else "")


def _header_texts(table: ProtoTable) -> list[str]:
    rows: list[list[str]] = [[] for _ in range(table.header_rows)]
    for cell in sorted(table.cells, key=lambda c: (c.cell.row, c.cell.col)):
        text = _cell_text(cell)
        if cell.cell.row < table.header_rows and text:
            rows[cell.cell.row].append(text)
    return [" ".join(" ".join(row).split()) for row in rows]


def _aligned(parent: ProtoTable, child: ProtoTable) -> bool:
    """Same frame and column count, every column edge within half the median word size."""
    a, b = parent.shape.col_edges, child.shape.col_edges
    if parent.frame != child.frame or len(a) != len(b):
        return False
    sizes = [w.size for w in (*parent.words, *child.words)]
    tol = EDGE_TOL_EM * statistics.median(sizes) if sizes else 0.0
    return all(abs(x - y) <= tol for x, y in zip(a, b, strict=True))


def _ceiling(child: ProtoTable, blocks: Sequence[ProtoBlock]) -> float:
    """The bottom of the lowest block ending above the child on its page, or the page top."""
    top = child.bbox.y0
    bottoms = [max(line.bottom for line in b.lines) for b in blocks]
    return max((b for b in bottoms if b <= top), default=0.0)


def _carry(parent: ProtoTable, child: ProtoTable, ceiling: float) -> ProtoTable:
    """The child with the parent's header rows on top: carried cells, and empty cells for blanks."""
    k = parent.header_rows
    edges = parent.shape.row_edges
    heights = [b - a for a, b in pairwise(edges[: k + 1])]
    top = child.shape.row_edges[0]
    room = top - ceiling
    scale = min(1.0, room / sum(heights)) if room > 0 else 0.0
    bands = [max(h * scale, MIN_BAND) for h in heights]
    start = top - sum(bands)
    new_rows = [start]
    for band in bands:
        new_rows.append(new_rows[-1] + band)
    new_rows[-1] = top  # no rounding drift at the child's own first edge
    row_edges = (*new_rows, *child.shape.row_edges[1:])
    cols = child.shape.col_edges

    def rect(row: int, col: int, row_span: int, col_span: int) -> Rect:
        return Rect(cols[col], row_edges[row], cols[col + col_span], row_edges[row + row_span])

    header: list[ProtoCell] = []
    for cell in parent.cells:
        c = cell.cell
        if c.row >= k:
            continue
        span = min(c.row_span, k - c.row)  # an empty cell may reach into the parent's body
        place = ShapeCell(c.row, c.col, span, c.col_span, rect(c.row, c.col, span, c.col_span))
        text = _cell_text(cell)
        if text:
            header.append(ProtoCell(place, (), carried=text, source=((c.row, c.col),)))
        else:
            header.append(ProtoCell(place, ()))
    body = [
        replace(
            cell,
            cell=replace(
                cell.cell,
                row=cell.cell.row + k,
                rect=rect(cell.cell.row + k, cell.cell.col, cell.cell.row_span, cell.cell.col_span),
            ),
        )
        for cell in child.cells
    ]
    cells = tuple(sorted((*header, *body), key=lambda c: (c.cell.row, c.cell.col)))
    shape = GridShape(row_edges, cols, tuple(c.cell for c in cells))
    banners = (*(b for b in parent.banner_rows if b < k), *(b + k for b in child.banner_rows))
    return replace(
        child, shape=shape, cells=cells, header_rows=k, banner_rows=banners, continues=parent
    )


def join_tables(
    pages: Sequence[Sequence[ProtoBlock]], tables: Sequence[Sequence[ProtoTable]]
) -> list[tuple[ProtoTable, ...]]:
    """Each page's tables, a child of a continuation carrying or linking its parent (s. 4)."""
    out = [list(page) for page in tables]
    for p in range(len(out) - 1):
        last = _flow(pages[p], out[p])
        first = _flow(pages[p + 1], out[p + 1])
        if not last or not first:
            continue
        parent, child = last[-1], first[0]
        if not isinstance(parent, ProtoTable) or not isinstance(child, ProtoTable):
            continue
        if not _aligned(parent, child):
            continue
        if child.header_rows == 0 and parent.header_rows == 0:
            joined = replace(child, continues=parent)  # neither prints a header: nothing to carry
        elif child.header_rows == 0:
            joined = _carry(parent, child, _ceiling(child, pages[p + 1]))
        elif _header_texts(child) == _header_texts(parent):
            joined = replace(child, continues=parent)  # the document reprints the header
        else:
            continue
        out[p + 1] = [joined if t is child else t for t in out[p + 1]]
    return [tuple(page) for page in out]


def _continues(parent: ProtoBlock, child: ProtoBlock) -> bool:
    """A sentence broken by the page: no terminal punctuation, then a lower-case opening."""
    last = parent.lines[-1].words[-1].text
    first = child.lines[0].words[0].text
    return not last.endswith(TERMINAL) and first[:1].islower()


def join_paragraphs(
    pages: Sequence[Sequence[ProtoBlock]], tables: Sequence[Sequence[ProtoTable]]
) -> list[tuple[ProtoBlock, ...]]:
    """Each page's blocks, a paragraph broken by the page joined into the first part (s. 5).

    The joined block keeps the first part's place; a page the paragraph fills keeps the chain going.
    """
    out = [list(page) for page in pages]
    tail: tuple[int, int] | None = None  # (page, index) of the paragraph the flow last ended on
    for p, page_tables in enumerate(tables):
        flow = _flow(out[p], page_tables)
        if tail is not None and flow:
            first = flow[0]
            parent = out[tail[0]][tail[1]]
            if (
                isinstance(first, ProtoBlock)
                and first.kind == "paragraph"
                and _continues(parent, first)
            ):
                out[tail[0]][tail[1]] = replace(parent, lines=(*parent.lines, *first.lines))
                out[p] = [b for b in out[p] if b is not first]
                flow = flow[1:]
                if not flow:
                    continue  # the page only continued the paragraph: the chain goes on
        last = flow[-1] if flow else None
        if isinstance(last, ProtoBlock) and last.kind == "paragraph":
            tail = (p, next(i for i, b in enumerate(out[p]) if b is last))
        else:
            tail = None
    return [tuple(page) for page in out]
