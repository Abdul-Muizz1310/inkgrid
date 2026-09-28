"""The table checks and value fidelity (docs/specs/10-verify.md sections 4 and 5).

A table is checked in its grid's frame: every character's centre is turned into the frame, and each
cell's rectangle comes from the grid's bands. Every box a defect reports is back in the page's
unrotated frame, where the document's own boxes are.
"""

import math
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from inkgrid.model.document import Cell, Document, Table
from inkgrid.model.geometry import Rect, Rotation, turn_rect, unturn_rect
from inkgrid.model.verification import Anchor, Defect, DefectCode
from inkgrid.verify.ink import InkChar, InkPage, InkRule, Point

Home = tuple[str, Anchor | None]
"""Where a word is bound: its block's id, and its cell's anchor when the block is a table."""

CROSS_MARGIN = 1.0
EDGE = 2.0
LINE_OVERLAP = 0.5
DIAGONAL = (15.0, 75.0)  # degrees from the horizontal that a watermark runs at
BAND = 20.0


def homes_of(doc: Document) -> dict[int, Home]:
    """Every word's block, and its cell inside a table."""
    out: dict[int, Home] = {}
    for block in doc.blocks:
        if isinstance(block, Table):
            for cell in block.grid.cells:
                for word_id in cell.word_ids:
                    out[word_id] = (block.id, (cell.row, cell.col))
        else:
            for word_id in block.word_ids:
                out[word_id] = (block.id, None)
    return out


def _inside(box: Rect, x: float, y: float) -> bool:
    return box.x0 <= x < box.x1 and box.y0 <= y < box.y1


class CellIndex:
    """Cell rectangles by the vertical bands they reach; `homes` lists every one holding a point."""

    def __init__(self, rects: Sequence[Rect]) -> None:
        self._bands: defaultdict[int, list[int]] = defaultdict(list)
        self._rects = rects
        for i, rect in enumerate(rects):
            for band in range(math.floor(rect.y0 / BAND), math.floor(rect.y1 / BAND) + 1):
                self._bands[band].append(i)

    def homes(self, x: float, y: float) -> list[int]:
        """The indexes of every rectangle holding the point, half-open."""
        return [
            i for i in self._bands.get(math.floor(y / BAND), []) if _inside(self._rects[i], x, y)
        ]


@dataclass(frozen=True, slots=True)
class _Frame:
    rotation: Rotation
    width: float
    height: float

    def box(self, box: Rect) -> Rect:
        return turn_rect(box, self.rotation, self.width, self.height) if self.rotation else box

    def unbox(self, box: Rect) -> Rect:
        return unturn_rect(box, self.rotation, self.width, self.height)

    def rule(self, rule: InkRule) -> InkRule:
        if not self.rotation:
            return rule
        if rule.axis == "h":
            line = Rect(rule.start, rule.at, rule.end, rule.at)
        else:
            line = Rect(rule.at, rule.start, rule.at, rule.end)
        t = self.box(line)
        if t.width >= t.height:
            return InkRule("h", t.y0, t.x0, t.x1)
        return InkRule("v", t.x0, t.y0, t.y1)


def reading_sequence(
    chars: Iterable[InkChar], frame: Rotation, width: float, height: float
) -> list[InkChar]:
    """The verifier's reading order (L15): lines by vertical overlap, then left to right."""
    turn = _Frame(frame, width, height)
    boxed = sorted(((ch, turn.box(ch.box)) for ch in chars), key=lambda t: t[1].center[1])
    lines: list[list[tuple[InkChar, Rect]]] = []
    for ch, box in boxed:
        if lines:
            top = min(b.y0 for _, b in lines[-1])
            bottom = max(b.y1 for _, b in lines[-1])
            overlap = min(box.y1, bottom) - max(box.y0, top)
            if overlap > LINE_OVERLAP * min(box.height, bottom - top):
                lines[-1].append((ch, box))
                continue
        lines.append([(ch, box)])
    return [ch for line in lines for ch, _ in sorted(line, key=lambda t: t[1].x0)]


