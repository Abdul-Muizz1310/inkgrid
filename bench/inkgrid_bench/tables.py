"""The normalized table every adapter writes (spec 12 section 3.1), and its JSON form."""

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

Box = tuple[float, float, float, float]
ROTATIONS = (0, 90, 180, 270)
EDGE_TOL = 1.0  # points: cell edges closer than this are one grid line


@dataclass(frozen=True, slots=True)
class NCell:
    """A cell: its anchor, its span, its text, and whether the tool marks it a header."""

    row: int
    col: int
    rows: int = 1
    cols: int = 1
    text: str = ""
    header: bool = False


@dataclass(frozen=True, slots=True)
class NTable:
    """A table on a page: its box (PDF points, origin at the page box's top left) and its cells.

    The cells tile the grid: every position is covered by exactly one cell.
    """

    page: int
    bbox: Box
    cells: tuple[NCell, ...]

    def __post_init__(self) -> None:
        seen: set[tuple[int, int]] = set()
        for cell in self.cells:
            for r in range(cell.row, cell.row + cell.rows):
                for c in range(cell.col, cell.col + cell.cols):
                    if (r, c) in seen:
                        msg = f"position ({r}, {c}) is covered twice"
                        raise ValueError(msg)
                    seen.add((r, c))
        rows, cols = self.n_rows, self.n_cols
        if len(seen) != rows * cols:
            msg = f"the cells cover {len(seen)} of {rows} x {cols} positions"
            raise ValueError(msg)

    @property
    def n_rows(self) -> int:
        """How many rows the cells reach."""
        return max((c.row + c.rows for c in self.cells), default=0)

    @property
    def n_cols(self) -> int:
        """How many columns the cells reach."""
        return max((c.col + c.cols for c in self.cells), default=0)

    @classmethod
    def filled(cls, *, page: int, bbox: Box, cells: Sequence[NCell]) -> "NTable":
        """The table with every position no cell covers filled by an empty cell."""
        covered = {
            (r, c)
            for cell in cells
            for r in range(cell.row, cell.row + cell.rows)
            for c in range(cell.col, cell.col + cell.cols)
        }
        rows = max((c.row + c.rows for c in cells), default=0)
        cols = max((c.col + c.cols for c in cells), default=0)
        empty = [NCell(r, c) for r in range(rows) for c in range(cols) if (r, c) not in covered]
        ordered = sorted([*cells, *empty], key=lambda c: (c.row, c.col))
        return cls(page=page, bbox=bbox, cells=tuple(ordered))


@dataclass(frozen=True, slots=True)
class NPage:
    """A page's box in PDF user space (the CropBox clipped to the MediaBox) and its rotation.

    Tables are placed in the unrotated box, with the origin at its top-left corner.
    """

    box: Box
    rotation: int

    def __post_init__(self) -> None:
        if self.rotation not in ROTATIONS:
            msg = f"a page rotation of {self.rotation}; /Rotate is a multiple of 90"
            raise ValueError(msg)

    @property
    def width(self) -> float:
        """The box's width in points."""
        return self.box[2] - self.box[0]

    @property
    def height(self) -> float:
        """The box's height in points."""
        return self.box[3] - self.box[1]

    def to_user(self, x: float, y: float) -> tuple[float, float]:
        """A point of the top-left frame in PDF user space (origin at the bottom left)."""
        return (x + self.box[0], self.box[3] - y)

    @property
    def shown_size(self) -> tuple[float, float]:
        """The page's width and height as it displays, turned by its rotation."""
        if self.rotation in (90, 270):
            return (self.height, self.width)
        return (self.width, self.height)

    def to_shown(self, x: float, y: float) -> tuple[float, float]:
        """A point of the unrotated top-left frame in the displayed top-left frame.

        /Rotate turns the page clockwise (PDF 32000-1 section 7.7.3.3): at 90 degrees the
        unrotated top-left corner displays at the top right.
        """
        w, h = self.width, self.height
        match self.rotation:
            case 0:
                return (x, y)
            case 90:
                return (h - y, x)
            case 180:
                return (w - x, h - y)
            case _:  # 270, by __post_init__
                return (y, w - x)

    def from_shown(self, sx: float, sy: float) -> tuple[float, float]:
        """A point of the displayed top-left frame in the unrotated top-left frame."""
        w, h = self.width, self.height
        match self.rotation:
            case 0:
                return (sx, sy)
            case 90:
                return (sy, h - sx)
            case 180:
                return (w - sx, h - sy)
            case _:  # 270, by __post_init__
                return (w - sy, sx)

    def _icdar_frame(self) -> None:
        if self.rotation and (self.box[0], self.box[1]) != (0.0, 0.0):
            msg = f"a turned page with an offset box {self.box} has no ICDAR frame"
            raise ValueError(msg)

    def to_icdar(self, x: float, y: float) -> tuple[float, float]:
        """A point in ICDAR-2013's frame: PDF user space, and a turned page as it displays, y up.

        Its ground truth measures a /Rotate 90 page in the turned frame (practice eu-015 reaches
        x = 745 on a page 595 points wide); no ICDAR page is turned with an offset box.
        """
        if not self.rotation:
            return self.to_user(x, y)
        self._icdar_frame()
        sx, sy = self.to_shown(x, y)
        return (sx, self.shown_size[1] - sy)

    def from_icdar(self, ix: float, iy: float) -> tuple[float, float]:
        """A point of ICDAR-2013's frame in the unrotated top-left frame."""
        if not self.rotation:
            return (ix - self.box[0], self.box[3] - iy)
        self._icdar_frame()
        return self.from_shown(ix, self.shown_size[1] - iy)


