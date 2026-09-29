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
from inkgrid.core.lines import Line, fragments, group_lines
from inkgrid.core.tables.proto import (
    ProtoCell,
    ProtoTable,
    cell_lines,
    table_roles,
)
from inkgrid.core.tables.shape import GridShape, ShapeCell
from inkgrid.model.config import Profile
from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.geometry import Rect, Rotation
from inkgrid.model.page import Rule, Word

Span = tuple[float, float]

MAX_QUALIFIED_TOKENS = 4  # `$5,000 per month`: a value and a few words qualifying it
WRAP_PITCH = 0.8  # a line whose pitch is at most this share of the row pitch wraps the line above
VALUE_WRAP = 0.35  # a value line this close (share of the row pitch) to the last one wraps its row
REACH = 0.5  # a line without a value joins the nearest value line within this share of the pitch
HEIGHT_REACH = 1.5  # ... and within this many line heights, however far apart the values are
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
    # Judged on the whole piece: `CHF 250` is money though neither `CHF` nor `250` is strong alone.
    if is_strong_value(" ".join(tokens)):
        return True
    return len(tokens) <= MAX_QUALIFIED_TOKENS and is_strong_value(tokens[0])


def is_value_like(words: Sequence[Word]) -> bool:
    """True for a piece that reads as a value at all, weak values included (`62`, `1 - 150`)."""
    tokens = _tokens(words)
    return bool(tokens) and is_value(" ".join(tokens))


def _holds_value(words: Sequence[Word]) -> bool:
    """A value-like or a value piece: what anchors rows."""
    return is_value_like(words) or is_value_piece(words)


def _counts_as_value(words: Sequence[Word]) -> bool:
    """What the L2 checks count: a piece that holds a value, or opens with one however long.

    `$10 per million on the value` is too long to make a value row, but it is still a fee, and it
    never shares a row's column or a cell with another.
    """
    tokens = _tokens(words)
    return _holds_value(words) or (bool(tokens) and is_strong_value(tokens[0]))


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


@dataclass(frozen=True, slots=True)
class _Walls:
    """The page's vertical rules by position: a drawn rule between two words ends a piece."""

    ats: tuple[float, ...]
    rules: tuple[Rule, ...]

    @classmethod
    def of(cls, rules: Sequence[Rule]) -> "_Walls":
        vertical = sorted((r for r in rules if r.axis == "v"), key=lambda r: r.at)
        return cls(tuple(r.at for r in vertical), tuple(vertical))

    def between(self, a: Word, b: Word) -> bool:
        """True when a rule stands in the gap from `a` to `b`, across both words' centres."""
        lo = bisect.bisect_left(self.ats, a.bbox.x1)
        hi = bisect.bisect_right(self.ats, b.bbox.x0)
        top, bottom = sorted((a.bbox.center[1], b.bbox.center[1]))
        return any(r.start <= top and bottom <= r.end for r in self.rules[lo:hi])


NO_WALLS = _Walls((), ())


def _pieces(line: Line, profile: Profile, walls: _Walls = NO_WALLS) -> tuple[Line, ...]:
    """The line's fragments, each split again where a drawn vertical rule stands between two words.

    A drawn horizontal rule ends a row (section 2); a vertical one ends a piece (spec 14 s. 3).
    """
    parts = fragments(line, profile)
    if not walls.ats:
        return parts
    out: list[Line] = []
    for part in parts:
        group = [part.words[0]]
        for a, b in pairwise(part.words):
            if walls.between(a, b):
                out.append(Line(tuple(group)))
                group = [b]
            else:
                group.append(b)
        out.append(Line(tuple(group)))
    return tuple(out)


def _row(lines: Sequence[Line], profile: Profile, walls: _Walls = NO_WALLS) -> Row:
    pieces = sorted(
        (p for line in lines for p in _pieces(line, profile, walls)), key=lambda p: p.x0
    )
    return Row(tuple(lines), tuple(pieces))


def _clash(line: Line, row: Sequence[Line], profile: Profile, walls: _Walls = NO_WALLS) -> bool:
    """True when the line holds a value-like piece over one the row already holds (L2)."""
    mine = [p for p in _pieces(line, profile, walls) if _counts_as_value(p.words)]
    theirs = [
        p for other in row for p in _pieces(other, profile, walls) if _counts_as_value(p.words)
    ]
    return any(a.x0 < b.x1 and b.x0 < a.x1 for a in mine for b in theirs)


def _centre(line: Line) -> float:
    return (line.top + line.bottom) / 2


