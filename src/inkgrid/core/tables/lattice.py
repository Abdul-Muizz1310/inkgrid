"""Ruled grids to proto tables (docs/specs/06-ruled-tables.md section 5).

A word belongs to the cell whose half-open rectangle holds its centre, so assignment is a partition
by construction. A grid is a table only when it has two rows, two columns, and two cells with words:
a box around a paragraph or a furniture label is not a table. A frame around a table reads as its
core, a grid over an accepted table is none, an accepted grid splits at the page's own rules, and no
diagonal word is a cell's (spec 14 sections 2, 4, 7).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from inkgrid.core.tables.proto import (
    ProtoCell,
    ProtoTable,
    cell_lines,
    table_roles,
)
from inkgrid.core.tables.shape import GridShape, grid_shape
from inkgrid.model.config import Profile
from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.geometry import Rect, Rotation
from inkgrid.model.page import PageModel, Word

MIN_ROWS = MIN_COLS = MIN_FILLED = 2
CROSS_TOLERANCE = 1.0  # pt a word may overhang its cell's left or right edge
# Grids sharing only a border overlap by at most shape.SNAP (0.5 pt); more is a grid over a table.
OVERLAP_MIN = 1.0
# The page's rules on one line merge within these; a merged rule splits a cell when it lies this
# far inside the cell's edges across it and reaches this near both ends along it. Every value is
# stricter than the verifier's VRULE and HRULE tests (spec 14 section 2).
MERGE_AT = 0.25
MERGE_GAP = 0.5
SPLIT_INSIDE = 1.5
SPLIT_REACH = 1.5
CORE_TOL = 0.5


@dataclass(frozen=True, slots=True)
class _Line:
    axis: str
    at: float
    start: float
    end: float


@dataclass(frozen=True, slots=True)
class TableStage:
    """What the table stage made of one page: tables, the words they claim, and findings."""

    tables: tuple[ProtoTable, ...]
    claimed: frozenset[int]
    findings: tuple[Finding, ...]


def _ruled_layout(cells: Sequence[ProtoCell], n_cols: int, profile: Profile) -> bool:
    """True when every column is running text: a frame ruled around columns of prose, not a table.

    A column is running text when its single-column cells hold prose by layout's test and one of
    them holds a column's worth of lines (twice `column_min_lines`). Table cells of text are short.
    """
    for col in range(n_cols):
        own = [c for c in cells if c.cell.col == col and c.cell.col_span == 1]
        lines = [line for c in own for line in c.lines]
        if len(lines) < profile.column_min_lines:
            return False
        if sum(len(line.words) for line in lines) / len(lines) < profile.prose_min_words:
            return False
        if max(len(c.lines) for c in own) < 2 * profile.column_min_lines:
            return False
    return True


def _crossing(cells: Sequence[ProtoCell], bbox: Rect) -> int:
    """Words overhanging their cell's left or right edge into a neighbouring cell."""
    count = 0
    for cell in cells:
        rect = cell.cell.rect
        for word in cell.words:
            left = rect.x0 > bbox.x0 and word.bbox.x0 < rect.x0 - CROSS_TOLERANCE
            right = rect.x1 < bbox.x1 and word.bbox.x1 > rect.x1 + CROSS_TOLERANCE
            count += left or right
    return count


def _bbox(rects: Sequence[Rect]) -> Rect:
    return Rect(
        min(r.x0 for r in rects),
        min(r.y0 for r in rects),
        max(r.x1 for r in rects),
        max(r.y1 for r in rects),
    )


def _overlaps(a: Rect, b: Rect) -> bool:
    across = min(a.x1, b.x1) - max(a.x0, b.x0)
    down = min(a.y1, b.y1) - max(a.y0, b.y0)
    return across >= OVERLAP_MIN and down >= OVERLAP_MIN


def _in_core(rects: Sequence[Rect], core: Rect | None, words: Sequence[Word]) -> list[Rect]:
    """A frame's cells cut to its core, when nothing but blank margin lies beside the core."""
    if core is None:
        return list(rects)
    box = _bbox(rects)
    for w in words:
        x, y = w.bbox.center
        beside = box.x0 <= x < core.x0 or core.x1 <= x < box.x1
        if beside and core.y0 <= y < core.y1:
            return list(rects)  # a real table's side columns hold words; a frame's margins do not
    inside = [
        r
        for r in rects
        if r.x0 >= core.x0 - CORE_TOL
        and r.y0 >= core.y0 - CORE_TOL
        and r.x1 <= core.x1 + CORE_TOL
        and r.y1 <= core.y1 + CORE_TOL
    ]
    return inside or list(rects)


def _merged(page: PageModel) -> list[_Line]:
    """The page's rules merged along each line.

    A line holds the rules whose `at` lies within MERGE_AT of its first; along it, rules join where
    they touch or leave a gap of at most MERGE_GAP.
    """
    out: list[_Line] = []
    for axis in ("h", "v"):
        rules = sorted((r for r in page.rules if r.axis == axis), key=lambda r: (r.at, r.start))
        k = 0
        while k < len(rules):
            at = rules[k].at
            line = [r for r in rules[k:] if r.at - at <= MERGE_AT]
            k += len(line)
            spans = sorted((r.start, r.end) for r in line)
            lo, hi = spans[0]
            for start, end in spans[1:]:
                if start <= hi + MERGE_GAP:
                    hi = max(hi, end)
                else:
                    out.append(_Line(axis, at, lo, hi))
                    lo, hi = start, end
            out.append(_Line(axis, at, lo, hi))
    return out


