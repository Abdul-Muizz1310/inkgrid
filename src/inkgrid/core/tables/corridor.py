"""Unruled tables from whitespace corridors (docs/specs/07-unruled-tables.md).

Columns come from the whitespace between the value rows' pieces, which stays put however a column is
aligned; every row votes on where each boundary sits; and two values never share a cell (L2, L11).
"""

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property
from itertools import pairwise

from inkgrid.core.lexicon import is_strong_value, is_value
from inkgrid.core.lines import Line, fragments
from inkgrid.model.config import Profile
from inkgrid.model.page import Word

MAX_QUALIFIED_TOKENS = 4  # `$5,000 per month`: a value and a few words qualifying it
WRAP_RATIO = 0.35  # a line closer than this share of the block's typical gap wraps its row
MIN_WRAP = 0.5  # pt: the wrap threshold is never smaller


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