def _ruled_between(a: Line, b: Line, rules: Sequence[Rule]) -> bool:
    """True when a drawn horizontal rule lies between two lines' centres, across line `b`."""
    upper, lower = sorted((_centre(a), _centre(b)))
    return any(
        rule.axis == "h" and upper < rule.at < lower and rule.start < b.x1 and b.x0 < rule.end
        for rule in rules
    )


def _same_weight(
    line: Line, row: Sequence[Line], profile: Profile, walls: _Walls = NO_WALLS
) -> bool:
    """True when each piece of the line is bold, or not, as every piece of the row it lies under."""
    theirs = [q for other in row for q in _pieces(other, profile, walls)]
    return all(
        p.bold == q.bold
        for p in _pieces(line, profile, walls)
        for q in theirs
        if p.x0 < q.x1 and q.x0 < p.x1
    )


def _fold_by_pitch(
    lines: Sequence[Line], profile: Profile, rules: Sequence[Rule], walls: _Walls = NO_WALLS
) -> list[list[Line]]:
    """Rows by pitch alone, for a run with fewer than two value lines (spec 07 section 2)."""
    pitches = [b.top - a.top for a, b in pairwise(lines)]
    wrap = WRAP_PITCH * statistics.median(pitches) if pitches else 0.0
    groups: list[list[Line]] = [[lines[0]]]
    for prev, line in pairwise(lines):
        current = groups[-1]
        if (
            line.top - prev.top <= wrap
            and not _clash(line, current, profile, walls)
            and not _ruled_between(prev, line, rules)
        ):
            current.append(line)
        else:
            groups.append([line])
    return groups


def _value_rows(
    lines: Sequence[Line],
    anchors: Sequence[int],
    pitch: float,
    profile: Profile,
    rules: Sequence[Rule],
    *,
    walls: _Walls = NO_WALLS,
) -> list[list[int]]:
    """Each value line starts a row, unless it wraps the last (close, no clash, no rule between)."""
    groups: list[list[int]] = []
    for i in anchors:
        if groups:
            last = groups[-1][-1]
            close = _centre(lines[i]) - _centre(lines[last]) <= VALUE_WRAP * pitch
            if (
                close
                and not _clash(lines[i], [lines[j] for j in groups[-1]], profile, walls)
                and not _ruled_between(lines[last], lines[i], rules)
            ):
                groups[-1].append(i)
                continue
        groups.append([i])
    return groups


def _nearest_row(
    line: Line,
    lines: Sequence[Line],
    anchors: Sequence[int],
    *,
    owner: dict[int, int],
    reach: float,
    profile: Profile,
    rules: Sequence[Rule],
    walls: _Walls = NO_WALLS,
) -> int | None:
    """The row of the value line nearest this line's centre, within reach and no rule between.

    A line over the value line's pieces must share their weight: a bold caption over a regular label
    is not its wrap. A label in a column of its own (a bold row header) joins in any weight.
    """
    centres = [_centre(lines[i]) for i in anchors]
    at = bisect.bisect(centres, _centre(line))
    best: tuple[float, int] | None = None
    for k in (at - 1, at):
        if 0 <= k < len(anchors):
            anchor = lines[anchors[k]]
            distance = abs(_centre(anchor) - _centre(line))
            nearer = best is None or distance < best[0]
            alike = _same_weight(line, [anchor], profile, walls)
            if distance <= reach and nearer and alike and not _ruled_between(anchor, line, rules):
                best = (distance, owner[anchors[k]])
    return None if best is None else best[1]


def _wrapped_row(
    line: Line,
    lines: Sequence[Line],
    groups: Sequence[list[int]],
    *,
    pitch: float,
    height: float,
    profile: Profile,
    rules: Sequence[Rule],
    walls: _Walls = NO_WALLS,
) -> int | None:
    """The value row directly above that this line wraps: close under its last line, continuing it.

    Closer than a row: within 0.8 x the row pitch and 1.5 line heights of the row's last line. A
    wrap is set in the weight of the pieces it lies under: a bold header under regular cells is not.
    """
    above = [g for g, members in enumerate(groups) if all(lines[i].top < line.top for i in members)]
    if not above:
        return None
    row = max(above, key=lambda g: max(lines[i].top for i in groups[g]))
    members = [lines[i] for i in groups[row]]
    last = max(members, key=lambda other: other.top)
    close = line.top - last.top <= min(WRAP_PITCH * pitch, HEIGHT_REACH * height)
    continues = _continues(members, line, profile, walls) and _same_weight(
        line, members, profile, walls
    )
    if close and continues and not _ruled_between(last, line, rules):
        return row
    return None


