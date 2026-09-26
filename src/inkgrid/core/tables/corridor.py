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

from inkgrid.core.layout import Region
from inkgrid.core.lexicon import is_strong_value, is_value
from inkgrid.core.lines import Line, fragments
from inkgrid.core.tables.proto import (
    ProtoCell,
    ProtoTable,
    cell_lines,
    missing_header,
    table_roles,
)
from inkgrid.core.tables.shape import GridShape, ShapeCell
from inkgrid.model.config import Profile
from inkgrid.model.findings import Finding
from inkgrid.model.geometry import Rect, Rotation
from inkgrid.model.page import Rule, Word

Span = tuple[float, float]

MAX_QUALIFIED_TOKENS = 4  # `$5,000 per month`: a value and a few words qualifying it
WRAP_PITCH = 0.8  # a line whose pitch is at most this share of the block's typical pitch wraps
MIN_BLANK_EM = 0.5  # narrower gaps are word spacing, not column space
MIN_PIECES = MIN_COLUMNS = MIN_ROWS = 2
MAX_HEADER_ROWS = 3  # rows above the first value row a table may take: header, caption, banner
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


def _ruled_between(prev: Line, line: Line, rules: Sequence[Rule]) -> bool:
    """True when a drawn horizontal rule lies between two lines' centres, across the line."""
    upper = (prev.top + prev.bottom) / 2
    lower = (line.top + line.bottom) / 2
    return any(
        rule.axis == "h" and upper < rule.at < lower and rule.start < line.x1 and line.x0 < rule.end
        for rule in rules
    )


def fold_rows(
    lines: Sequence[Line], profile: Profile, *, rules: Sequence[Rule] = ()
) -> tuple[Row, ...]:
    """Consecutive lines as table rows: a wrap joins its row, but two values never share one.

    A wrap is told by its pitch (top to top), not its gap: MuPDF's boxes span the font's full
    ascent and descent, so rows at ordinary leading overlap like wraps do. A drawn horizontal rule
    between two lines always ends the row (spec 07 section 2).
    """
    if not lines:
        return ()
    pitches = [b.top - a.top for a, b in pairwise(lines)]
    wrap = WRAP_PITCH * statistics.median(pitches) if pitches else 0.0
    groups: list[list[Line]] = [[lines[0]]]
    for prev, line in pairwise(lines):
        current = groups[-1]
        if (
            line.top - prev.top <= wrap
            and not _clash(line, current, profile)
            and not _ruled_between(prev, line, rules)
        ):
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
    header, banners, text_only = table_roles(cells, len(rows))
    return ProtoTable(page, grid, tuple(cells), header, banners, frame, "corridor", text_only)


@dataclass(frozen=True, slots=True)
class CorridorStage:
    """What the corridor stage made of a page: tables, the regions left for prose, and findings."""

    tables: tuple[ProtoTable, ...]
    regions: tuple[Region, ...]
    findings: tuple[Finding, ...]


def _side_by_side(row: Row) -> bool:
    """True when two pieces of the row sit apart horizontally: cells, not a wrapped cell."""
    return any(a.x1 <= b.x0 for a, b in pairwise(row.pieces))


def _has_value_piece(row: Row) -> bool:
    return any(is_value_piece(p.words) for p in row.pieces)


def _fits(row: Row, spans: Sequence[Span], tol: float) -> bool:
    """True when every piece of the row is anchored to the columns (spec 07 section 3 item 4).

    A piece is anchored by its centre at the centre of a span of consecutive columns, or by its
    start at a column's start or its end at a column's end while it lies within the table's width:
    a centred header may be wider than its column, a sentence may not run past the columns.
    """
    lo, hi = spans[0][0] - tol, spans[-1][1] + tol
    starts = [a for a, _ in spans]
    ends = [b for _, b in spans]
    centres = [
        (spans[i][0] + spans[j][1]) / 2 for i in range(len(spans)) for j in range(i, len(spans))
    ]
    for piece in row.pieces:
        mid = (piece.x0 + piece.x1) / 2
        if any(abs(mid - c) <= tol for c in centres):
            continue
        within = lo <= piece.x0 and piece.x1 <= hi
        edge = any(abs(piece.x0 - a) <= tol for a in starts) or any(
            abs(piece.x1 - b) <= tol for b in ends
        )
        if not (within and edge):
            return False
    return True


