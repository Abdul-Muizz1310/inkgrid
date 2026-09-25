"""Build words from characters (pure). Rules W1-W6 of `docs/specs/02-reader.md` section 4.

A word is a maximal run of word characters within one span. Across a span boundary within one line
it continues only when nothing separates the two runs and both share their superscript and hidden
states: a font change mid-word stays one word, and `$0.40` followed by a raised `2` stays two.
"""

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum, auto

from inkgrid.model.geometry import Rect
from inkgrid.model.page import Word
from inkgrid.read.raw import Box, RawLine, RawSpan

JOIN_GAP_MAX = 0.6
JOIN_GAP_MIN = -1.0
JOIN_OVERLAP = 0.3
DIRECTION_TOL = 1e-3
EPS = 1e-6

SUPERSCRIPT = 1
ITALIC = 2
BOLD = 16
CHAR_BOLD = 8
CHAR_FILLED = 16
CHAR_STROKED = 32

ZERO_WIDTH_SPACE = "\u200b"
REPLACEMENT = "\ufffd"
INVISIBLE_CATEGORIES = frozenset({"Cc", "Cf", "Co", "Cn"})


class _Kind(Enum):
    SPACE = auto()
    INVISIBLE = auto()
    WORD = auto()


def _classify(cp: str) -> _Kind:
    if cp.isspace() or cp == ZERO_WIDTH_SPACE:
        return _Kind.SPACE
    if unicodedata.category(cp) in INVISIBLE_CATEGORIES:
        return _Kind.INVISIBLE
    return _Kind.WORD


@dataclass
class _Token:
    superscript: bool
    hidden: bool
    horizontal: bool
    text: list[str] = field(default_factory=list)
    box: list[float] = field(default_factory=list)
    span_counts: dict[int, int] = field(default_factory=dict)
    spans: dict[int, RawSpan] = field(default_factory=dict)

    def add(self, cp: str, box: Box, span_id: int, span: RawSpan) -> None:
        self.text.append(cp)
        if self.box:
            self.box = [
                min(self.box[0], box[0]),
                min(self.box[1], box[1]),
                max(self.box[2], box[2]),
                max(self.box[3], box[3]),
            ]
        else:
            self.box = list(box)
        self.span_counts[span_id] = self.span_counts.get(span_id, 0) + 1
        self.spans[span_id] = span

    def dominant(self) -> RawSpan:
        """The span contributing the most characters; ties go to the earliest."""
        best = max(self.span_counts.items(), key=lambda item: (item[1], -item[0]))[0]
        return self.spans[best]


def _can_join(prev: _Token, box: Box, *, superscript: bool, hidden: bool) -> bool:
    if not prev.horizontal or prev.superscript != superscript or prev.hidden != hidden:
        return False
    gap = box[0] - prev.box[2]
    if not JOIN_GAP_MIN - EPS <= gap <= JOIN_GAP_MAX + EPS:
        return False
    overlap = min(prev.box[3], box[3]) - max(prev.box[1], box[1])
    smaller = min(prev.box[3] - prev.box[1], box[3] - box[1])
    return overlap >= JOIN_OVERLAP * smaller - EPS


def _is_horizontal(direction: tuple[float, float]) -> bool:
    dx, dy = direction
    return abs(dx - 1.0) < DIRECTION_TOL and abs(dy) < DIRECTION_TOL


def _to_word(token: _Token, word_id: int, page: int) -> Word:
    span = token.dominant()
    font_lower = span.font.lower()
    return Word(
        id=word_id,
        page=page,
        bbox=Rect(*token.box),
        text="".join(token.text),
        size=round(span.size, 2),
        font=span.font,
        bold=bool(span.flags & BOLD) or bool(span.char_flags & CHAR_BOLD) or "bold" in font_lower,
        italic=bool(span.flags & ITALIC) or "italic" in font_lower or "oblique" in font_lower,
        superscript=token.superscript,
        hidden=token.hidden,
        horizontal=token.horizontal,
    )


@dataclass(frozen=True, slots=True)
class WordsOut:
    """The words of one page, and the character counts the page model reports."""

    words: tuple[Word, ...]
    invisible_chars: int
    unmapped_chars: int
    hidden_chars: int


def build_words(lines: Sequence[RawLine], page: int, first_id: int) -> WordsOut:
    """Turn a page's raw lines into words numbered from `first_id`, in `rawdict` order."""
    tokens: list[_Token] = []
    invisible = 0
    span_id = 0
    for line in lines:
        horizontal = _is_horizontal(line.direction)
        carry: _Token | None = None
        for span in line.spans:
            span_id += 1
            superscript = bool(span.flags & SUPERSCRIPT)
            hidden = not (span.char_flags & (CHAR_FILLED | CHAR_STROKED))
            current: _Token | None = None
            at_start = True
            for char in span.chars:
                for cp in char.c:
                    kind = _classify(cp)
                    if kind is _Kind.SPACE:
                        if cp == ZERO_WIDTH_SPACE:
                            invisible += 1
                        current = carry = None
                        at_start = False
                        continue
                    if kind is _Kind.INVISIBLE:
                        invisible += 1
                        continue
                    if current is None:
                        joins = (
                            at_start
                            and carry is not None
                            and _can_join(carry, char.bbox, superscript=superscript, hidden=hidden)
                        )
                        if joins and carry is not None:
                            current = carry
                        else:
                            current = _Token(superscript, hidden, horizontal)
                            tokens.append(current)
                    current.add(cp, char.bbox, span_id, span)
                    at_start = False
            carry = current
    words = tuple(_to_word(t, first_id + i, page) for i, t in enumerate(tokens))
    unmapped = sum(w.text.count(REPLACEMENT) for w in words)
    hidden_chars = sum(len(w.text) for w in words if w.hidden)
    return WordsOut(words, invisible, unmapped, hidden_chars)
