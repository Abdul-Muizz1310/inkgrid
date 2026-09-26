"""Tables before assembly, shared by the ruled and the unruled gridder (specs 06 and 07)."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from inkgrid.core.lexicon import is_strong_value, is_value
from inkgrid.core.lines import Line, group_lines
from inkgrid.core.tables.shape import GridShape, ShapeCell
from inkgrid.model.config import Profile
from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.geometry import Rect, Rotation
from inkgrid.model.page import Word


@dataclass(frozen=True, slots=True)
class ProtoCell:
    """One cell of a proto table: its place in the grid and its words as lines."""

    cell: ShapeCell
    lines: tuple[Line, ...]

    @property
    def words(self) -> tuple[Word, ...]:
        """The cell's words in reading order."""
        return tuple(w for line in self.lines for w in line.words)


@dataclass(frozen=True, slots=True)
class ProtoTable:
    """A table before assembly: its shape, cells, header and banner rows, frame, and gridder."""

    page: int
    shape: GridShape
    cells: tuple[ProtoCell, ...]
    header_rows: int
    banner_rows: tuple[int, ...]
    frame: Rotation
    source: Literal["lattice", "corridor"]
    text_only: bool = False  # no value to tell headers from: header_rows came from bold type

    @property
    def bbox(self) -> Rect:
        """The grid's outer rectangle, in the frame it was read in."""
        rows, cols = self.shape.row_edges, self.shape.col_edges
        return Rect(cols[0], rows[0], cols[-1], rows[-1])

    @property
    def words(self) -> tuple[Word, ...]:
        """The table's words, cell by cell in (row, col) order."""
        return tuple(w for cell in self.cells for w in cell.words)


def is_value_cell(cell: ProtoCell) -> bool:
    """A value cell, reading past note marks (superscripts) and qualifiers around the value."""
    tokens = [w.text for w in cell.words if not w.superscript]
    return is_value(" ".join(tokens)) or any(is_strong_value(t) for t in tokens)


def cell_lines(words: Sequence[Word], profile: Profile) -> tuple[Line, ...]:
    """A cell's lines: horizontal words by position, then rotated words in id order (04, 4)."""
    across = group_lines([w for w in words if w.horizontal], profile)
    turned = tuple(sorted((w for w in words if not w.horizontal), key=lambda w: w.id))
    return (*across, Line(turned)) if turned else across


def table_roles(cells: Sequence[ProtoCell], n_rows: int) -> tuple[int, tuple[int, ...], bool]:
    """Header rows, banner rows, and whether the table holds no value to tell headers from."""
    rows: list[tuple[bool, bool, bool]] = []  # (has words, has a value, full width)
    for r in range(n_rows):
        holding = [c for c in cells if c.cell.row == r and c.words]
        values = any(is_value_cell(c) for c in holding)
        rows.append((bool(holding), values, len(holding) == 1 and holding[0].cell.col == 0))
    banners = tuple(r for r, (has, values, full) in enumerate(rows) if has and full and not values)
    header, columns = 0, False
    for has, values, full in rows:
        if not has or values or (full and columns):
            break
        columns = columns or not full
        header += 1
    text_only = header == n_rows
    if text_only:
        first = [w for c in cells if c.cell.row == 0 for w in c.words]
        header = 1 if first and all(w.bold for w in first) else 0
    # Reach down to the last row a header cell spans: HTML ends a rowspan at its row group.
    while 0 < header < n_rows:
        reach = max(c.cell.row + c.cell.row_span for c in cells if c.cell.row < header)
        if reach <= header:
            break
        header = min(reach, n_rows)
    return header, banners, text_only


def missing_header(table: ProtoTable) -> tuple[Finding, ...]:
    """`header_not_found` for a table with no header row, saying why; nothing otherwise."""
    if table.header_rows:
        return ()
    detail = (
        "the table holds no values and its first row is not bold, so no header row was found"
        if table.text_only
        else "the table's first rows hold values, so no header row was found"
    )
    return (Finding.of(FindingCode.HEADER_NOT_FOUND, detail, page=table.page),)
