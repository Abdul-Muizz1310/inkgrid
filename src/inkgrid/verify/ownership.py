"""Every ink character to one word, and each word against its ink (spec 10 sections 2 and 3).

Comparison happens at the character level, so a difference in word grouping between the two
engines cannot fake a defect: a word owns the characters its box contains, and holds or lacks each.
"""

import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from inkgrid.model.geometry import Rect
from inkgrid.model.page import Word
from inkgrid.verify.ink import REPLACEMENT, InkChar, InkPage

BAND = 20.0  # the height of the vertical bands words are indexed by, in points


@dataclass(frozen=True, slots=True)
class WordGap:
    """A word's characters that no ink answers, in word order."""

    word: Word
    missing: str


@dataclass(frozen=True, slots=True)
class PageOwnership:
    """Where each of a page's ink characters went.

    `owner` maps a character's index to the id of the word it pairs with. Every ink character is
    counted once: owned, in a lost run, outside, clipped, or a soft hyphen.
    """

    owner: Mapping[int, int]
    lost: tuple[tuple[InkChar, ...], ...]
    doubled: tuple[WordGap, ...]
    invented: tuple[WordGap, ...]
    outside: int
    clipped: int
    soft_hyphens: int
    unmapped: int

    @property
    def owned(self) -> int:
        """How many ink characters pair with a word character."""
        return len(self.owner)


def contains(box: Rect, x: float, y: float) -> bool:
    """Half-open containment; an axis of zero extent is closed (spec 10 section 2)."""
    in_x = box.x0 <= x <= box.x1 if box.x0 == box.x1 else box.x0 <= x < box.x1
    in_y = box.y0 <= y <= box.y1 if box.y0 == box.y1 else box.y0 <= y < box.y1
    return in_x and in_y


class _Index:
    """Words by the vertical bands their boxes reach, so a lookup never scans the page."""

    def __init__(self, words: Iterable[Word]) -> None:
        self._bands: defaultdict[int, list[Word]] = defaultdict(list)
        for word in sorted(words, key=lambda w: w.id):
            for band in range(math.floor(word.bbox.y0 / BAND), math.floor(word.bbox.y1 / BAND) + 1):
                self._bands[band].append(word)

    def containing(self, x: float, y: float) -> list[Word]:
        return [w for w in self._bands.get(math.floor(y / BAND), []) if contains(w.bbox, x, y)]


def _needs(need: Counter[str], ch: InkChar) -> bool:
    if need[ch.char] > 0 or need[REPLACEMENT] > 0:
        return True
    return ch.kind == "unmapped" and any(n > 0 for n in need.values())


def _take(need: Counter[str], ch: InkChar) -> None:
    for key in (ch.char, REPLACEMENT):
        if need[key] > 0:
            need[key] -= 1
            return
    if ch.kind == "unmapped":
        other = next((k for k, n in need.items() if n > 0), None)
        if other is not None:
            need[other] -= 1


@dataclass
class _Assignment:
    claimed: defaultdict[int, list[InkChar]]
    elsewhere: defaultdict[int, Counter[str]]  # characters a word contains that another took
    unowned: list[InkChar]


def _assign(page: InkPage, words: Sequence[Word]) -> _Assignment:
    """Pass 1 gives unambiguous characters; pass 2 gives contested ones to the word needing them."""
    index = _Index(words)
    need = {w.id: Counter(w.text) for w in words}
    out = _Assignment(defaultdict(list), defaultdict(Counter), [])
    pending: list[tuple[InkChar, list[Word]]] = []
    for ch in page.chars:
        if not ch.is_ink:
            continue
        candidates = [] if page.outside(ch) or ch.clipped else index.containing(*ch.center)
        if not candidates:
            out.unowned.append(ch)
        elif len(candidates) == 1:
            out.claimed[candidates[0].id].append(ch)
            _take(need[candidates[0].id], ch)
        else:
            pending.append((ch, candidates))
    for ch, candidates in pending:
        x, y = ch.center
        best = min(
            candidates,
            key=lambda w: (
                not _needs(need[w.id], ch),
                abs(w.bbox.center[1] - y),
                abs(w.bbox.center[0] - x),
                w.id,
            ),
        )
        out.claimed[best.id].append(ch)
        _take(need[best.id], ch)
        for other in candidates:
            if other is not best:
                out.elsewhere[other.id][ch.char] += 1
    return out


