"""The normalized table every adapter writes (spec 12 section 3.1), and its JSON form."""

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

Box = tuple[float, float, float, float]
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
    (spec 12 section 3.1).
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
    return sorted(cells, key=lambda c: (c.row, c.col))
