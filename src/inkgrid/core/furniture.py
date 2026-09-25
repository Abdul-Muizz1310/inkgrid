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

from inkgrid.core.lines import Line, group_lines
from inkgrid.model.config import Profile
from inkgrid.model.page import PageModel

Role = Literal["header", "footer", "page_number"]
DIGITS = re.compile(r"\d+")
THREE_LETTERS = re.compile(r"[^\W\d_]{3}")
ROMAN = re.compile(r"m{0,3}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})", re.IGNORECASE)
ROMAN_MAX = 6


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


def _keyed(page: PageModel, profile: Profile) -> list[_Keyed]:
    lines = group_lines([w for w in page.words if w.horizontal], profile)
    if not lines:
        return []
    top = min(line.top for line in lines)
    bottom = max(line.bottom for line in lines)
    band = profile.furniture_band * (bottom - top)
    return [
        _Keyed(page, line, line_key(line), not top + band < _centre(line) < bottom - band)
        for line in lines
    ]


def _role(key: str, line: Line, page: PageModel) -> Role:
    if not _has_letter(key):
        return "page_number"
    return "header" if _centre(line) < page.height / 2 else "footer"


def find_furniture(pages: Sequence[PageModel], profile: Profile) -> FoundFurniture:
    """Mark the lines whose key recurs at the page edges on enough pages."""
    keyed = [k for page in pages for k in _keyed(page, profile)]
    seen: defaultdict[str, set[int]] = defaultdict(set)
    starts: defaultdict[str, list[float]] = defaultdict(list)
    for k in keyed:
        if k.candidate:
            seen[k.key].add(k.page.number)
            starts[k.key].append(k.line.x0)
    need = max(2, math.ceil(profile.furniture_share * len(pages)))
    keys = {key for key, on in seen.items() if len(on) >= need}
    lines = []
    for k in keyed:
        if k.key not in keys:
            continue
        if not _has_letter(k.key):
            column = statistics.median(starts[k.key])
            if not k.candidate or abs(k.line.x0 - column) > profile.furniture_x_tol:
                continue
        lines.append(FurnitureLine(k.page.number, k.line, _role(k.key, k.line, k.page), k.key))
    return FoundFurniture(tuple(lines), frozenset(w.id for f in lines for w in f.line.words))
