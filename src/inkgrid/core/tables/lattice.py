"""Ruled grids to proto tables (docs/specs/06-ruled-tables.md section 5).

A word belongs to the cell whose half-open rectangle holds its centre, so assignment is a partition
by construction. A grid is a table only when it has two rows, two columns, and two cells with words:
a box around a paragraph or a furniture label is not a table.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from inkgrid.core.tables.proto import ProtoCell, ProtoTable, cell_lines, table_roles
from inkgrid.core.tables.shape import grid_shape
from inkgrid.model.config import Profile
from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.geometry import Rect, Rotation
from inkgrid.model.page import PageModel, Word

MIN_ROWS = MIN_COLS = MIN_FILLED = 2
CROSS_TOLERANCE = 1.0  # pt a word may overhang its cell's left or right edge


@dataclass(frozen=True, slots=True)
class TableStage:
    """What the table stage made of one page: tables, the words they claim, and findings."""

    tables: tuple[ProtoTable, ...]
    claimed: frozenset[int]
    findings: tuple[Finding, ...]


def _ruled_layout(cells: Sequence[ProtoCell], n_cols: int, profile: Profile) -> bool:
    """True when every column is running text: a frame ruled around columns of prose, not a table.

    A column is running text when its single-column cells hold prose by layout's test and one of
    them holds a column's worth of lines (twice `column_min_lines`). Table cells of text are short.
    """
    for col in range(n_cols):
        own = [c for c in cells if c.cell.col == col and c.cell.col_span == 1]
        lines = [line for c in own for line in c.lines]
        if len(lines) < profile.column_min_lines:
            return False
        if sum(len(line.words) for line in lines) / len(lines) < profile.prose_min_words:
            return False
        if max(len(c.lines) for c in own) < 2 * profile.column_min_lines:
            return False
    return True


def _crossing(cells: Sequence[ProtoCell], bbox: Rect) -> int:
    """Words overhanging their cell's left or right edge into a neighbouring cell."""
    count = 0
    for cell in cells:
        rect = cell.cell.rect
        for word in cell.words:
            left = rect.x0 > bbox.x0 and word.bbox.x0 < rect.x0 - CROSS_TOLERANCE
            right = rect.x1 < bbox.x1 and word.bbox.x1 > rect.x1 + CROSS_TOLERANCE
            count += left or right
    return count


def lattice_tables(
    page: PageModel,
    grids: Sequence[Sequence[Rect]],
    words: Sequence[Word],
    profile: Profile,
    *,
    frame: Rotation,
    read: bool,
) -> TableStage:
    """The page's ruled grids as proto tables, over its content words (all in one frame).

    `read` says whether the lattice reader read this page.
    """
    tables: list[ProtoTable] = []
    claimed: set[int] = set()
    findings: list[Finding] = []
    if read and not grids:
        detail = "the page has rules both ways, but Camelot returned no grid"
        findings.append(Finding.of(FindingCode.LATTICE_DISAGREES, detail, page=page.number))
    for rects in grids:
        shape = grid_shape(rects)
        if shape is None:
            detail = "a lattice grid whose cells do not tile it was dropped"
            findings.append(Finding.of(FindingCode.LATTICE_FAILED, detail, page=page.number))
            continue
        cells = [
            ProtoCell(
                cell,
                cell_lines(
                    [
                        w
                        for w in words
                        if w.id not in claimed and cell.rect.contains_point(*w.bbox.center)
                    ],
                    profile,
                ),
            )
            for cell in shape.cells
        ]
        n_rows, n_cols = len(shape.row_edges) - 1, len(shape.col_edges) - 1
        if n_rows < MIN_ROWS or n_cols < MIN_COLS or sum(1 for c in cells if c.words) < MIN_FILLED:
            continue
        if _ruled_layout(cells, n_cols, profile):
            continue
        header, banners, text_only = table_roles(cells, n_rows)
        table = ProtoTable(page.number, shape, tuple(cells), header, banners, frame, "lattice")
        if header == 0:
            detail = (
                "the table holds no values and its first row is not bold, "
                "so no header row was found"
                if text_only
                else "the table's first rows hold values, so no header row was found"
            )
            findings.append(Finding.of(FindingCode.HEADER_NOT_FOUND, detail, page=page.number))
        crossing = _crossing(cells, table.bbox)
        if crossing:
            detail = f"{crossing} word{'s' if crossing > 1 else ''} cross a drawn column rule"
            findings.append(Finding.of(FindingCode.WORD_CROSSES_RULE, detail, page=page.number))
        tables.append(table)
        claimed |= {w.id for w in table.words}
    return TableStage(tuple(tables), frozenset(claimed), tuple(findings))