def _wrap_lone_values(
    lines: Sequence[Line],
    groups: list[list[int]],
    loose: list[list[int]],
    *,
    limit: float,
    profile: Profile,
    rules: Sequence[Rule],
    walls: _Walls = NO_WALLS,
) -> list[list[int]]:
    """Fold a lone one-piece value line into the value-free row it wraps (a banner's second line).

    `loose` gains the line; the value rows that remain are returned.
    """
    in_loose = {i: row for row in loose for i in row}
    kept: list[list[int]] = []
    for group in groups:
        (i,) = group if len(group) == 1 else (None,)
        above = in_loose.get(i - 1) if i is not None else None
        if (
            i is not None
            and above is not None
            and len(_pieces(lines[i], profile, walls)) == 1
            and lines[i].top - lines[i - 1].top <= limit
            and not _ruled_between(lines[i - 1], lines[i], rules)
            and _continues([lines[j] for j in above], lines[i], profile, walls)
            and not _clash(lines[i], [lines[j] for j in above], profile, walls)
        ):
            above.append(i)
            continue
        kept.append(group)
    return kept


def _continues(row: Sequence[Line], line: Line, profile: Profile, walls: _Walls = NO_WALLS) -> bool:
    """True when the line wraps the row: it continues columns the row has already opened.

    Pieces side by side open columns under a row of one column (a header under a paragraph).
    """
    above = [p for other in row for p in _pieces(other, profile, walls)]
    mine = _pieces(line, profile, walls)
    side_by_side = any(a.x1 <= b.x0 for a, b in pairwise(sorted(above, key=lambda p: p.x0)))
    overlaps = all(any(p.x0 < q.x1 and q.x0 < p.x1 for q in above) for p in mine)
    if overlaps and (len(mine) == 1 or side_by_side):
        return True
    left, right = min(p.x0 for p in above), max(p.x1 for p in above)
    return side_by_side and left <= line.x0 and line.x1 <= right


def fold_rows(
    lines: Sequence[Line], profile: Profile, *, rules: Sequence[Rule] = ()
) -> tuple[Row, ...]:
    """A size run's lines as table rows, anchored on their values (spec 07 section 2).

    Each value line starts a row; every other line joins the value line nearest it within half the
    row pitch; what joins none folds into rows of its own by pitch. A drawn horizontal rule never
    lies inside a row, and two values in one column are never one row (L2).
    """
    if not lines:
        return ()
    walls = _Walls.of(rules)
    valued = [any(_holds_value(p.words) for p in _pieces(line, profile, walls)) for line in lines]
    anchors = [i for i, v in enumerate(valued) if v]
    steps = [_centre(lines[b]) - _centre(lines[a]) for a, b in pairwise(anchors)]
    if not steps:
        return tuple(
            _row(group, profile, walls) for group in _fold_by_pitch(lines, profile, rules, walls)
        )
    pitch = statistics.median(steps)
    height = statistics.median(line.bottom - line.top for line in lines)
    reach = min(REACH * pitch, HEIGHT_REACH * height)
    groups = _value_rows(lines, anchors, pitch, profile, rules, walls=walls)
    owner = {i: g for g, members in enumerate(groups) for i in members}
    loose: list[list[int]] = []
    for i, line in enumerate(lines):
        if valued[i]:
            continue
        # A label wraps within its column: pieces side by side wrap only the row above, by cell.
        single = len(_pieces(line, profile, walls)) == 1
        row = (
            _nearest_row(
                line,
                lines,
                anchors,
                owner=owner,
                reach=reach,
                profile=profile,
                rules=rules,
                walls=walls,
            )
            if single
            else None
        )
        if row is None:
            row = _wrapped_row(
                line,
                lines,
                groups,
                pitch=pitch,
                height=height,
                profile=profile,
                rules=rules,
                walls=walls,
            )
        # Never into a row whose column already holds a value (L2), however close.
        if row is not None and not _clash(line, [lines[j] for j in groups[row]], profile, walls):
            groups[row].append(i)
            continue
        prev = loose[-1][-1] if loose else None
        if (
            prev == i - 1
            and line.top - lines[prev].top <= min(WRAP_PITCH * pitch, HEIGHT_REACH * height)
            and not _ruled_between(lines[prev], line, rules)
            and _continues([lines[j] for j in loose[-1]], line, profile, walls)
            and not _clash(line, [lines[j] for j in loose[-1]], profile, walls)
        ):
            loose[-1].append(i)
        else:
            loose.append([i])
    groups = _wrap_lone_values(
        lines,
        groups,
        loose,
        limit=min(WRAP_PITCH * pitch, HEIGHT_REACH * height),
        profile=profile,
        rules=rules,
        walls=walls,
    )
    rows = [sorted(group) for group in [*groups, *loose]]
    rows.sort(key=lambda group: min(lines[i].top for i in group))
    return tuple(_row([lines[i] for i in group], profile, walls) for group in rows)


