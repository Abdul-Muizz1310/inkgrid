"""Chart evidence (docs/specs/14-tables-and-furniture.md section 6).

A plot box with ticks gives a gridder a grid, and a chart's labels stack like a table's rows. A
table candidate is refused when its extent holds bars in one proportion to the numbers they carry
(E1) or a numeric axis with a tick at every label (E2). Both tests are strict on purpose: a fee
table's shaded rows, equal fills, and tier numbers beside sub-row rules hold neither.
"""

import re
from collections.abc import Callable, Iterator, Sequence
from itertools import pairwise
from typing import Literal, assert_never

from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.geometry import Rect
from inkgrid.model.page import Rule, Word

type Evidence = Literal["bars", "axis"]

MIN_MARKS = 3  # bars, values, lengths, and axis labels
EDGE_TOL = 0.5  # pt: bars share a baseline and a thickness within this
LENGTH_APART = 1.0  # pt: two bar lengths are distinct when further apart than this
VALUE_REACH = 1.5  # x the word's size: a value's gap beyond its bar's far end
FIT_PT, FIT_SHARE = 1.0, 0.03  # |length - k * value| within the larger of these
LINE_TOL = 3.0  # pt: axis labels on one line or column, each centre this near the next
SPACING_PT, SPACING_SHARE = 1.5, 0.05  # evenly spaced: the gaps within the larger of these
STEP_SHARE = 1e-3  # an arithmetic progression: every step within this share of the first
TICK_AT = 1.5  # pt: a tick lies this near its label's centre
TICK_REACH = 2.0  # x the word's size: a tick's near end this near its label
WALL_TOL = 0.5  # pt

_NUMBER = re.compile(
    r"(?P<sign>[-+\u2212]?)[$\u20ac\u00a3]?"
    r"(?P<whole>[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)?(?:(?P<sep>[.,])(?P<part>[0-9]+))?%?"
)

# A bar's side: bars grow along x (True) or y, from their low edge (True) or their high one.
type _Side = tuple[bool, bool]
_SIDES: tuple[_Side, ...] = ((True, True), (True, False), (False, True), (False, False))


def number(text: str) -> float | None:
    """The value a numeric word prints (`1,400`, `1,4`, `(12.5%)`, `$3`), or None."""
    m = _NUMBER.fullmatch(text.strip("()"))
    if m is None or (m["whole"] is None and m["part"] is None):
        return None
    whole = m["whole"] or "0"
    if "," in whole and m["sep"] == ",":
        return None  # `1,400,5` is neither thousands nor a decimal comma
    value = float(whole.replace(",", "") + "." + (m["part"] or "0"))
    return -value if m["sign"] in {"-", "\u2212"} else value


def _meets(a: Rect, b: Rect) -> bool:
    return a.x0 <= b.x1 and b.x0 <= a.x1 and a.y0 <= b.y1 and b.y0 <= a.y1


def _bar(rect: Rect, side: _Side) -> tuple[float, float, float, float]:
    """The bar's baseline, far end, and its start and end across the baseline, on `side`."""
    along_x, low = side
    a0, a1, c0, c1 = (
        (rect.x0, rect.x1, rect.y0, rect.y1) if along_x else (rect.y0, rect.y1, rect.x0, rect.x1)
    )
    return (a0, a1, c0, c1) if low else (a1, a0, c0, c1)


def _clusters[T](items: Sequence[T], key: Callable[[T], float]) -> Iterator[list[T]]:
    """Runs of `items` whose keys lie within EDGE_TOL of their run's first."""
    run: list[T] = []
    for item in sorted(items, key=key):
        if run and key(item) - key(run[0]) > EDGE_TOL:
            yield run
            run = []
        run.append(item)
    if run:
        yield run


def _bar_groups(fills: Sequence[Rect], side: _Side) -> Iterator[list[Rect]]:
    """Fills sharing a baseline and a thickness on `side`, pairwise disjoint across it."""
    for level in _clusters(fills, lambda r: _bar(r, side)[0]):
        for group in _clusters(level, lambda r: _bar(r, side)[3] - _bar(r, side)[2]):
            if len(group) < MIN_MARKS:
                continue
            spans = sorted((_bar(r, side)[2], _bar(r, side)[3]) for r in group)
            reach = spans[0][1]
            for start, end in spans[1:]:
                if start < reach - EDGE_TOL:
                    break
                reach = max(reach, end)
            else:
                yield group


def _value(bar: Rect, side: _Side, words: Sequence[Word]) -> float | None:
    """The one positive number inside the bar or just beyond its far end, within its span."""
    base, far, c0, c1 = _bar(bar, side)
    along_x, low = side
    grows = 1.0 if low else -1.0
    found: list[float] = []
    for word in words:
        value = number(word.text)
        if value is None or value <= 0:
            continue
        cx, cy = word.bbox.center
        along, across = (cx, cy) if along_x else (cy, cx)
        extent = word.bbox.width if along_x else word.bbox.height
        beyond = (along - base) * grows
        if c0 <= across <= c1 and 0 <= beyond <= abs(far - base) + VALUE_REACH * word.size + (
            extent / 2
        ):
            found.append(value)
    return found[0] if len(found) == 1 else None


