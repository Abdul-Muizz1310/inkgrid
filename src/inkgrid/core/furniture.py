"""Running headers, footers, and page numbers (docs/specs/04-text-pipeline.md section 3).

Decisions are per line, never per block (L9): a line is furniture only when its whole key recurs.
A line inside a ruled table is table content, and furniture runs from the page's edge
(docs/specs/14-tables-and-furniture.md section 8).
"""

import bisect
import math
import re
import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Self

from inkgrid.core.lines import Line, fragments, group_lines
from inkgrid.core.tables.lattice import MIN_COLS, MIN_FILLED, MIN_ROWS
from inkgrid.core.tables.shape import GridShape, grid_shape
from inkgrid.model.config import Profile
from inkgrid.model.geometry import Rect
from inkgrid.model.page import PageModel, Word

Role = Literal["header", "footer", "page_number"]
type PageGrids = Mapping[int, Sequence[Sequence[Rect]]]
"""Each page's ruled grids by page number: every grid's cells, in the page's own frame."""
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
    tabled: bool


type _Slots = dict[tuple[int, int], int]


def _cell(shape: GridShape, slots: _Slots, word: Word) -> int | None:
    """The cell whose half-open rectangle holds the word's centre, as the lattice stage reads it."""
    x, y = word.bbox.center
    row = bisect.bisect_right(shape.row_edges, y) - 1
    col = bisect.bisect_right(shape.col_edges, x) - 1
    return slots.get((row, col))


@dataclass(frozen=True, slots=True)
class _Table:
    """A ruled grid the lattice stage could accept, and the ids of the words each cell holds."""

    shape: GridShape
    slots: _Slots
    held: tuple[frozenset[int], ...]

    @classmethod
    def of(cls, cells: Sequence[Rect], words: Sequence[Word]) -> Self | None:
        shape = grid_shape(cells)
        if shape is None:
            return None
        if len(shape.row_edges) - 1 < MIN_ROWS or len(shape.col_edges) - 1 < MIN_COLS:
            return None
        slots = {
            (r, c): i
            for i, cell in enumerate(shape.cells)
            for r in range(cell.row, cell.row + cell.row_span)
            for c in range(cell.col, cell.col + cell.col_span)
        }
        held: list[set[int]] = [set() for _ in shape.cells]
        for word in words:
            index = _cell(shape, slots, word)
            if index is not None:
                held[index].add(word.id)
        return cls(shape, slots, tuple(frozenset(ids) for ids in held))

    def holds(self, line: Line) -> bool:
        """S1: every word of the line lies in a cell, and at least 2 other cells hold a word."""
        homes = {_cell(self.shape, self.slots, w) for w in line.words}
        if None in homes:
            return False
        others = sum(1 for i, ids in enumerate(self.held) if ids and i not in homes)
        return others >= MIN_FILLED


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


def _keyed(page: PageModel, profile: Profile, tables: Sequence[_Table]) -> list[_Keyed]:
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
    tabled = [any(t.holds(line) for t in tables) for line, _, _ in placed]
    base = [
        where is not None
        and not table
        and len(fragments(line, profile)) < MAX_FRAGMENTS
        and not stacked(line, key, where)
        for (line, key, where), table in zip(placed, tabled, strict=True)
    ]

    def from_edge(line: Line, where: str | None) -> bool:
        """S2: every line between this one and its band's page edge is a candidate too."""
        if where == "top":
            return all(
                ok for (o, _, _), ok in zip(placed, base, strict=True) if _centre(o) < line.top
            )
        return all(
            ok for (o, _, _), ok in zip(placed, base, strict=True) if _centre(o) > line.bottom
        )

    return [
        _Keyed(page, line, key, ok and from_edge(line, where), table)
        for (line, key, where), ok, table in zip(placed, base, tabled, strict=True)
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


def find_furniture(
    pages: Sequence[PageModel], profile: Profile, *, grids: PageGrids | None = None
) -> FoundFurniture:
    """Mark the lines whose key recurs at the page edges on enough pages.

    `grids` are the pages' ruled grids in each page's frame: a line inside one that could be a
    table is never furniture (S1).
    """
    keyed: list[_Keyed] = []
    for page in pages:
        cells = (grids or {}).get(page.number, ())
        tables = [t for grid in cells if (t := _Table.of(grid, page.words)) is not None]
        keyed += _keyed(page, profile, tables)
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
        if k.key not in keys or k.tabled:
            continue
        if not _has_letter(k.key) and not (
            k.candidate and _in_column(k, candidates[k.key], need, profile.furniture_x_tol)
        ):
            continue
        lines.append(FurnitureLine(k.page.number, k.line, _role(k.key, k.line, k.page), k.key))
    return FoundFurniture(tuple(lines), frozenset(w.id for f in lines for w in f.line.words))
