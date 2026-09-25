"""Running headers, footers, and page numbers (docs/specs/04-text-pipeline.md section 3).

Decisions are per line, never per block (L9): a line is furniture only when its whole key recurs.
"""

import math
import re
import statistics
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from inkgrid.core.lines import Line, fragments, group_lines
from inkgrid.model.config import Profile
from inkgrid.model.page import PageModel

Role = Literal["header", "footer", "page_number"]
DIGITS = re.compile(r"\d+")
THREE_LETTERS = re.compile(r"[^\W\d_]{3}")
ROMAN = re.compile(r"m{0,3}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})", re.IGNORECASE)
ROMAN_MAX = 6
MAX_FRAGMENTS = 3  # a line of this many fragments is a table row, never furniture


@dataclass(frozen=True, slots=True)
class FurnitureLine:
    """One line marked as furniture, with its page, role, and key."""

    page: int
    line: Line
    role: Role
    key: str


@dataclass(frozen=True, slots=True)
class FoundFurniture:
    """Every furniture line of a document, in page order, and the ids of their words."""

    lines: tuple[FurnitureLine, ...]
    word_ids: frozenset[int]


@dataclass(frozen=True, slots=True)
class _Keyed:
    page: PageModel
    line: Line
    key: str
    candidate: bool


def _is_roman(text: str) -> bool:
    return 0 < len(text) <= ROMAN_MAX and ROMAN.fullmatch(text) is not None


def _is_number(text: str) -> bool:
    return text == "#" or _is_roman(text)


def _has_letter(text: str) -> bool:
    return any(ch.isalpha() for ch in text)


def line_key(line: Line) -> str:
    """The line's text with digit runs masked and edge page numbers stripped."""
    tokens = [DIGITS.sub("#", w.text) for w in line.words]
    if not any(_has_letter(t) and not _is_roman(t) for t in tokens):
        return " ".join("#" if _is_roman(t) else t for t in tokens)
    if any(THREE_LETTERS.search(t) for t in tokens):
        while _is_number(tokens[0]):
            tokens.pop(0)
        while _is_number(tokens[-1]):
            tokens.pop()
    return " ".join(tokens)


def _centre(line: Line) -> float:
    return statistics.median((w.bbox.y0 + w.bbox.y1) / 2 for w in line.words)


def _band(line: Line, top: float, bottom: float, band: float) -> Literal["top", "bottom"] | None:
    centre = _centre(line)
    if centre <= top + band:
        return "top"
    if centre >= bottom - band:
        return "bottom"
    return None


def _keyed(page: PageModel, profile: Profile) -> list[_Keyed]:
    lines = group_lines([w for w in page.words if w.horizontal], profile)
    if not lines:
        return []
    top = min(line.top for line in lines)
    bottom = max(line.bottom for line in lines)
    band = profile.furniture_band * (bottom - top)
    placed = [(line, line_key(line), _band(line, top, bottom, band)) for line in lines]

    def stacked(line: Line, key: str, where: str) -> bool:
        """The key recurs in this band at this position: rows of a table, not furniture."""
        return any(
            other is not line and k == key and w == where and _aligned(other, line, tol)
            for other, k, w in placed
        )

    tol = profile.furniture_x_tol
    return [
        _Keyed(
            page,
            line,
            key,
            where is not None
            and len(fragments(line, profile)) < MAX_FRAGMENTS
            and not stacked(line, key, where),
        )
        for line, key, where in placed
    ]


def _anchors(line: Line) -> tuple[float, float, float]:
    """Where a line sits across the page: its start, its end, and its centre."""
    return (line.x0, line.x1, (line.x0 + line.x1) / 2)


def _aligned(a: Line, b: Line, tol: float) -> bool:
    return any(abs(p - q) <= tol for p, q in zip(_anchors(a), _anchors(b), strict=True))


def _in_column(k: _Keyed, others: Sequence[_Keyed], need: int, tol: float) -> bool:
    """True when some anchor of the line recurs within `tol` on at least `need` pages."""
    mine = _anchors(k.line)
    for i in range(3):
        pages = {o.page.number for o in others if abs(_anchors(o.line)[i] - mine[i]) <= tol}
        if len(pages) >= need:
            return True
    return False


def _role(key: str, line: Line, page: PageModel) -> Role:
    if not _has_letter(key):
        return "page_number"
    return "header" if _centre(line) < page.height / 2 else "footer"


def find_furniture(pages: Sequence[PageModel], profile: Profile) -> FoundFurniture:
    """Mark the lines whose key recurs at the page edges on enough pages."""
    keyed = [k for page in pages for k in _keyed(page, profile)]
    seen: defaultdict[str, set[int]] = defaultdict(set)
    candidates: defaultdict[str, list[_Keyed]] = defaultdict(list)
    for k in keyed:
        if k.candidate:
            seen[k.key].add(k.page.number)
            candidates[k.key].append(k)
    need = max(2, math.ceil(profile.furniture_share * len(pages)))
    keys = {key for key, on in seen.items() if len(on) >= need}
    lines = []
    for k in keyed:
        if k.key not in keys:
            continue
        if not _has_letter(k.key) and not (
            k.candidate and _in_column(k, candidates[k.key], need, profile.furniture_x_tol)
        ):
            continue
        lines.append(FurnitureLine(k.page.number, k.line, _role(k.key, k.line, k.page), k.key))
    return FoundFurniture(tuple(lines), frozenset(w.id for f in lines for w in f.line.words))