def _cuts(rule: InkRule, rect: Rect, points: Sequence[Point]) -> bool:
    """Spec 10 section 4.4: the rule crosses the cell's interior, spans it, and divides its ink."""
    if rule.axis == "v":
        lo, hi, first, last, along = rect.x0, rect.x1, rect.y0, rect.y1, 0
    else:
        lo, hi, first, last, along = rect.y0, rect.y1, rect.x0, rect.x1, 1
    if not (lo + CROSS_MARGIN < rule.at < hi - CROSS_MARGIN):
        return False
    if rule.start > first + EDGE or rule.end < last - EDGE:
        return False
    sides = [p[along] for p in points]
    return any(v < rule.at for v in sides) and any(v > rule.at for v in sides)


@dataclass(frozen=True, slots=True)
class _Where:
    """Where a cell's defect is: its page, table, anchor, and box in the unrotated frame."""

    page: int
    block: str
    cell: Anchor
    bbox: Rect

    def defect(self, code: DefectCode, text: str, detail: str) -> Defect:
        return Defect(
            code=code,
            page=self.page,
            block=self.block,
            cell=self.cell,
            text=text,
            bbox=self.bbox,
            detail=detail,
        )


@dataclass(frozen=True, slots=True)
class TableResult:
    """One table's defects and advisories, and how many of its characters overflow their cell."""

    defects: tuple[Defect, ...]
    advisories: tuple[Defect, ...]
    overflow: int
    overlay: int = 0


@dataclass
class _Placed:
    """Each character's centre in the frame and home cell, and the ink sorted to cells and words."""

    centre: dict[int, Point]
    home: dict[int, Anchor]
    by_cell: defaultdict[Anchor, list[InkChar]]
    by_word: defaultdict[int, list[InkChar]]
    others: defaultdict[int, list[InkChar]]  # ink of words outside the table, by word
    orphans: list[InkChar]
    doubles: list[InkChar]


def _place(table: Table, page: InkPage, owner: Mapping[int, int], turn: _Frame) -> _Placed:
    cells = table.grid.cells
    rects = [table.grid.cell_rect(c) for c in cells]
    index = CellIndex(rects)
    live = [rect for cell, rect in zip(cells, rects, strict=True) if not cell.carried]
    extent = Rect.union_all(live) if live else None
    words = {w for c in cells for w in c.word_ids}
    out = _Placed({}, {}, defaultdict(list), defaultdict(list), defaultdict(list), [], [])
    for ch in page.chars:
        if not ch.is_ink:
            continue
        x, y = turn.box(ch.box).center
        out.centre[ch.index] = (x, y)
        word = owner.get(ch.index)
        if word in words:
            out.by_word[word].append(ch)
        elif word is not None:
            out.others[word].append(ch)
        found = index.homes(x, y)
        if not found:
            if extent is not None and _inside(extent, x, y):
                out.orphans.append(ch)
        elif len(found) > 1:
            out.doubles.append(ch)
        else:
            anchor = (cells[found[0]].row, cells[found[0]].col)
            out.home[ch.index] = anchor
            out.by_cell[anchor].append(ch)
    return out


def _spread(
    code: DefectCode, table: Table, page: int, chars: Sequence[InkChar], what: str
) -> Defect:
    return Defect(
        code=code,
        page=page,
        block=table.id,
        text="".join(c.char for c in chars),
        bbox=Rect.union_all(c.box for c in chars),
        detail=f"{len(chars)} ink characters inside the table's extent lie {what}",
    )


@dataclass(frozen=True, slots=True)
class Words:
    """What the checks read about the document's words: each one's home and text, by id."""

    homes: Mapping[int, Home]
    texts: Mapping[int, str]
    horizontal: Mapping[int, bool]

    @classmethod
    def of(cls, doc: Document) -> "Words":
        """The document's words, indexed."""
        texts = {w.id: w.text for w in doc.words}
        return cls(homes_of(doc), texts, {w.id: w.horizontal for w in doc.words})


