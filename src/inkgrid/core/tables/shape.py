"""Cell rectangles to rows, columns, and spans (docs/specs/06-ruled-tables.md section 4)."""

import bisect
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from inkgrid.model.geometry import Rect

SNAP = 0.5  # pt: edges closer than this are one edge


@dataclass(frozen=True, slots=True)
class ShapeCell:
    """One cell: its first row and column, its spans, and its rectangle on the snapped edges."""

    row: int
    col: int
    row_span: int
    col_span: int
    rect: Rect


@dataclass(frozen=True, slots=True)
class GridShape:
    """A grid's edges, top to bottom and left to right, and its cells in (row, col) order."""

    row_edges: tuple[float, ...]
    col_edges: tuple[float, ...]
    cells: tuple[ShapeCell, ...]


def _edges(values: Iterable[float]) -> tuple[float, ...]:
    edges: list[float] = []
    for value in sorted(values):
        if not edges or value - edges[-1] > SNAP:
            edges.append(value)
    return tuple(edges)


def _index(edges: Sequence[float], value: float) -> int:
    """The edge `value` snaps to."""
    i = bisect.bisect_left(edges, value - SNAP)
    return min(range(i, min(i + 2, len(edges))), key=lambda k: abs(edges[k] - value))


def grid_shape(cells: Sequence[Rect]) -> GridShape | None:
    """The grid the rectangles form, or None when they do not tile their bounding box exactly."""
    rows = _edges(v for r in cells for v in (r.y0, r.y1))
    cols = _edges(v for r in cells for v in (r.x0, r.x1))
    covered: set[tuple[int, int]] = set()
    shaped: list[ShapeCell] = []
    for rect in cells:
        r0, r1 = _index(rows, rect.y0), _index(rows, rect.y1)
        c0, c1 = _index(cols, rect.x0), _index(cols, rect.x1)
        if r1 <= r0 or c1 <= c0:
            return None
        positions = {(r, c) for r in range(r0, r1) for c in range(c0, c1)}
        if positions & covered:
            return None
        covered |= positions
        snapped = Rect(cols[c0], rows[r0], cols[c1], rows[r1])
        shaped.append(ShapeCell(r0, c0, r1 - r0, c1 - c0, snapped))
    if len(covered) != (len(rows) - 1) * (len(cols) - 1):
        return None
    return GridShape(rows, cols, tuple(sorted(shaped, key=lambda c: (c.row, c.col))))
