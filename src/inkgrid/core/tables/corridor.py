"""Unruled tables from whitespace corridors (docs/specs/07-unruled-tables.md).

Columns come from the whitespace between the value rows' pieces, which stays put however a column is
aligned; every row votes on where each boundary sits; and two values never share a cell (L2, L11).
"""

import bisect
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property
from itertools import pairwise

from inkgrid.core.lexicon import is_strong_value, is_value
from inkgrid.core.lines import Line, fragments
from inkgrid.core.tables.proto import ProtoCell, ProtoTable, cell_lines, table_roles
from inkgrid.core.tables.shape import GridShape, ShapeCell
from inkgrid.model.config import Profile
from inkgrid.model.geometry import Rect, Rotation
from inkgrid.model.page import Word

Span = tuple[float, float]

MAX_QUALIFIED_TOKENS = 4  # `$5,000 per month`: a value and a few words qualifying it
WRAP_RATIO = 0.35  # a line closer than this share of the block's typical gap wraps its row
MIN_WRAP = 0.5  # pt: the wrap threshold is never smaller
MIN_BLANK_EM = 0.5  # narrower gaps are word spacing, not column space
MIN_PIECES = MIN_COLUMNS = MIN_ROWS = 2
RIGHT_PAD = 0.01  # pt past the rightmost word, so its centre sits inside the last band


def _tokens(words: Sequence[Word]) -> list[str]:
    """The piece's tokens without its note marks (superscript words)."""
    return [w.text for w in words if not w.superscript]


def is_value_piece(words: Sequence[Word]) -> bool:
    """True for a piece that holds a value cell: it is a strong value, or opens with one."""
    tokens = _tokens(words)
    if not tokens:
        return False
    if is_value(" ".join(tokens)) and any(is_strong_value(t) for t in tokens):
        return True
    return len(tokens) <= MAX_QUALIFIED_TOKENS and is_strong_value(tokens[0])


def is_value_like(words: Sequence[Word]) -> bool:
    """True for a piece that reads as a value at all, weak values included (`62`, `1 - 150`)."""
    tokens = _tokens(words)
    return bool(tokens) and is_value(" ".join(tokens))


@dataclass(frozen=True)
class Row:
    """One table row: its lines top to bottom, and their pieces left to right."""

    lines: tuple[Line, ...]
    pieces: tuple[Line, ...]

    @cached_property
    def top(self) -> float:
        """The highest line top."""
        return min(line.top for line in self.lines)

    @cached_property
    def bottom(self) -> float:
        """The lowest line bottom."""
        return max(line.bottom for line in self.lines)

    @cached_property
    def size(self) -> float:
        """The median size of the row's words."""
        return statistics.median(w.size for line in self.lines for w in line.words)

    @cached_property
    def words(self) -> tuple[Word, ...]:
        """The row's words, line by line."""
        return tuple(w for line in self.lines for w in line.words)


def _row(lines: Sequence[Line], profile: Profile) -> Row:
    pieces = sorted((p for line in lines for p in fragments(line, profile)), key=lambda p: p.x0)
    return Row(tuple(lines), tuple(pieces))


def _clash(line: Line, row: Sequence[Line], profile: Profile) -> bool:
    """True when the line holds a value-like piece over one the row already holds (L2)."""
    mine = [p for p in fragments(line, profile) if is_value_like(p.words)]
    theirs = [p for other in row for p in fragments(other, profile) if is_value_like(p.words)]
    return any(a.x0 < b.x1 and b.x0 < a.x1 for a in mine for b in theirs)


def fold_rows(lines: Sequence[Line], profile: Profile) -> tuple[Row, ...]:
    """Consecutive lines as table rows: a wrap joins its row, but two values never share one."""
    if not lines:
        return ()
    gaps = [b.top - a.bottom for a, b in pairwise(lines) if b.top > a.bottom]
    wrap = max(WRAP_RATIO * statistics.median(gaps), MIN_WRAP) if gaps else MIN_WRAP
    groups: list[list[Line]] = [[lines[0]]]
    for line in lines[1:]:
        current = groups[-1]
        gap = line.top - max(other.bottom for other in current)
        if gap <= wrap and not _clash(line, current, profile):
            current.append(line)
        else:
            groups.append([line])
    return tuple(_row(group, profile) for group in groups)


def is_value_row(row: Row) -> bool:
    """A row with at least two pieces, one of them past the first a value piece."""
    return len(row.pieces) >= MIN_PIECES and any(is_value_piece(p.words) for p in row.pieces[1:])


def columns(rows: Sequence[Row]) -> tuple[Span, ...]:
    """The value rows' piece extents, merged where they overlap: the table's columns."""
    spans = sorted((p.x0, p.x1) for row in rows if is_value_row(row) for p in row.pieces)
    merged: list[list[float]] = []
    for x0, x1 in spans:
        if merged and x0 <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], x1)
        else:
            merged.append([x0, x1])
    return tuple((a, b) for a, b in merged)