def _separates(rule: InkRule, inside: Sequence[Point], point: Point) -> bool:
    """True when the rule lies between the point and every one of `inside`, and spans the point."""
    along, across = (1, 0) if rule.axis == "v" else (0, 1)
    if not rule.start <= point[along] <= rule.end:
        return False
    beyond = point[across]
    return all(p[across] < rule.at < beyond for p in inside) or all(
        beyond < rule.at < p[across] for p in inside
    )


def _crosses_rule(
    chars: Sequence[InkChar],
    anchor: Anchor,
    placed: _Placed,
    page: InkPage,
    rules: Sequence[InkRule],
) -> bool:
    """Section 4.3: a placed word's overflow runs across a drawn rule as two texts, not one.

    Text that runs on over a border, unbroken, is overflow. Two texts glued into one word show at
    the rule: PDFium breaks the word there, or digits sit on both sides of it.
    """
    inside = [c for c in chars if placed.home.get(c.index) == anchor]
    points = [placed.centre[c.index] for c in inside]
    crossed = [
        c
        for c in chars
        if placed.home.get(c.index) != anchor
        and any(_separates(r, points, placed.centre[c.index]) for r in rules)
    ]
    if not crossed:
        return False
    first, last = min(c.index for c in chars), max(c.index for c in chars)
    broken = any(not ch.is_ink for ch in page.span(first, last))
    digits = [any(unicodedata.category(c.char) == "Nd" for c in part) for part in (inside, crossed)]
    return broken or all(digits)


def _diagonal(chars: Sequence[InkChar]) -> bool:
    """True when a word's glyphs run at 15 to 75 degrees: a watermark, not a turned label.

    MuPDF's `horizontal` flag cannot tell 45 from 90 degrees; PDFium's glyph positions can.
    """
    if len(chars) < 2:  # noqa: PLR2004 - one glyph has no direction
        return False
    (x0, y0), (x1, y1) = chars[0].center, chars[-1].center
    angle = math.degrees(math.atan2(abs(y1 - y0), abs(x1 - x0)))
    return DIAGONAL[0] < angle < DIAGONAL[1]


def _problems(
    cell: Cell,
    placed: _Placed,
    owner: Mapping[int, int],
    words: Words,
    context: tuple[Table, InkPage, Sequence[InkRule]],
) -> tuple[list[str], int, int]:
    """Section 4.3: the cell's misplaced words and foreign ink, and its words' overflow."""
    table, page, rules = context
    anchor = (cell.row, cell.col)
    problems, overflow = [], 0
    for word_id in cell.word_ids:
        chars = placed.by_word.get(word_id, [])
        inside = sum(1 for c in chars if placed.home.get(c.index) == anchor)
        text = words.texts[word_id]
        if chars and 2 * inside <= len(chars):
            problems.append(f"{text!r} has {inside} of its {len(chars)} characters in the cell")
        elif inside < len(chars) and _crosses_rule(chars, anchor, placed, page, rules):
            problems.append(f"{text!r} runs across a drawn rule into another cell")
        else:
            overflow += len(chars) - inside
    foreign = []
    overlay = 0
    for ch in placed.by_cell.get(anchor, []):
        other = owner.get(ch.index)
        if other is None or words.homes[other][0] == table.id:
            continue
        if (
            table.grid.frame == 0
            and not words.horizontal[other]
            and _diagonal(placed.others[other])
        ):
            overlay += 1  # a diagonal watermark over a table (spec 11 section 3.2)
        else:
            foreign.append(ch.char)
    if foreign:
        problems.append(f"it holds ink of another block: {''.join(foreign)!r}")
    return problems, overflow, overlay