def _proportional(bars: Sequence[Rect], side: _Side, words: Sequence[Word]) -> bool:
    """Every bar pairs with its own number, and one factor fits them all.

    A bar with no number, or two, fails the group: a table's in-cell data bars pair only where a
    value sits near its bar's end (the final review's R4).
    """
    pairs: list[tuple[float, float]] = []
    for bar in bars:
        value = _value(bar, side, words)
        if value is None:
            return False
        base, far, _, _ = _bar(bar, side)
        pairs.append((abs(far - base), value))
    if len(pairs) < MIN_MARKS or len({v for _, v in pairs}) < MIN_MARKS:
        return False
    lengths = sorted(length for length, _ in pairs)
    if 1 + sum(1 for a, b in pairwise(lengths) if b - a > LENGTH_APART) < MIN_MARKS:
        return False
    k = sum(length for length, _ in pairs) / sum(v for _, v in pairs)
    return all(abs(length - k * v) <= max(FIT_PT, FIT_SHARE * length) for length, v in pairs)


def _bars(extent: Rect, words: Sequence[Word], fills: Sequence[Rect]) -> bool:
    """E1: at least 3 bars meeting the extent, in one proportion to the values they carry."""
    near = [f for f in fills if _meets(f, extent)]
    return any(
        _proportional(group, side, words)
        for side in _SIDES
        if len(near) >= MIN_MARKS
        for group in _bar_groups(near, side)
    )


def _divides(rule: Rule, label: Word, words: Sequence[Word], *, along_x: bool) -> bool:
    """Words lie along the rule on both of its sides: it divides rows (or columns), no tick."""
    reach = TICK_REACH * label.size
    sides: set[bool] = set()
    for word in words:
        if word.id == label.id:
            continue
        cx, cy = word.bbox.center
        along, across = (cy, cx) if along_x else (cx, cy)
        if rule.start <= along <= rule.end and 0 < abs(across - rule.at) <= reach:
            sides.add(across > rule.at)
    return len(sides) == 2  # noqa: PLR2004 - both sides


def _ticked(word: Word, rules: Sequence[Rule], words: Sequence[Word], *, along_x: bool) -> bool:
    """A tick: a rule perpendicular to the labels' line, ending near the word.

    No rule lies between them, and the rule divides no text along it: a sub-row rule beside a
    tier number is a row rule (the final review's R5).
    """
    b = word.bbox
    tick, wall = ("v", "h") if along_x else ("h", "v")
    at = b.center[0] if along_x else b.center[1]
    near, far = (b.y0, b.y1) if along_x else (b.x0, b.x1)
    for rule in rules:
        if rule.axis != tick or abs(rule.at - at) > TICK_AT:
            continue
        if rule.start >= far:
            lo, hi = far, rule.start
        elif rule.end <= near:
            lo, hi = rule.end, near
        else:
            continue  # the rule runs through the word: a strike, not a tick
        if hi - lo > TICK_REACH * word.size or _divides(rule, word, words, along_x=along_x):
            continue
        if not any(
            q.axis == wall and lo - WALL_TOL <= q.at <= hi + WALL_TOL and q.start <= at <= q.end
            for q in rules
        ):
            return True
    return False


def _progression(values: Sequence[float], gaps: Sequence[float]) -> bool:
    steps = [b - a for a, b in pairwise(values)]
    if steps[0] == 0 or any(abs(s - steps[0]) > STEP_SHARE * abs(steps[0]) + 1e-9 for s in steps):
        return False
    return max(gaps) - min(gaps) <= max(SPACING_PT, SPACING_SHARE * max(gaps))


def _axis(extent: Rect, words: Sequence[Word], rules: Sequence[Rule]) -> bool:
    """E2: at least 3 evenly spaced labels in arithmetic progression, each with its tick."""
    inside = [
        w
        for w in words
        if extent.x0 <= w.bbox.center[0] <= extent.x1 and extent.y0 <= w.bbox.center[1] <= extent.y1
    ]
    held = [(w, v) for w in inside if (v := number(w.text)) is not None]
    for along_x in (True, False):
        line, pos = (1, 0) if along_x else (0, 1)
        groups: list[list[tuple[Word, float]]] = []
        for w, v in sorted(held, key=lambda t: t[0].bbox.center[line]):
            if groups and w.bbox.center[line] - groups[-1][-1][0].bbox.center[line] < LINE_TOL:
                groups[-1].append((w, v))
            else:
                groups.append([(w, v)])
        for group in groups:
            if len(group) < MIN_MARKS:
                continue
            group.sort(key=lambda t: t[0].bbox.center[pos])
            gaps = [b[0].bbox.center[pos] - a[0].bbox.center[pos] for a, b in pairwise(group)]
            if _progression([v for _, v in group], gaps) and all(
                _ticked(w, rules, inside, along_x=along_x) for w, _ in group
            ):
                return True
    return False


def chart_evidence(
    extent: Rect, words: Sequence[Word], rules: Sequence[Rule], fills: Sequence[Rect]
) -> Evidence | None:
    """The evidence that a table candidate's extent holds a chart, or None (section 6).

    `words`, `rules`, and `fills` are the page's, in the extent's frame.
    """
    if _bars(extent, words, fills):
        return "bars"
    if _axis(extent, words, rules):
        return "axis"
    return None


def chart_left_as_text(evidence: Evidence, page: int) -> Finding:
    """The info finding for a table candidate refused as a chart, its words left for prose."""
    match evidence:
        case "bars":
            why = "its bars are in one proportion to the numbers they carry"
        case "axis":
            why = "it holds a numeric axis with a tick at every label"
        case _:
            assert_never(evidence)
    detail = f"a chart read as a table was left as text: {why}"
    return Finding.of(FindingCode.CHART_LEFT_AS_TEXT, detail, page=page)