def is_value_row(row: Row) -> bool:
    """A row with at least two pieces, one of them past the first a value piece."""
    return len(row.pieces) >= MIN_PIECES and any(is_value_piece(p.words) for p in row.pieces[1:])


def _merged(spans: Sequence[Span], row: Row) -> tuple[Span, ...]:
    """The columns `spans` with a value row's pieces merged in where they overlap."""
    merged: list[list[float]] = []
    for x0, x1 in sorted([*spans, *((p.x0, p.x1) for p in row.pieces)]):
        if merged and x0 <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], x1)
        else:
            merged.append([x0, x1])
    return tuple((a, b) for a, b in merged)


def columns(rows: Sequence[Row]) -> tuple[Span, ...]:
    """The value rows' piece extents, merged where they overlap: the table's columns."""
    spans: tuple[Span, ...] = ()
    for row in rows:
        if is_value_row(row):
            spans = _merged(spans, row)
    return spans


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


def _joined(blanks: Sequence[Span]) -> list[Span]:
    """A row's blanks with touching ones joined, so no point lies in two of them."""
    out: list[Span] = []
    for a, b in blanks:
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def _boundary(lo: float, hi: float, rows: Sequence[Row]) -> float:
    """Where the rows vote the boundary inside the corridor [lo, hi] (spec 07 section 4).

    A candidate's votes are the rows whose blanks hold it less the rows whose blanks do not, and
    its clearance is its distance to the nearest word edge; both are counted by bisection, so a
    long table costs n log n, not n squared.
    """
    blanks = [_blanks(row, lo, hi) for row in rows]
    candidates = dict.fromkeys([(lo + hi) / 2, *((a + b) / 2 for row in blanks for a, b in row)])
    spans = [span for row in blanks for span in _joined(row)]
    starts = sorted(a for a, _ in spans)
    ends = sorted(b for _, b in spans)
    voters = sum(1 for row in blanks if row)
    edges = sorted(e for row in rows for w in row.words for e in (w.bbox.x0, w.bbox.x1))

    def score(x: float) -> tuple[int, float]:
        holding = bisect.bisect_right(starts, x) - bisect.bisect_left(ends, x)
        at = bisect.bisect_left(edges, x)
        clearance = min((abs(x - e) for e in edges[max(at - 1, 0) : at + 1]), default=0.0)
        return 2 * holding - voters, clearance

    return max(candidates, key=score)


def _split(piece: Line, bounds: Sequence[float], size: float) -> list[list[Word]]:
    """The piece cut wherever a boundary falls in a column-sized gap between two of its words.

    A gap narrower than half the row's size is a word space: a boundary there does not split.
    """
    parts: list[list[Word]] = [[piece.words[0]]]
    for prev, word in pairwise(piece.words):
        wide = word.bbox.x0 - prev.bbox.x1 >= MIN_BLANK_EM * size
        if wide and any(prev.bbox.x1 <= b <= word.bbox.x0 for b in bounds):
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


def _values_on_own_lines(words: Sequence[Word], profile: Profile) -> int:
    """Value-like pieces among a cell's words, counted on the cell's own visual lines.

    A word centred beside two rows can chain them into one page-level line (spec 04 section 2),
    so the cell's words are grouped again without it before the values are counted (L2).
    """
    return sum(
        1
        for line in group_lines(words, profile)
        for piece in fragments(line, profile)
        if _counts_as_value(piece.words)
    )


