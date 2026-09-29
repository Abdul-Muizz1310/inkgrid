"""Lines, fragments, and the body size (docs/specs/04-text-pipeline.md section 2)."""

import statistics
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property

from inkgrid.model.config import Profile
from inkgrid.model.page import Word

# W3's join geometry (02-reader.md section 4), restated here since the core never imports the
# reader: a mark glued to a word (spec 13 section 5).
GLUE_GAP_MIN = -1.0
GLUE_GAP_MAX = 0.6
GLUE_OVERLAP = 0.3
EPS = 1e-6


@dataclass(frozen=True)
class Line:
    """Words that share a line, sorted by `x0`; every measure is derived from them."""

    words: tuple[Word, ...]

    def __post_init__(self) -> None:
        if not self.words:
            msg = "a line holds at least one word"
            raise ValueError(msg)

    @cached_property
    def top(self) -> float:
        """The highest word top."""
        return min(w.bbox.y0 for w in self.words)

    @cached_property
    def bottom(self) -> float:
        """The lowest word bottom."""
        return max(w.bbox.y1 for w in self.words)

    @cached_property
    def x0(self) -> float:
        """The leftmost word start."""
        return min(w.bbox.x0 for w in self.words)

    @cached_property
    def x1(self) -> float:
        """The rightmost word end."""
        return max(w.bbox.x1 for w in self.words)

    @cached_property
    def size(self) -> float:
        """The median font size of the line's words."""
        return statistics.median(w.size for w in self.words)

    @cached_property
    def bold(self) -> bool:
        """True when at least half the line's characters are in bold words."""
        total = sum(len(w.text) for w in self.words)
        return 2 * sum(len(w.text) for w in self.words if w.bold) >= total


def _centre(word: Word) -> float:
    return (word.bbox.y0 + word.bbox.y1) / 2


def _by_x(words: Sequence[Word]) -> tuple[Word, ...]:
    return tuple(sorted(words, key=lambda w: (w.bbox.x0, w.id)))


def _glued(left: Word, right: Word) -> bool:
    """True when `right` starts where `left` ends, overlapping it as W3 joins a word."""
    gap = right.bbox.x0 - left.bbox.x1
    if not GLUE_GAP_MIN - EPS <= gap <= GLUE_GAP_MAX + EPS:
        return False
    overlap = min(left.bbox.y1, right.bbox.y1) - max(left.bbox.y0, right.bbox.y0)
    smaller = min(left.bbox.y1 - left.bbox.y0, right.bbox.y1 - right.bbox.y0)
    return overlap >= GLUE_OVERLAP * smaller - EPS


def _marks_home(groups: list[list[Word]]) -> list[list[Word]]:
    """Each raised mark moved to the line of the value it is glued to (spec 13 section 5).

    MuPDF flags a mark superscript against its own line, so a flagged mark glued on its left to a
    value was read on that value's line; clustering by centre can put it on a line above.
    """
    home = {w.id: i for i, group in enumerate(groups) for w in group}
    for i, group in enumerate(groups):
        for mark in [w for w in group if w.superscript]:
            if any(_glued(w, mark) or _glued(mark, w) for w in group if w is not mark):
                continue
            value = next(
                (
                    w
                    for j, other in enumerate(groups)
                    if j != i
                    for w in other
                    if not w.superscript and _glued(w, mark)
                ),
                None,
            )
            if value is not None:
                home[mark.id] = home[value.id]
    moved: list[list[Word]] = [[] for _ in groups]
    for group in groups:
        for w in group:
            moved[home[w.id]].append(w)
    return [group for group in moved if group]


def group_lines(words: Sequence[Word], profile: Profile) -> tuple[Line, ...]:
    """Cluster words into lines by vertical overlap (L15), top to bottom."""
    if not words:
        return ()
    reach = max(w.bbox.y1 - w.bbox.y0 for w in words) / 2
    groups: list[list[Word]] = []
    extents: list[list[float]] = []
    active: list[int] = []
    for word in sorted(words, key=lambda w: (_centre(w), w.bbox.x0, w.id)):
        # Words arrive by centre, so a line ending above `centre - reach` can meet no later word.
        centre = _centre(word)
        active = [i for i in active if extents[i][1] >= centre - reach]
        height = word.bbox.y1 - word.bbox.y0
        for i in active:
            top, bottom = extents[i]
            overlap = min(bottom, word.bbox.y1) - max(top, word.bbox.y0)
            if overlap > profile.line_overlap * min(bottom - top, height):
                groups[i].append(word)
                extents[i] = [min(top, word.bbox.y0), max(bottom, word.bbox.y1)]
                break
        else:
            active.append(len(groups))
            groups.append([word])
            extents.append([word.bbox.y0, word.bbox.y1])
    lines = [Line(_by_x(group)) for group in _marks_home(groups)]
    return tuple(sorted(lines, key=lambda line: (line.top, line.x0)))


def fragments(line: Line, profile: Profile) -> tuple[Line, ...]:
    """The line split wherever a gap exceeds `fragment_gap_em` x the pair's larger size."""
    out: list[list[Word]] = [[line.words[0]]]
    for prev, word in zip(line.words, line.words[1:], strict=False):
        gap = word.bbox.x0 - prev.bbox.x1
        if gap > profile.fragment_gap_em * max(prev.size, word.size):
            out.append([word])
        else:
            out[-1].append(word)
    return tuple(Line(tuple(group)) for group in out)


def body_size(words: Sequence[Word]) -> float:
    """The size carrying the most characters, rounded to 0.5 pt; ties go to the smaller size."""
    if not words:
        msg = "body_size needs at least one word, and there are no words"
        raise ValueError(msg)
    chars: Counter[float] = Counter()
    for word in words:
        chars[round(word.size * 2) / 2] += len(word.text)
    return min(chars, key=lambda size: (-chars[size], size))