@dataclass
class _Comparison:
    owner: dict[int, int]
    surplus: list[InkChar]
    doubled: list[WordGap]
    invented: list[WordGap]
    unmapped: int = 0


def _pair(word: Word, chars: Sequence[InkChar], out: _Comparison) -> Counter[str]:
    """Section 3.1 steps 1-2: exact pairs, then unmapped wildcards; returns the unanswered."""
    remaining = Counter(word.text)
    leftover = []
    for ch in chars:
        if remaining[ch.char] > 0:
            remaining[ch.char] -= 1
            out.owner[ch.index] = word.id
            out.unmapped += ch.char == REPLACEMENT
        else:
            leftover.append(ch)
    for ch in leftover:
        key = next((k for k, n in remaining.items() if n > 0), None)
        if ch.kind == "unmapped" and key is not None:
            remaining[key] -= 1
        elif remaining[REPLACEMENT] > 0:
            remaining[REPLACEMENT] -= 1
        else:
            out.surplus.append(ch)
            continue
        out.owner[ch.index] = word.id
        out.unmapped += 1
    return remaining


def _gaps(word: Word, remaining: Counter[str], elsewhere: Counter[str], out: _Comparison) -> None:
    """Section 3.1 step 4: each unanswered character is doubled, or else invented."""
    doubled, invented = "", ""
    for c in word.text:
        if remaining[c] <= 0:
            continue
        remaining[c] -= 1
        if elsewhere[c] > 0:
            elsewhere[c] -= 1
            doubled += c
        else:
            invented += c
    if doubled:
        out.doubled.append(WordGap(word, doubled))
    if invented:
        out.invented.append(WordGap(word, invented))


def _runs(page: InkPage, lost: set[int]) -> tuple[tuple[InkChar, ...], ...]:
    """Lost characters with no other ink character between them, in PDFium's order."""
    runs: list[list[InkChar]] = []
    current: list[InkChar] = []
    for ch in page.chars:
        if not ch.is_ink:
            continue
        if ch.index in lost:
            current.append(ch)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return tuple(tuple(run) for run in runs)


def own_page(
    page: InkPage, words: Sequence[Word], *, clipped_chars: int, invisible_chars: int
) -> PageOwnership:
    """Assign and compare a page's ink (spec 10 sections 2, 3.1 and 3.2).

    `clipped_chars` and `invisible_chars` are the reader's counts for the page: they bound the
    outside-and-clipped class and the soft-hyphen class.
    """
    assignment = _assign(page, words)
    comparison = _Comparison({}, [], [], [])
    for word in sorted(words, key=lambda w: w.id):
        remaining = _pair(word, assignment.claimed.get(word.id, []), comparison)
        _gaps(word, remaining, assignment.elsewhere[word.id], comparison)
    outside = [ch for ch in assignment.unowned if page.outside(ch)]
    clipped = [ch for ch in assignment.unowned if ch.clipped and not page.outside(ch)]
    hidden = {ch.index for ch in (*outside, *clipped)}
    loose = [*assignment.unowned, *comparison.surplus]
    hyphens = [ch for ch in loose if ch.kind == "hyphen" and ch.index not in hidden]
    lost = [ch for ch in loose if ch.kind != "hyphen" and ch.index not in hidden]
    if len(outside) + len(clipped) > clipped_chars:
        lost += [*outside, *clipped]
        outside, clipped = [], []
    if len(hyphens) > invisible_chars:
        lost += hyphens
        hyphens = []
    return PageOwnership(
        owner=MappingProxyType(comparison.owner),
        lost=_runs(page, {ch.index for ch in lost}),
        doubled=tuple(comparison.doubled),
        invented=tuple(comparison.invented),
        outside=len(outside),
        clipped=len(clipped),
        soft_hyphens=len(hyphens),
        unmapped=comparison.unmapped,
    )