def _row_cells(
    row: Row, bounds: Sequence[float], profile: Profile
) -> list[tuple[int, int, list[Word]]] | None:
    """The row's cells as (first band, last band, words), or None when a cell holds two values."""
    parts = [part for piece in row.pieces for part in _split(piece, bounds, row.size)]
    spans = sorted(
        [
            (
                bisect.bisect_right(bounds, min(w.bbox.x0 for w in part)),
                bisect.bisect_left(bounds, max(w.bbox.x1 for w in part)),
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
        words = [w for part in members for w in part]
        if _values_on_own_lines(words, profile) > 1:
            return None
        out.append((first, last, words))
    return out


def _across(word: Word, x0: float, x1: float) -> bool:
    return x0 <= word.bbox.center[0] < x1


def _outer_edges(
    rows: Sequence[Row], edges: list[float], foreign: Sequence[Word], x0: float, x1: float
) -> list[float]:
    """The table's top and bottom edges moved in past the nearest foreign word they hold.

    The interior-edge rule (spec 07 section 5 item 4) against that word: the middle of the gap,
    kept strictly between its centre and the row's nearest word centre (spec 14 section 5). An
    edge only ever moves in.
    """
    out = list(edges)
    first = min(w.bbox.center[1] for w in rows[0].words)
    above = [w for w in foreign if _across(w, x0, x1) and edges[0] <= w.bbox.center[1] < first]
    if above:
        near = max(above, key=lambda w: w.bbox.center[1])
        lo, mid = near.bbox.center[1], (near.bbox.y1 + rows[0].top) / 2
        out[0] = mid if lo < mid <= first else (lo + first) / 2
    last = max(w.bbox.center[1] for w in rows[-1].words)
    below = [w for w in foreign if _across(w, x0, x1) and last < w.bbox.center[1] < edges[-1]]
    if below:
        near = min(below, key=lambda w: w.bbox.center[1])
        hi, mid = near.bbox.center[1], (rows[-1].bottom + near.bbox.y0) / 2
        out[-1] = mid if last < mid <= hi else (last + hi) / 2
    return out


def corridor_table(
    rows: Sequence[Row],
    spans: Sequence[Span],
    profile: Profile,
    *,
    page: int,
    frame: Rotation,
    others: Sequence[Word] = (),
) -> ProtoTable | None:
    """The rows as a grid on the columns `spans`, or None when they do not make one safely.

    `others` are the page's other content words: the table's edges keep clear of them, and a
    table that would still hold one is refused (spec 14 section 5).
    """
    if len(spans) < MIN_COLUMNS or len(rows) < MIN_ROWS:
        return None
    bounds = [_boundary(a[1], b[0], rows) for a, b in pairwise(spans)]
    words = [w for row in rows for w in row.words]
    col_edges = [min(w.bbox.x0 for w in words), *bounds, max(w.bbox.x1 for w in words) + RIGHT_PAD]
    row_edges = _row_edges(rows)
    if row_edges is None:
        return None
    mine = {w.id for w in words}
    foreign = [w for w in others if w.id not in mine]
    if foreign:
        row_edges = _outer_edges(rows, row_edges, foreign, col_edges[0], col_edges[-1])
        box = Rect(col_edges[0], row_edges[0], col_edges[-1], row_edges[-1])
        if any(box.contains_point(*w.bbox.center) for w in foreign):
            return None
    cells: list[ProtoCell] = []
    for r, row in enumerate(rows):
        found = _row_cells(row, bounds, profile)
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


def _level_with(row: Row, spans: Sequence[Span], foreign: Sequence[Word]) -> bool:
    """True when a word outside the run sits level with the row, within the table's width."""
    x0, x1 = spans[0][0], spans[-1][1]
    return any(
        row.top <= w.bbox.center[1] <= row.bottom and x0 <= w.bbox.center[0] <= x1 for w in foreign
    )


def _extent(
    run: Sequence[Row],
    start: int,
    first: int,
    take: int,
    *,
    others: Sequence[Word] = (),
) -> tuple[int, int, tuple[Span, ...], int]:
    """The rows (lo, hi) of the table whose first value row is `first`, and its columns.

    It takes at most `take` value rows, and says how many it took. A row level with a word of
    `others` outside the run (another region's line) is not taken above or below (spec 14 s. 5).
    """
    in_run = {w.id for row in run for w in row.words}
    foreign = [w for w in others if w.id not in in_run]
    taken = 1
    last = first
    spans = _merged((), run[first])
    tol = 0.5 * run[first].size
    for k in range(first + 1, len(run)):
        if taken == take:
            break
        if not is_value_row(run[k]):
            continue
        between = run[last + 1 : k]
        # A row of several pieces holding no value at all (not even `Free` or `-`) before more
        # values is the next table's column header.
        if any(
            _side_by_side(row) and not any(_holds_value(p.words) for p in row.pieces)
            for row in between
        ):
            break
        grown = _merged(spans, run[k])
        if not all(_fits(row, grown, tol) for row in between):
            break
        taken, last, spans = taken + 1, k, grown
    hi = last
    while hi + 1 < len(run) and _side_by_side(run[hi + 1]):
        below = run[hi + 1]
        if _has_value_piece(below) or not _fits(below, spans, tol):
            break
        if _level_with(below, spans, foreign):
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
        if _level_with(above, spans, foreign):
            break
        lo -= 1
    return lo, hi, spans, taken


Found = tuple[int, int, ProtoTable]  # a table's first and last rows in its run, and the table


def _grown(
    run: Sequence[Row],
    start: int,
    first: int,
    profile: Profile,
    *,
    page: int,
    frame: Rotation,
    others: Sequence[Word] = (),
) -> tuple[Found | None, tuple[int, int] | None]:
    """The table from `first` with the most value rows that grid, and its extent if refused.

    The whole extent is tried first. When it is refused, value rows are taken 1, 2, 4, ... while
    the rows make a grid, then halved back between the last count that did and the first that did
    not (spec 07 section 3 item 7): a refusal costs a few attempts, not one per row. An extent is
    refused when it reads as a table (2 rows, 2 columns) but no grid holds it safely.
    """
    best: Found | None = None

    def attempt(take: int) -> tuple[int, tuple[int, int] | None]:
        nonlocal best
        lo, hi, spans, taken = _extent(run, start, first, take, others=others)
        table = corridor_table(
            run[lo : hi + 1], spans, profile, page=page, frame=frame, others=others
        )
        if table is not None:
            best = (lo, hi, table)
        elif len(spans) >= MIN_COLUMNS and hi - lo + 1 >= MIN_ROWS:
            return taken, (lo, hi)
        return taken, None

    whole, refused = attempt(len(run))
    if refused is None:
        return best, None
    good, bad, take = 0, whole, 1
    while take < bad:
        taken, wide = attempt(take)
        if wide is not None:
            bad = taken
            break
        good, take = taken, 2 * take
    while bad - good > 1:
        mid = (good + bad) // 2
        if attempt(mid)[1] is None:
            good = mid
        else:
            bad = mid
    return best, refused


def _run_tables(
    run: Sequence[Row],
    profile: Profile,
    *,
    page: int,
    frame: Rotation,
    others: Sequence[Word] = (),
) -> tuple[list[Found], list[list[int]]]:
    """Every table in one size run, and the runs of rows that read as a table but are in none."""
    found: list[Found] = []
    refused: set[int] = set()
    start = 0
    while True:
        first = next((k for k in range(start, len(run)) if is_value_row(run[k])), None)
        if first is None:
            break
        best, wide = _grown(run, start, first, profile, page=page, frame=frame, others=others)
        if wide is not None:
            refused.update(range(wide[0], wide[1] + 1))
        if best is None:
            start = first + 1
            continue
        found.append(best)
        start = best[1] + 1
    claimed = {k for lo, hi, _ in found for k in range(lo, hi + 1)}
    stretches: list[list[int]] = []
    for k in sorted(refused - claimed):
        if stretches and stretches[-1][-1] == k - 1:
            stretches[-1].append(k)
        else:
            stretches.append([k])
    return found, stretches


def _left_as_text(rows: Sequence[Row], page: int) -> Finding:
    """The warning for rows that read as a table but that no grid holds (never silent, G4)."""
    n = len(rows)
    first = " ".join(w.text for w in rows[0].lines[0].words)
    detail = (
        f"{n} row{'s' if n > 1 else ''} of a table left as text, from `{first[:60]}`: no grid holds"
        f" {'them' if n > 1 else 'it'} without fusing two values or two rows"
    )
    return Finding.of(FindingCode.TABLE_LEFT_AS_TEXT, detail, page=page)


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
    others: Sequence[Word] = (),
) -> CorridorStage:
    """Unruled tables in each run of stacked regions; the other lines go back to prose.

    `rules` are the page's drawn rules, in the regions' frame: horizontal ones end rows, vertical
    ones end pieces. `others` are the page's content words, which no table may hold unless they
    are its own (spec 14 section 5).
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
            found, left = _run_tables(run, profile, page=page, frame=frame, others=others)
            for lo, hi, table in found:
                tables.append(table)
                claimed |= {id(line) for row in run[lo : hi + 1] for line in row.lines}
            findings.extend(_left_as_text([run[k] for k in stretch], page) for stretch in left)
        out.extend(_leftover(group, claimed) if claimed else group)
        i = j
    return CorridorStage(tuple(tables), tuple(out), tuple(findings))
