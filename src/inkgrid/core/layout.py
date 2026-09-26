"""Column sections and reading order (docs/specs/04-text-pipeline.md section 4).

A gutter alone does not make columns: the narrowest table columns are as close as a label and its
text (L19). Prose columns need a gutter that persists over several lines and prose on both sides;
everything else keeps row order, which is right for tables and hanging-indent lists.
"""

import bisect
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from inkgrid.core.lines import Line, fragments, group_lines
from inkgrid.model.config import Profile
from inkgrid.model.page import Word

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


def _columns(run: _Run, gutters: Sequence[Interval], profile: Profile) -> list[Region] | None:
    """One prose region per column, or None when the section is not prose columns."""
    cuts = [(lo + hi) / 2 for lo, hi in gutters]
    count = len(cuts) + 1
    parts: list[list[Line]] = [[] for _ in range(count)]
    lines: list[list[Line]] = [[] for _ in range(count)]
    for row in run.rows:
        words: list[list[Word]] = [[] for _ in range(count)]
        for part in row.parts:
            index = bisect.bisect(cuts, (part.x0 + part.x1) / 2)
            parts[index].append(part)
            words[index].extend(part.words)
        for index, column_words in enumerate(words):
            if column_words:
                lines[index].append(Line(tuple(column_words)))
    for column in parts:
        if len(column) < profile.column_min_lines:
            return None
        if sum(len(part.words) for part in column) / len(column) < profile.prose_min_words:
            return None
    return [Region("prose", tuple(column)) for column in lines]


def _run_from(rows: Sequence[_Row]) -> _Run:
    run = _Run([rows[0]], rows[0].free, rows[0].line.x0, rows[0].line.x1)
    for row in rows[1:]:
        run = run.extended(row)
    return run


def _column_counts(row: _Row, cuts: Sequence[float]) -> Counter[int]:
    """How many of the row's fragments fall in each column."""
    return Counter(bisect.bisect(cuts, (part.x0 + part.x1) / 2) for part in row.parts)


def _prose_columns(rows: Sequence[_Row], profile: Profile, width: float) -> list[Region] | None:
    """The rows as prose columns on their own gutters, or None."""
    if len(rows) < profile.column_min_lines:
        return None
    run = _run_from(rows)
    gutters = _gutters(run.free, run.left, run.right, width)
    return _columns(run, gutters, profile) if gutters else None


def _sections(rows: Sequence[_Row], profile: Profile, body_size: float) -> list[Region]:
    width = profile.gutter_min_em * body_size
    regions: list[Region] = []
    plain: list[Line] = []

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
        columns = _columns(run, gutters, profile)
        if columns is not None:
            regions.extend(columns)
            i += len(run.rows)
            continue
        # Not prose columns: cut away a table beside them. A busy row holds two fragments in one
        # column, as a table row whose values share one side of the gutter does.
        busy = [k for k, row in enumerate(run.rows) if max(_column_counts(row, cuts).values()) > 1]
        head = _prose_columns(run.rows[: busy[0]], profile, width) if busy else None
        if head is not None:
            regions.extend(head)
            i += busy[0]
            continue
        tail = _prose_columns(run.rows[busy[-1] + 1 :], profile, width) if busy else None
        if tail is not None:
            regions.extend(_sections(run.rows[: busy[-1] + 1], profile, body_size))
            regions.extend(tail)
        else:
            regions.append(Region("rows", tuple(row.line for row in run.rows)))
        i += len(run.rows)
    flush()
    return regions


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
        regions = _sections(rows, profile, body_size)
    return (*regions, *_vertical([w for w in words if not w.horizontal]))
