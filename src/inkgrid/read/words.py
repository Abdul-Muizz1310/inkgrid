"""Build words from characters (pure). Rules W1-W8 of `docs/specs/02-reader.md` section 4.

A word is a maximal run of word characters within one span. Across a span boundary within one line
it continues only when nothing separates the two runs and both share their superscript and hidden
states: a font change mid-word stays one word, and `$0.40` followed by a raised `2` stays two.

A span is hidden when its fill alpha is 0 or it is neither filled nor stroked (render modes 3 and 7,
alpha-0 fills). Render modes 4-6 come back twice, the visible span and a clip copy; the copy is
dropped so no word is doubled (W7). A word drawn again at the same place (a banner painted twice,
fake bold, stroke then fill) is read once, its copy's characters counted (W8, spec 13 section 1).
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
# A run this much smaller than the next, its box bottom this much (of the next size) higher, is a
# mark glued to the word it opens (PHLX's `1A surcharge`): MuPDF flags nothing at a line's start.
MARK_SMALLER = 0.92
MARK_RAISED = 0.2
DIRECTION_TOL = 1e-3
EPS = 1e-6
# A copy's box edges lie within this much of its size of the kept word's (W8): copies measured
# 0.042 em apart at most, legitimate same-text neighbours 0.166 em at least (spec 13 section 0).
OVERPRINT_EM = 0.1

SUPERSCRIPT = 1
ITALIC = 2
BOLD = 16
CHAR_BOLD = 8
CHAR_FILLED = 16
CHAR_STROKED = 32
CHAR_CLIPPED = 64
BOX_DIGITS = 2

ZERO_WIDTH_SPACE = "\u200b"
REPLACEMENT = "\ufffd"
INVISIBLE_CATEGORIES = frozenset({"Cc", "Cf", "Co", "Cn"})


class _Kind(Enum):
    SPACE = auto()
    INVISIBLE = auto()
    SURROGATE = auto()
    WORD = auto()


def _classify(cp: str) -> _Kind:
    if cp.isspace() or cp == ZERO_WIDTH_SPACE:
        return _Kind.SPACE
    category = unicodedata.category(cp)
    if category == "Cs":
        return _Kind.SURROGATE
    if category in INVISIBLE_CATEGORIES:
        return _Kind.INVISIBLE
    return _Kind.WORD


def _is_clip_copy(span: RawSpan) -> bool:
    return bool(span.char_flags & CHAR_CLIPPED) and span.alpha == 0


def _signature(span: RawSpan) -> tuple[tuple[str, Box], ...]:
    return tuple(
        (
            ch.c,
            (
                round(ch.bbox[0], BOX_DIGITS),
                round(ch.bbox[1], BOX_DIGITS),
                round(ch.bbox[2], BOX_DIGITS),
                round(ch.bbox[3], BOX_DIGITS),
            ),
        )
        for ch in span.chars
    )


def _is_hidden(span: RawSpan) -> bool:
    return span.alpha == 0 or not (span.char_flags & (CHAR_FILLED | CHAR_STROKED))


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


def _can_join(prev: _Token, box: Box, *, size: float, superscript: bool, hidden: bool) -> bool:
    if not prev.horizontal or prev.superscript != superscript or prev.hidden != hidden:
        return False
    small_mark = prev.dominant().size <= MARK_SMALLER * size
    if small_mark and box[3] - prev.box[3] > MARK_RAISED * size:
        return False  # a raised mark opening the word (W3, spec 09 section 1.3)
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
    overprinted_chars: int = 0


_Identity = tuple[str, str, float, bool, bool, bool]


def _identity(word: Word) -> _Identity:
    return (word.text, word.font, word.size, word.hidden, word.horizontal, word.superscript)


def _covers(kept: Rect, copy: Rect, tolerance: float) -> bool:
    return (
        abs(kept.x0 - copy.x0) <= tolerance + EPS
        and abs(kept.y0 - copy.y0) <= tolerance + EPS
        and abs(kept.x1 - copy.x1) <= tolerance + EPS
        and abs(kept.y1 - copy.y1) <= tolerance + EPS
    )


def _read_once(words: Sequence[Word], type3_fonts: frozenset[str]) -> tuple[list[Word], int]:
    """The words with every copy of an earlier kept word dropped, and the copies' characters (W8).

    A copy has the kept word's text, font, size, and states, and each box edge within
    OVERPRINT_EM of its size. A U+FFFD or Type 3 word is never a copy: pictures share codes.
    """
    kept: list[Word] = []
    boxes: dict[_Identity, list[Rect]] = {}
    dropped = 0
    for word in words:
        key = _identity(word)
        comparable = REPLACEMENT not in word.text and word.font not in type3_fonts
        if comparable and any(
            _covers(box, word.bbox, OVERPRINT_EM * word.size) for box in boxes.get(key, ())
        ):
            dropped += len(word.text)
            continue
        kept.append(word)
        if comparable:
            boxes.setdefault(key, []).append(word.bbox)
    return kept, dropped


def build_words(
    lines: Sequence[RawLine],
    page: int,
    first_id: int,
    *,
    type3_fonts: frozenset[str] = frozenset(),
) -> WordsOut:
    """Turn a page's raw lines into words numbered from `first_id`, in `rawdict` order.

    `type3_fonts` names the page's Type 3 fonts, as PyMuPDF names their spans.
    """
    tokens: list[_Token] = []
    invisible = 0
    span_id = 0
    drawn = {_signature(s) for line in lines for s in line.spans if not _is_clip_copy(s)}
    for line in lines:
        horizontal = _is_horizontal(line.direction)
        carry: _Token | None = None
        for span in line.spans:
            if _is_clip_copy(span) and _signature(span) in drawn:
                continue
            span_id += 1
            superscript = bool(span.flags & SUPERSCRIPT)
            hidden = _is_hidden(span)
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
                    text = REPLACEMENT if kind is _Kind.SURROGATE else cp
                    if current is None:
                        joins = (
                            at_start
                            and carry is not None
                            and _can_join(
                                carry,
                                char.bbox,
                                size=span.size,
                                superscript=superscript,
                                hidden=hidden,
                            )
                        )
                        if joins and carry is not None:
                            current = carry
                        else:
                            current = _Token(superscript, hidden, horizontal)
                            tokens.append(current)
                    current.add(text, char.bbox, span_id, span)
                    at_start = False
            carry = current
    built = [_to_word(t, first_id + i, page) for i, t in enumerate(tokens)]
    once, overprinted = _read_once(built, type3_fonts)
    words = tuple(w.model_copy(update={"id": first_id + i}) for i, w in enumerate(once))
    unmapped = sum(w.text.count(REPLACEMENT) for w in words)
    hidden_chars = sum(len(w.text) for w in words if w.hidden)
    return WordsOut(words, invisible, unmapped, hidden_chars, overprinted)
