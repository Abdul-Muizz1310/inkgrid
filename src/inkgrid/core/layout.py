"""Column sections and reading order (docs/specs/04-text-pipeline.md section 4).

A gutter alone does not make columns: the narrowest table columns are as close as a label and its
text (L19). Prose columns need a gutter that persists over several lines and prose on both sides;
everything else keeps row order, which is right for tables and hanging-indent lists. A column that
is not prose beside prose columns is a stray, or a remainder laid out again in its own width
(docs/specs/19-ocr-benchmark-fixes.md section 2).
"""

import bisect
import statistics
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from inkgrid.core.lexicon import is_value_piece
from inkgrid.core.lines import Line, fragments, group_lines
from inkgrid.model.config import Profile
from inkgrid.model.page import Word

PROSE_MIN_WIDTH_EM = 10.0  # a column this many body sizes wide, its lines filling ...
PROSE_MIN_FILL = 0.6  # ... this share of it, is prose however few words its lines hold
MAX_BUSY_SHARE = 0.5  # more of a column's lines in two fragments or more, and it is not one column
MIN_PROSE_COLUMNS = 2  # beside strays alone, a section needs this many prose columns
MAX_DEPTH = 4  # a remainder laid out again within a remainder, at most this many levels

Interval = tuple[float, float]


@dataclass(frozen=True, slots=True)
class Region:
    """Lines to read in order: one prose column, or column-shaped rows (a table candidate)."""

    kind: Literal["prose", "rows"]
    lines: tuple[Line, ...]


@dataclass(frozen=True, slots=True)
class _Row:
    line: Line
    parts: tuple[Line, ...]
    free: tuple[Interval, ...]


def _free(parts: Sequence[Line], lo: float, hi: float) -> tuple[Interval, ...]:
    """The part of [lo, hi] that no fragment covers, as sorted disjoint intervals."""
    out: list[Interval] = []
    at = lo
    for part in parts:
        if part.x0 > at:
            out.append((at, part.x0))
        at = max(at, part.x1)
    if at < hi:
        out.append((at, hi))
    return tuple(out)


def _intersect(a: Sequence[Interval], b: Sequence[Interval]) -> tuple[Interval, ...]:
    out: list[Interval] = []
    i = j = 0
    while i < len(a) and j < len(b):
        lo = max(a[i][0], b[j][0])
        hi = min(a[i][1], b[j][1])
        if lo < hi:
            out.append((lo, hi))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return tuple(out)


def _gutters(free: Sequence[Interval], left: float, right: float, width: float) -> list[Interval]:
    """The free intervals, clipped to (left, right), that are at least `width` wide."""
    clipped = ((max(lo, left), min(hi, right)) for lo, hi in free)
    return [(lo, hi) for lo, hi in clipped if hi - lo >= width]


@dataclass
class _Run:
    rows: list[_Row]
    free: tuple[Interval, ...]
    left: float
    right: float

    def extended(self, row: _Row) -> "_Run":
        return _Run(
            [*self.rows, row],
            _intersect(self.free, row.free),
            min(self.left, row.line.x0),
            max(self.right, row.line.x1),
        )


def _prose_column(
    parts: Sequence[Line], lines: int, busy: int, profile: Profile, body_size: float
) -> bool:
    """A column of prose: enough fragments, one column, and either words or width and fill."""
    if len(parts) < profile.column_min_lines or busy > MAX_BUSY_SHARE * lines:
        return False
    if sum(len(part.words) for part in parts) / len(parts) >= profile.prose_min_words:
        return True
    if any(is_value_piece(part.words) for part in parts):
        return False  # a column of values is prose only by its words, as 0.1.0 read it
    width = max(part.x1 for part in parts) - min(part.x0 for part in parts)
    if width <= 0 or width < PROSE_MIN_WIDTH_EM * body_size:
        return False
    return statistics.mean(part.x1 - part.x0 for part in parts) >= PROSE_MIN_FILL * width


def _columns(
    run: _Run, gutters: Sequence[Interval], profile: Profile, body_size: float, depth: int
) -> list[Region] | None:
    """One prose region per column, or None when the section is not prose columns.

    Beside prose columns, a stray (too few fragments) and a remainder holding prose columns of its
    own are laid out again, in a section holding no value; any other column refuses the section.
    """
    cuts = [(lo + hi) / 2 for lo, hi in gutters]
    count = len(cuts) + 1
    parts: list[list[Line]] = [[] for _ in range(count)]
    lines: list[list[Line]] = [[] for _ in range(count)]
    busy = [0] * count
    for row in run.rows:
        words: list[list[Word]] = [[] for _ in range(count)]
        held: Counter[int] = Counter()
        for part in row.parts:
            index = bisect.bisect(cuts, (part.x0 + part.x1) / 2)
            parts[index].append(part)
            words[index].extend(part.words)
            held[index] += 1
        for index, column_words in enumerate(words):
            if column_words:
                lines[index].append(Line(tuple(column_words)))
        for index, n in held.items():
            busy[index] += n > 1
    prose = [
        _prose_column(column, len(column_lines), n, profile, body_size)
        for column, column_lines, n in zip(parts, lines, busy, strict=True)
    ]
    if all(prose):
        return [Region("prose", tuple(column)) for column in lines]
    if not any(prose) or depth >= MAX_DEPTH:
        return None
    if any(is_value_piece(part.words) for column in parts for part in column):
        return None  # values beside prose columns: a table's, read in rows as 0.1.0 read it
    out: list[Region] = []
    nested = False
    for ok, column, column_lines in zip(prose, parts, lines, strict=True):
        if ok:
            out.append(Region("prose", tuple(column_lines)))
            continue
        stray = len(column) < profile.column_min_lines
        regions, held_columns = _again(column_lines, profile, body_size, depth)
        if not stray and not held_columns:
            return None  # a table's label column beside its text
        nested = nested or held_columns
        out.extend(regions)
    if sum(prose) < MIN_PROSE_COLUMNS and not nested:
        return None  # strays beside one prose column: a short table's cells
    return out


