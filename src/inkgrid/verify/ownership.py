"""Every ink character to one word, and each word against its ink (spec 10 sections 2 and 3).

Comparison happens at the character level, so a difference in word grouping between the two
engines cannot fake a defect: a word owns the characters its box contains, and holds or lacks each.
"""

import math
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from inkgrid.model.geometry import Rect
from inkgrid.model.page import Word
from inkgrid.verify.ink import REPLACEMENT, InkChar, InkPage

BAND = 20.0  # the height of the vertical bands words are indexed by, in points
LIGATURES = ("ffi", "ffl", "ff", "fi", "fl", "st")  # longest first (spec 11 section 2.1)
LIGATURE_POINTS = range(0xFB00, 0xFB07)
# An overprint copy: an owned character's code point, its box's size within this many points, and a
# centre within this fraction of its height (spec 13 section 1.3).
OVERPRINT_SIZE_TOL = 0.5
OVERPRINT_CENTRE = 0.1


@dataclass(frozen=True, slots=True)
class WordGap:
    """A word's characters that no ink answers, in word order."""

    word: Word
    missing: str


@dataclass(frozen=True, slots=True)
class Decode:
    """A word's glyphs the two engines decode differently: MuPDF's `read`, PDFium's `ink`."""

    word: Word
    read: str
    ink: str


@dataclass(frozen=True, slots=True)
class PageOwnership:
    """Where each of a page's ink characters went.

    `owner` maps a character's index to the id of the word it pairs with. Every ink character is
    counted once: owned, in a lost run, outside, clipped, a soft hyphen, or an overprint copy.
    """

    owner: Mapping[int, int]
    lost: tuple[tuple[InkChar, ...], ...]
    doubled: tuple[WordGap, ...]
    invented: tuple[WordGap, ...]
    outside: int
    clipped: int
    soft_hyphens: int
    unmapped: int
    ligatures: int = 0
    decoded: tuple[Decode, ...] = ()
    overprints: int = 0

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

    def overlapping(self, box: Rect) -> list[Word]:
        found: dict[int, Word] = {}
        for band in range(math.floor(box.y0 / BAND), math.floor(box.y1 / BAND) + 1):
            for w in self._bands.get(band, []):
                if w.bbox.intersects(box):
                    found[w.id] = w
        return sorted(found.values(), key=lambda w: w.id)


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


def _pick(ch: InkChar, candidates: Sequence[Word], need: dict[int, Counter[str]]) -> Word:
    x, y = ch.center
    return min(
        candidates,
        key=lambda w: (
            not _needs(need[w.id], ch),
            abs(w.bbox.center[1] - y),
            abs(w.bbox.center[0] - x),
            w.id,
        ),
    )


def _repair(
    contested: list[tuple[InkChar, list[Word], Word]], claimed: defaultdict[int, list[InkChar]]
) -> None:
    """Undo greedy choices (spec 11 section 2.3).

    A contested character moves from a word holding more of it than it needs to another word
    containing it that holds fewer, until nothing moves.
    """
    held: defaultdict[int, Counter[str]] = defaultdict(Counter)
    for word_id, chars in claimed.items():
        held[word_id].update(c.char for c in chars)
    moved = True
    while moved:
        moved = False
        for k, (ch, candidates, holder) in enumerate(contested):
            if held[holder.id][ch.char] <= holder.text.count(ch.char):
                continue
            short = next(
                (
                    w
                    for w in candidates
                    if w is not holder and held[w.id][ch.char] < w.text.count(ch.char)
                ),
                None,
            )
            if short is None:
                continue
            claimed[holder.id].remove(ch)
            claimed[short.id].append(ch)
            held[holder.id][ch.char] -= 1
            held[short.id][ch.char] += 1
            contested[k] = (ch, candidates, short)
            moved = True


def _assign(page: InkPage, words: Sequence[Word]) -> _Assignment:
    """Give each ink character to at most one word (spec 10 section 2, spec 11 section 2).

    Pass 1 gives unambiguous characters; pass 2 gives contested ones to the word needing them;
    repair undoes pass 2's greedy choices; a last pass offers the rest by overlap.
    """
    index = _Index(words)
    need = {w.id: Counter(w.text) for w in words}
    out = _Assignment(defaultdict(list), defaultdict(Counter), [])
    pending: list[tuple[InkChar, list[Word]]] = []
    for ch in page.chars:
        if not ch.is_ink:
            continue
        # An outside character is still offered to a word containing it: MuPDF keeps a glyph that
        # straddles the page edge. A clipped one never is (spec 10 section 2).
        candidates = [] if ch.clipped else index.containing(*ch.center)
        if not candidates:
            out.unowned.append(ch)
        elif len(candidates) == 1:
            out.claimed[candidates[0].id].append(ch)
            _take(need[candidates[0].id], ch)
        else:
            pending.append((ch, candidates))
    contested: list[tuple[InkChar, list[Word], Word]] = []
    for ch, candidates in pending:
        best = _pick(ch, candidates, need)
        out.claimed[best.id].append(ch)
        _take(need[best.id], ch)
        contested.append((ch, candidates, best))
    _repair(contested, out.claimed)
    for ch, candidates, holder in contested:
        for other in candidates:
            if other is not holder:
                out.elsewhere[other.id][ch.char] += 1
    held = {w.id: Counter(c.char for c in out.claimed.get(w.id, [])) for w in words}
    rest = []
    for ch in out.unowned:
        wanting = [
            w
            for w in index.overlapping(ch.box)
            if not ch.clipped and held[w.id][ch.char] < w.text.count(ch.char)
        ]
        if wanting:
            best = _pick(ch, wanting, need)
            out.claimed[best.id].append(ch)
            held[best.id][ch.char] += 1
        else:
            rest.append(ch)
    out.unowned = rest
    return out