@dataclass(frozen=True, slots=True)
class NDocument:
    """One tool's reading of one PDF; `error` is set when it crashed or timed out."""

    tool: str
    version: str
    pdf_sha256: str
    pages: tuple[NPage, ...]
    tables: tuple[NTable, ...] = field(default=())
    seconds: float = 0.0
    error: str | None = None

    def to_json(self) -> str:
        """The document as JSON, keys sorted, ASCII only."""
        return json.dumps(asdict(self), ensure_ascii=True, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "NDocument":
        """A document from `to_json`'s output, every table's tiling checked again."""
        data: dict[str, Any] = json.loads(text)
        tables = tuple(
            NTable(
                page=t["page"],
                bbox=tuple(t["bbox"]),
                cells=tuple(NCell(**c) for c in t["cells"]),
            )
            for t in data.pop("tables")
        )
        pages = tuple(NPage(box=tuple(p["box"]), rotation=p["rotation"]) for p in data.pop("pages"))
        return cls(tables=tables, pages=pages, **data)


def _lines(values: Sequence[float]) -> list[float]:
    """Distinct grid lines: sorted values, merging any within EDGE_TOL of the previous line."""
    out: list[float] = []
    for v in sorted(values):
        if not out or v - out[-1] > EDGE_TOL:
            out.append(v)
    return out


def _at(lines: Sequence[float], v: float) -> int:
    return min(range(len(lines)), key=lambda i: abs(lines[i] - v))


def cells_from_boxes(
    boxes: Sequence[Sequence[Box | None]], texts: Sequence[Sequence[str | None]]
) -> list[NCell]:
    """Cells from a grid of cell boxes, `None` where a merged cell covers a position.

    Each cell spans the grid lines its box covers; the grid lines are every distinct cell edge
    (spec 12 section 3.1). A span stops before another cell's anchor (see `_stop_at_anchors`).
    """
    present = [(r, c, b) for r, row in enumerate(boxes) for c, b in enumerate(row) if b is not None]
    xs = _lines([v for _, _, b in present for v in (b[0], b[2])])
    ys = _lines([v for _, _, b in present for v in (b[1], b[3])])
    cells = []
    for r, c, (x0, y0, x1, y1) in present:
        col0, col1 = _at(xs, x0), _at(xs, x1)
        row0, row1 = _at(ys, y0), _at(ys, y1)
        text = texts[r][c] or ""
        cells.append(
            NCell(row0, col0, rows=max(1, row1 - row0), cols=max(1, col1 - col0), text=text)
        )
    return _stop_at_anchors(sorted(cells, key=lambda c: (c.row, c.col)))


def _stop_at_anchors(cells: Sequence[NCell]) -> list[NCell]:
    """Each cell's span cut before any other cell's anchor it covers: rows first, then columns.

    pdfplumber and PyMuPDF return a box that contains another cell's box (spec 12 section 3.1,
    amended): its rows end at the first later row holding another anchor within its columns, and
    its columns at the first later column holding another anchor within the rows left.
    """
    anchors = {(c.row, c.col) for c in cells}
    out = []
    for c in cells:
        rows = next(
            (
                r - c.row
                for r in range(c.row + 1, c.row + c.rows)
                if any((r, k) in anchors for k in range(c.col, c.col + c.cols))
            ),
            c.rows,
        )
        cols = next(
            (
                k - c.col
                for k in range(c.col + 1, c.col + c.cols)
                if any((r, k) in anchors for r in range(c.row, c.row + rows))
            ),
            c.cols,
        )
        out.append(NCell(c.row, c.col, rows=rows, cols=cols, text=c.text, header=c.header))
    return out