def _again(
    lines: Sequence[Line], profile: Profile, body_size: float, depth: int
) -> tuple[list[Region], bool]:
    """A column's lines laid out on their own, in its own width, and whether it held columns."""
    lo = min(line.x0 for line in lines)
    hi = max(line.x1 for line in lines)
    rows = []
    for line in lines:
        parts = fragments(line, profile)
        rows.append(_Row(line, parts, _free(parts, lo, hi)))
    return _sections(rows, profile, body_size, depth + 1)


def _run_from(rows: Sequence[_Row]) -> _Run:
    run = _Run([rows[0]], rows[0].free, rows[0].line.x0, rows[0].line.x1)
    for row in rows[1:]:
        run = run.extended(row)
    return run


def _column_counts(row: _Row, cuts: Sequence[float]) -> Counter[int]:
    """How many of the row's fragments fall in each column."""
    return Counter(bisect.bisect(cuts, (part.x0 + part.x1) / 2) for part in row.parts)


def _prose_columns(
    rows: Sequence[_Row], profile: Profile, width: float, body_size: float, depth: int
) -> list[Region] | None:
    """The rows as prose columns on their own gutters, or None."""
    if len(rows) < profile.column_min_lines:
        return None
    run = _run_from(rows)
    gutters = _gutters(run.free, run.left, run.right, width)
    return _columns(run, gutters, profile, body_size, depth) if gutters else None


def _sections(
    rows: Sequence[_Row], profile: Profile, body_size: float, depth: int = 0
) -> tuple[list[Region], bool]:
    """The rows' regions in reading order, and whether a section of prose columns was found."""
    width = profile.gutter_min_em * body_size
    regions: list[Region] = []
    plain: list[Line] = []
    found = False

    def flush() -> None:
        if plain:
            regions.append(Region("prose", tuple(plain)))
            plain.clear()

    i = 0
    while i < len(rows):
        run = _Run([rows[i]], rows[i].free, rows[i].line.x0, rows[i].line.x1)
        while i + len(run.rows) < len(rows):
            longer = run.extended(rows[i + len(run.rows)])
            if not _gutters(longer.free, longer.left, longer.right, width):
                break
            run = longer
        gutters = _gutters(run.free, run.left, run.right, width)
        if not gutters or len(run.rows) < profile.column_min_lines:
            plain.append(rows[i].line)
            i += 1
            continue
        cuts = [(lo + hi) / 2 for lo, hi in gutters]
        # A one-sided first row before a two-sided one ends the text above: a paragraph's short
        # last line, or a date set flush right.
        if (
            len(_column_counts(run.rows[0], cuts)) == 1
            and len(_column_counts(run.rows[1], cuts)) > 1
        ):
            plain.append(rows[i].line)
            i += 1
            continue
        flush()
        columns = _columns(run, gutters, profile, body_size, depth)
        if columns is not None:
            regions.extend(columns)
            found = True
            i += len(run.rows)
            continue
        cut, taken, held = _beside_a_table(
            run, cuts, profile, width=width, body_size=body_size, depth=depth
        )
        regions.extend(cut)
        found = found or held
        i += taken
    flush()
    return regions, found


def _beside_a_table(
    run: _Run,
    cuts: Sequence[float],
    profile: Profile,
    *,
    width: float,
    body_size: float,
    depth: int,
) -> tuple[list[Region], int, bool]:
    """A gutter section that is not prose columns, with prose columns cut from a table beside them.

    A busy row holds two fragments in one column, as a table row whose values share one side of
    the gutter does. The regions, how many of the run's rows they read, and whether prose columns
    were found.
    """
    busy = [k for k, row in enumerate(run.rows) if max(_column_counts(row, cuts).values()) > 1]
    if busy:
        head = _prose_columns(run.rows[: busy[0]], profile, width, body_size, depth)
        if head is not None:
            return head, busy[0], True
        tail = _prose_columns(run.rows[busy[-1] + 1 :], profile, width, body_size, depth)
        if tail is not None:
            before, _ = _sections(run.rows[: busy[-1] + 1], profile, body_size, depth)
            return [*before, *tail], len(run.rows), True
    return [Region("rows", tuple(row.line for row in run.rows))], len(run.rows), False


def _vertical(words: Sequence[Word]) -> list[Region]:
    """One rows region per maximal run of consecutive word ids, each one line in id order."""
    runs: list[list[Word]] = []
    for word in sorted(words, key=lambda w: w.id):
        if runs and runs[-1][-1].id + 1 == word.id:
            runs[-1].append(word)
        else:
            runs.append([word])
    return [Region("rows", (Line(tuple(run)),)) for run in runs]


def layout(words: Sequence[Word], profile: Profile, body_size: float) -> tuple[Region, ...]:
    """Split one page's content words into regions, in reading order."""
    horizontal = [w for w in words if w.horizontal]
    regions: list[Region] = []
    if horizontal:
        lo = min(w.bbox.x0 for w in horizontal)
        hi = max(w.bbox.x1 for w in horizontal)
        rows = []
        for line in group_lines(horizontal, profile):
            parts = fragments(line, profile)
            rows.append(_Row(line, parts, _free(parts, lo, hi)))
        regions, _ = _sections(rows, profile, body_size)
    return (*regions, *_vertical([w for w in words if not w.horizontal]))