@dataclass
class _Comparison:
    owner: dict[int, int]
    surplus: list[InkChar]
    doubled: list[WordGap]
    invented: list[WordGap]
    decoded: list[Decode]
    unmapped: int = 0
    ligatures: int = 0


def _ligature(word: Word, ch: InkChar, remaining: Counter[str]) -> bool:
    """Section 2.1 (spec 11): an unmapped or ligature glyph against the letters it draws."""
    if ord(ch.char) in LIGATURE_POINTS:
        spellings: tuple[str, ...] = (unicodedata.normalize("NFKC", ch.char),)
    elif ch.kind == "unmapped":
        spellings = LIGATURES
    else:
        return False
    for letters in spellings:
        need = Counter(letters)
        if letters in word.text and all(remaining[c] >= n for c, n in need.items()):
            remaining.subtract(need)
            return True
    return False


def _pair(
    word: Word, chars: Sequence[InkChar], out: _Comparison
) -> tuple[Counter[str], list[InkChar]]:
    """Section 3.1 steps 1-2 (spec 10): exact pairs, ligatures (spec 11), then unmapped wildcards.

    Returns the word characters no ink answered, and the word's ink no character answered.
    """
    remaining = Counter(word.text)
    leftover = []
    for ch in chars:
        if remaining[ch.char] > 0:
            remaining[ch.char] -= 1
            out.owner[ch.index] = word.id
            out.unmapped += ch.char == REPLACEMENT
        else:
            leftover.append(ch)
    rest = []
    for ch in leftover:
        if _ligature(word, ch, remaining):
            out.owner[ch.index] = word.id
            out.ligatures += 1
        else:
            rest.append(ch)
    surplus = []
    for ch in rest:
        key = next((k for k, n in remaining.items() if n > 0), None)
        if ch.kind == "unmapped" and key is not None:
            remaining[key] -= 1
        elif remaining[REPLACEMENT] > 0:
            remaining[REPLACEMENT] -= 1
        else:
            surplus.append(ch)
            continue
        out.owner[ch.index] = word.id
        out.unmapped += 1
    return remaining, surplus


def _gaps(
    word: Word,
    remaining: Counter[str],
    elsewhere: Counter[str],
    surplus: list[InkChar],
    out: _Comparison,
) -> None:
    """Section 3.1 step 4 (spec 10): each unanswered character is doubled, or else invented.

    As many invented characters as the word has unanswered ink glyphs are a decode disagreement
    (spec 11 section 2.4).
    """
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
    glyphs = sorted((ch for ch in surplus if ch.kind == "ink"), key=lambda ch: ch.box.x0)
    if invented and len(glyphs) == len(invented):
        out.decoded.append(Decode(word, invented, "".join(ch.char for ch in glyphs)))
        for ch in glyphs:
            out.owner[ch.index] = word.id
        surplus = [ch for ch in surplus if ch.kind != "ink"]
        invented = ""
    out.surplus.extend(surplus)
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


def _is_copy(ch: InkChar, owned: Sequence[InkChar]) -> bool:
    """True when an owned character of the same code point is drawn at `ch`'s place and size."""
    return any(
        abs(o.box.width - ch.box.width) <= OVERPRINT_SIZE_TOL
        and abs(o.box.height - ch.box.height) <= OVERPRINT_SIZE_TOL
        and math.dist(o.center, ch.center) <= OVERPRINT_CENTRE * o.box.height
        for o in owned
    )


def _overprints(
    page: InkPage, owner: Mapping[int, int], lost: Sequence[InkChar], counted: int
) -> set[int]:
    """The lost characters that are copies of owned ones, when no more than `counted` are."""
    owned: defaultdict[str, list[InkChar]] = defaultdict(list)
    for ch in page.chars:
        if ch.index in owner:
            owned[ch.char].append(ch)
    copies = {
        ch.index
        for ch in lost
        if ch.kind in {"ink", "unmapped"} and _is_copy(ch, owned.get(ch.char, ()))
    }
    return copies if len(copies) <= counted else set()


def own_page(
    page: InkPage,
    words: Sequence[Word],
    *,
    clipped_chars: int,
    invisible_chars: int,
    overprinted_chars: int = 0,
) -> PageOwnership:
    """Assign and compare a page's ink (spec 10 sections 2, 3.1 and 3.2; spec 13 section 1.3).

    `clipped_chars`, `invisible_chars` and `overprinted_chars` are the reader's counts for the
    page: they bound the outside-and-clipped class, the soft-hyphen class, and overprint copies.
    """
    assignment = _assign(page, words)
    comparison = _Comparison({}, [], [], [], [])
    for word in sorted(words, key=lambda w: w.id):
        remaining, surplus = _pair(word, assignment.claimed.get(word.id, []), comparison)
        _gaps(word, remaining, assignment.elsewhere[word.id], surplus, comparison)
    outside = [ch for ch in assignment.unowned if page.outside(ch)]
    clipped = [ch for ch in assignment.unowned if ch.clipped and not page.outside(ch)]
    hidden = {ch.index for ch in (*outside, *clipped)}
    loose = [*assignment.unowned, *comparison.surplus]
    hyphens = [ch for ch in loose if ch.kind == "hyphen" and ch.index not in hidden]
    lost = [ch for ch in loose if ch.kind != "hyphen" and ch.index not in hidden]
    copies = _overprints(page, comparison.owner, lost, overprinted_chars)
    lost = [ch for ch in lost if ch.index not in copies]
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
        ligatures=comparison.ligatures,
        decoded=tuple(comparison.decoded),
        overprints=len(copies),
    )