def _size_runs(lines: Sequence[Line], profile: Profile) -> list[list[Line]]:
    """The lines split wherever the type size changes (prose rule 2, against the smaller size)."""
    runs: list[list[Line]] = []
    for line in lines:
        if runs:
            prev = runs[-1][-1]
            if abs(line.size - prev.size) <= profile.size_change_ratio * min(line.size, prev.size):
                runs[-1].append(line)
                continue
        runs.append([line])
    return runs


def _extent(run: Sequence[Row], start: int, first: int) -> tuple[int, int, tuple[Span, ...]]:
    """The rows (lo, hi) of the table whose first value row is `first`, and its columns."""
    members = [first]
    last = first
    tol = 0.5 * run[first].size
    for k in range(first + 1, len(run)):
        if not is_value_row(run[k]):
            continue
        between = [run[j] for j in range(last + 1, k)]
        # A row of several pieces holding no value at all (not even `Free` or `-`) before more
        # values is the next table's column header.
        if any(
            _side_by_side(row) and not any(is_value_like(p.words) for p in row.pieces)
            for row in between
        ):
            break
        spans = columns([run[j] for j in [*members, k]])
        if all(_fits(row, spans, tol) for row in between):
            members.append(k)
            last = k
        else:
            break
    spans = columns([run[j] for j in members])
    hi = last
    while hi + 1 < len(run) and _side_by_side(run[hi + 1]):
        below = run[hi + 1]
        if _has_value_piece(below) or not _fits(below, spans, tol):
            break
        hi += 1
    # Rows that lead up to another value row are the next table's header: give them back.
    if hi + 1 < len(run) and is_value_row(run[hi + 1]):
        hi = last
    lo = first
    while lo - 1 >= start and first - (lo - 1) <= MAX_HEADER_ROWS:
        above = run[lo - 1]
        if _has_value_piece(above) or not _fits(above, spans, tol):
            break
        lo -= 1
    return lo, hi, spans


def _run_tables(
    run: Sequence[Row], profile: Profile, *, page: int, frame: Rotation
) -> list[tuple[int, int, ProtoTable]]:
    """Every table in one size run, as (first row, last row, table)."""
    found: list[tuple[int, int, ProtoTable]] = []
    start = 0
    while True:
        first = next((k for k in range(start, len(run)) if is_value_row(run[k])), None)
        if first is None:
            return found
        lo, hi, spans = _extent(run, start, first)
        table = corridor_table(run[lo : hi + 1], spans, profile, page=page, frame=frame)
        if table is None:
            start = first + 1
            continue
        found.append((lo, hi, table))
        start = hi + 1


def _leftover(group: Sequence[Region], claimed: set[int]) -> list[Region]:
    """The group's unclaimed lines as regions, cut where a table was or a region ended."""
    out: list[Region] = []
    for region in group:
        current: list[Line] = []
        for line in region.lines:
            if id(line) in claimed:
                if current:
                    out.append(Region(region.kind, tuple(current)))
                    current = []
            else:
                current.append(line)
        if current:
            out.append(Region(region.kind, tuple(current)))
    return out


def corridor_tables(
    regions: Sequence[Region],
    profile: Profile,
    *,
    page: int,
    frame: Rotation,
    rules: Sequence[Rule] = (),
) -> CorridorStage:
    """Unruled tables in each run of stacked regions; the other lines go back to prose.

    `rules` are the page's drawn rules, in the regions' frame; horizontal ones end rows.
    """
    tables: list[ProtoTable] = []
    out: list[Region] = []
    findings: list[Finding] = []
    i = 0
    while i < len(regions):
        # A candidate is a run of regions that stack; side-by-side columns never do (section 3).
        j = i + 1
        while j < len(regions) and regions[j].lines[0].top > regions[j - 1].lines[-1].top:
            j += 1
        group = regions[i:j]
        claimed: set[int] = set()
        # Fold each size run on its own: the headings' pitch must not set the table's.
        for lines in _size_runs([line for region in group for line in region.lines], profile):
            run = fold_rows(lines, profile, rules=rules)
            for lo, hi, table in _run_tables(run, profile, page=page, frame=frame):
                tables.append(table)
                findings.extend(missing_header(table))
                claimed |= {id(line) for row in run[lo : hi + 1] for line in row.lines}
        out.extend(_leftover(group, claimed) if claimed else group)
        i = j
    return CorridorStage(tuple(tables), tuple(out), tuple(findings))