def table_checks(
    table: Table, page: InkPage, owner: Mapping[int, int], words: Words
) -> TableResult:
    """ORPHAN, DOUBLE, TEXT, VRULE and HRULE defects, and ORDER advisories (section 4)."""
    grid = table.grid
    turn = _Frame(grid.frame, page.width, page.height)
    placed = _place(table, page, owner, turn)
    defects: list[Defect] = []
    advisories: list[Defect] = []
    if placed.orphans:
        defects.append(_spread(DefectCode.ORPHAN, table, page.number, placed.orphans, "in no cell"))
    if placed.doubles:
        defects.append(
            _spread(DefectCode.DOUBLE, table, page.number, placed.doubles, "in two cells")
        )
    rules = [turn.rule(r) for r in page.rules]
    overflow = overlay = 0
    for cell in grid.cells:
        anchor = (cell.row, cell.col)
        rect = grid.cell_rect(cell)
        where = _Where(page.number, table.id, anchor, turn.unbox(rect))
        problems, spilled, over = _problems(cell, placed, owner, words, (table, page, rules))
        overflow += spilled
        overlay += over
        if problems:
            defects.append(where.defect(DefectCode.TEXT, cell.text, "; ".join(problems)))
            continue
        own = [c for w in cell.word_ids for c in placed.by_word.get(w, [])]
        want = "".join(words.texts[w] for w in cell.word_ids)
        if own and "\ufffd" not in want and all(c.kind != "unmapped" for c in own):
            seq = "".join(
                c.char for c in reading_sequence(own, grid.frame, page.width, page.height)
            )
            if seq != want:
                detail = f"the ink reads {seq!r}"
                advisories.append(where.defect(DefectCode.ORDER, want, detail))
        points = [placed.centre[c.index] for c in own if placed.home.get(c.index) == anchor]
        if len(points) < 2:  # noqa: PLR2004 - two characters are the least a rule can divide
            continue
        for axis, code in (("v", DefectCode.VRULE), ("h", DefectCode.HRULE)):
            rule = next((r for r in rules if r.axis == axis and _cuts(r, rect, points)), None)
            if rule is not None:
                detail = f"a drawn {axis} rule at {rule.at:.2f} divides the cell's ink"
                defects.append(where.defect(code, cell.text, detail))
    return TableResult(tuple(defects), tuple(advisories), overflow, overlay)


def value_checks(page: InkPage, owner: Mapping[int, int], words: Words) -> list[Defect]:
    """VALUE defects: a value token bound to more than one block or cell (section 5)."""
    out: list[Defect] = []
    token: list[InkChar] = []
    for ch in (*page.chars, None):
        if ch is not None and ch.is_ink and not (token and _apart(token[-1], ch)):
            token.append(ch)
            continue
        if any(unicodedata.category(c.char) == "Nd" for c in token):
            defect = _value(token, page.number, owner, words)
            if defect is not None:
                out.append(defect)
        token = [ch] if ch is not None and ch.is_ink else []
    return out


def _apart(prev: InkChar, ch: InkChar) -> bool:
    """Spec 11 section 3.1: PDFium runs far-apart characters together; a token ends at a gap.

    The gap is the distance between the two boxes in any direction, so a run keeps together
    whichever way its text goes: across the page, down a landscape page, or upside down.
    """
    a, b = prev.box, ch.box
    dx = max(0.0, b.x0 - a.x1, a.x0 - b.x1)
    dy = max(0.0, b.y0 - a.y1, a.y0 - b.y1)
    size = max(a.width, a.height, b.width, b.height)
    return math.hypot(dx, dy) > size / 2


def _value(
    token: Sequence[InkChar], page: int, owner: Mapping[int, int], words: Words
) -> Defect | None:
    owners = [owner.get(c.index) for c in token]
    if any(w is None for w in owners):
        return None  # unowned ink is LOST, reported once
    homes = {words.homes[w] for w in owners if w is not None}
    blocks = sorted({block for block, _ in homes})
    anchors = sorted({anchor for _, anchor in homes if anchor is not None})
    text = "".join(c.char for c in token)
    if len(blocks) > 1:
        detail = f"the value {text!r} is split across blocks {', '.join(blocks)}"
    elif len(anchors) > 1:
        cells = ", ".join(f"({r}, {c})" for r, c in anchors)
        detail = f"the value {text!r} is split across cells {cells}"
    else:
        return None
    return Defect(
        code=DefectCode.VALUE,
        page=page,
        block=blocks[0] if len(blocks) == 1 else None,
        text=text,
        bbox=Rect.union_all(c.box for c in token),
        detail=detail,
    )