def _blanks(row: Row, lo: float, hi: float) -> list[Span]:
    """The parts of [lo, hi] none of the row's words cover, at least half its size wide."""
    out: list[Span] = []
    at = lo
    for word in sorted(row.words, key=lambda w: w.bbox.x0):
        if word.bbox.x1 <= at or word.bbox.x0 >= hi:
            continue
        if word.bbox.x0 > at:
            out.append((at, word.bbox.x0))
        at = max(at, word.bbox.x1)
    if at < hi:
        out.append((at, hi))
    return [(a, b) for a, b in out if b - a >= MIN_BLANK_EM * row.size]


def _boundary(lo: float, hi: float, rows: Sequence[Row]) -> float:
    """Where the rows vote the boundary inside the corridor [lo, hi] (spec 07 section 4)."""
    blanks = [_blanks(row, lo, hi) for row in rows]
    candidates = [(lo + hi) / 2, *((a + b) / 2 for row in blanks for a, b in row)]
    edges = [e for row in rows for w in row.words for e in (w.bbox.x0, w.bbox.x1)]

    def score(x: float) -> tuple[int, float]:
        votes = sum(1 if any(a <= x <= b for a, b in row) else -1 for row in blanks if row)
        clearance = min((abs(x - e) for e in edges), default=0.0)
        return votes, clearance

    return max(candidates, key=score)


def _split(piece: Line, bounds: Sequence[float]) -> list[list[Word]]:
    """The piece cut wherever a boundary falls in the gap between two of its words."""
    parts: list[list[Word]] = [[piece.words[0]]]
    for prev, word in pairwise(piece.words):
        if any(prev.bbox.x1 <= b <= word.bbox.x0 for b in bounds):
            parts.append([word])
        else:
            parts[-1].append(word)
    return parts


def _row_edges(rows: Sequence[Row]) -> list[float] | None:
    """Contiguous row bands, or None when two rows' word centres interleave."""
    edges = [rows[0].top]
    for upper, lower in pairwise(rows):
        lo = max(w.bbox.center[1] for w in upper.words)
        hi = min(w.bbox.center[1] for w in lower.words)
        if lo >= hi:
            return None
        mid = (upper.bottom + lower.top) / 2
        edges.append(mid if lo < mid <= hi else (lo + hi) / 2)
    edges.append(rows[-1].bottom)
    return edges


def _row_cells(row: Row, bounds: Sequence[float]) -> list[tuple[int, int, list[Word]]] | None:
    """The row's cells as (first band, last band, words), or None when a cell holds two values."""
    parts = [part for piece in row.pieces for part in _split(piece, bounds)]
    spans = sorted(
        [
            (
                bisect.bisect_right(bounds, part[0].bbox.x0),
                bisect.bisect_left(bounds, part[-1].bbox.x1),
                part,
            )
            for part in parts
        ],
        key=lambda span: (span[0], span[1]),
    )
    cells: list[tuple[int, int, list[list[Word]]]] = []
    for first, last, part in spans:
        if cells and first <= cells[-1][1]:
            start, end, members = cells[-1]
            cells[-1] = (start, max(end, last), [*members, part])
        else:
            cells.append((first, last, [part]))
    out: list[tuple[int, int, list[Word]]] = []
    for first, last, members in cells:
        if sum(1 for part in members if is_value_like(part)) > 1:
            return None
        out.append((first, last, [w for part in members for w in part]))
    return out


def corridor_table(
    rows: Sequence[Row],
    spans: Sequence[Span],
    profile: Profile,
    *,
    page: int,
    frame: Rotation,
) -> ProtoTable | None:
    """The rows as a grid on the columns `spans`, or None when they do not make one safely."""
    if len(spans) < MIN_COLUMNS or len(rows) < MIN_ROWS:
        return None
    bounds = [_boundary(a[1], b[0], rows) for a, b in pairwise(spans)]
    words = [w for row in rows for w in row.words]
    col_edges = [min(w.bbox.x0 for w in words), *bounds, max(w.bbox.x1 for w in words) + RIGHT_PAD]
    row_edges = _row_edges(rows)
    if row_edges is None:
        return None
    cells: list[ProtoCell] = []
    for r, row in enumerate(rows):
        found = _row_cells(row, bounds)
        if found is None:
            return None
        taken = {c for first, last, _ in found for c in range(first, last + 1)}
        entries = [*found, *((c, c, []) for c in range(len(spans)) if c not in taken)]
        for first, last, members in sorted(entries, key=lambda e: e[0]):
            rect = Rect(col_edges[first], row_edges[r], col_edges[last + 1], row_edges[r + 1])
            shape = ShapeCell(r, first, 1, last - first + 1, rect)
            cells.append(ProtoCell(shape, cell_lines(members, profile)))
    grid = GridShape(tuple(row_edges), tuple(col_edges), tuple(c.cell for c in cells))
    header, banners, _ = table_roles(cells, len(rows))
    return ProtoTable(page, grid, tuple(cells), header, banners, frame, "corridor")