def _split(rect: Rect, lines: Sequence[_Line], words: Sequence[Word]) -> list[Rect] | None:
    """The cell's two halves at the first rule dividing it and its words, or None."""
    held = [w.bbox.center for w in words if rect.contains_point(*w.bbox.center)]
    for line in lines:
        if line.axis == "v":
            lo, hi, start, end, index = rect.x0, rect.x1, rect.y0, rect.y1, 0
        else:
            lo, hi, start, end, index = rect.y0, rect.y1, rect.x0, rect.x1, 1
        if not lo + SPLIT_INSIDE < line.at < hi - SPLIT_INSIDE:
            continue
        if line.start > start + SPLIT_REACH or line.end < end - SPLIT_REACH:
            continue
        before = any(p[index] < line.at for p in held)
        after = any(p[index] >= line.at for p in held)
        if not (before and after):
            continue
        if line.axis == "v":
            return [
                Rect(rect.x0, rect.y0, line.at, rect.y1),
                Rect(line.at, rect.y0, rect.x1, rect.y1),
            ]
        return [Rect(rect.x0, rect.y0, rect.x1, line.at), Rect(rect.x0, line.at, rect.x1, rect.y1)]
    return None


def _split_at_rules(
    rects: Sequence[Rect], lines: Sequence[_Line], words: Sequence[Word]
) -> list[Rect]:
    """The cells split, repeatedly, wherever one of the page's rules divides a cell's words."""
    pending, out = list(rects), []
    while pending:
        rect = pending.pop()
        halves = _split(rect, lines, words) if lines else None
        if halves is None:
            out.append(rect)
        else:
            pending.extend(halves)
    return sorted(out, key=lambda r: (r.y0, r.x0))


def _cells(shape: GridShape, words: Sequence[Word], profile: Profile) -> list[ProtoCell]:
    return [
        ProtoCell(
            cell,
            cell_lines([w for w in words if cell.rect.contains_point(*w.bbox.center)], profile),
        )
        for cell in shape.cells
    ]


def lattice_tables(
    page: PageModel,
    grids: Sequence[Sequence[Rect]],
    words: Sequence[Word],
    profile: Profile,
    *,
    frame: Rotation,
    read: bool,
    cores: Sequence[Rect | None] = (),
) -> TableStage:
    """The page's ruled grids as proto tables, over its content words (all in one frame).

    `read` says whether the lattice reader read this page; `cores` gives each grid's frame core,
    when it has one. Grids are taken smallest first, so a grid over an accepted table is none, and
    the tables come out in the grids' order.
    """
    found: dict[int, ProtoTable] = {}
    accepted: list[Rect] = []
    claimed: set[int] = set()
    findings: list[Finding] = []
    if read and not grids:
        detail = "the page has rules both ways, but Camelot returned no grid"
        findings.append(Finding.of(FindingCode.LATTICE_DISAGREES, detail, page=page.number))
    claimable = [w for w in words if not w.diagonal]  # a watermark is no cell's (spec 14 s. 7)
    lines = _merged(page)
    cut = [
        _in_core(rects, cores[i] if i < len(cores) else None, words) if rects else []
        for i, rects in enumerate(grids)
    ]
    order = sorted(
        (i for i, rects in enumerate(cut) if rects),
        key=lambda i: (_bbox(cut[i]).width * _bbox(cut[i]).height, i),
    )
    for i in order:
        rects = cut[i]
        if any(_overlaps(_bbox(rects), box) for box in accepted):
            continue  # a frame or panel grid over a table already read (spec 14 section 4.1)
        shape = grid_shape(rects)
        if shape is None:
            detail = "a lattice grid whose cells do not tile it was dropped"
            findings.append(Finding.of(FindingCode.LATTICE_FAILED, detail, page=page.number))
            continue
        free = [w for w in claimable if w.id not in claimed]
        cells = _cells(shape, free, profile)
        n_rows, n_cols = len(shape.row_edges) - 1, len(shape.col_edges) - 1
        if n_rows < MIN_ROWS or n_cols < MIN_COLS or sum(1 for c in cells if c.words) < MIN_FILLED:
            continue
        if _ruled_layout(cells, n_cols, profile):
            continue
        held = [w for c in cells for w in c.words]
        split = _split_at_rules(rects, lines, held)
        if len(split) != len(rects):
            reshaped = grid_shape(split)
            if reshaped is not None:
                shape = reshaped
                cells = _cells(shape, held, profile)
                n_rows, n_cols = len(shape.row_edges) - 1, len(shape.col_edges) - 1
        header, banners, text_only = table_roles(cells, n_rows)
        table = ProtoTable(
            page.number, shape, tuple(cells), header, banners, frame, "lattice", text_only
        )
        crossing = _crossing(cells, table.bbox)
        if crossing:
            detail = f"{crossing} word{'s' if crossing > 1 else ''} cross a drawn column rule"
            findings.append(Finding.of(FindingCode.WORD_CROSSES_RULE, detail, page=page.number))
        found[i] = table
        accepted.append(_bbox(rects))
        claimed |= {w.id for w in table.words}
    tables = tuple(found[i] for i in sorted(found))
    return TableStage(tables, frozenset(claimed), tuple(findings))
