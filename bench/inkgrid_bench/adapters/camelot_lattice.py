"""Camelot's tables: `camelot.read_pdf(pages="all", flavor="lattice")` (spec 12 section 2)."""

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import camelot
import pypdfium2 as pdfium
from pypdfium2 import raw

from inkgrid_bench.adapters._cli import main
from inkgrid_bench.tables import NCell, NTable

if TYPE_CHECKING:
    from camelot import Table  # the stub's name; Camelot keeps the class in camelot.core

Point = tuple[float, float]


def _frames(pdf: Path) -> list[tuple[tuple[float, float, float, float], int]]:
    """Each page's box in PDF user space and its rotation."""
    doc = pdfium.PdfDocument(pdf.read_bytes())
    out = []
    for i in range(len(doc)):
        page = doc[i]
        r = raw.FS_RECTF()
        raw.FPDF_GetPageBoundingBox(page.raw, r)
        out.append(((r.left, r.bottom, r.right, r.top), page.get_rotation()))
    return out


def _turn(x: float, y: float, rotation: int, width: float, height: float) -> Point:
    """A top-left point of a page turned by `rotation` (PyMuPDF's convention, spec 06)."""
    if rotation == 90:  # noqa: PLR2004
        return height - y, x
    if rotation == 180:  # noqa: PLR2004
        return width - x, height - y
    if rotation == 270:  # noqa: PLR2004
        return y, width - x
    return x, y


def _placer(
    size: Sequence[float], box: Sequence[float], rotation: int
) -> Callable[[float, float], Point]:
    """Camelot's y-up point to the unrotated page box's top-left frame.

    Camelot works in the page's turned frame when it turned the page: for /Rotate 180, and for 90 or
    270 when its page size comes back swapped (spec 06-ruled-tables section 3).
    """
    width, height = size
    unrotated_w, unrotated_h = box[2] - box[0], box[3] - box[1]
    swapped = (width > height) != (unrotated_w > unrotated_h)
    back = {180: 180, 90: 270, 270: 90}.get(rotation) if (rotation == 180 or swapped) else None  # noqa: PLR2004
    if back is not None:
        return lambda x, y: _turn(x, height - y, back, width, height)
    return lambda x, y: (x, unrotated_h - y)


def _groups(table: "Table") -> list[tuple[int, int, int, int]]:
    """Merged cells from Camelot's edge flags: neighbours join where neither draws the edge."""
    grid = table.cells
    rows, cols = len(grid), len(grid[0]) if grid else 0
    parent = {(r, c): (r, c) for r in range(rows) for c in range(cols)}

    def find(k: tuple[int, int]) -> tuple[int, int]:
        while parent[k] != k:
            k = parent[k]
        return k

    for r in range(rows):
        for c in range(cols):
            if c + 1 < cols and not grid[r][c].right and not grid[r][c + 1].left:
                parent[find((r, c + 1))] = find((r, c))
            if r + 1 < rows and not grid[r][c].bottom and not grid[r + 1][c].top:
                parent[find((r + 1, c))] = find((r, c))
    members: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for k in parent:
        members.setdefault(find(k), []).append(k)
    out = []
    for group in members.values():
        r0, c0 = min(r for r, _ in group), min(c for _, c in group)
        r1, c1 = max(r for r, _ in group) + 1, max(c for _, c in group) + 1
        if len(group) == (r1 - r0) * (c1 - c0):
            out.append((r0, c0, r1, c1))
        else:
            out += [(r, c, r + 1, c + 1) for r, c in group]
    return sorted(out)


def read(pdf: Path) -> list[NTable]:
    """Every table Camelot's lattice finds, merged cells from its edge flags."""
    frames = _frames(pdf)
    out = []
    for found in camelot.read_pdf(pdf.read_bytes(), pages="all", flavor="lattice"):
        number = int(found.page)
        box, rotation = frames[number - 1]
        place = _placer(found.pdf_size, box, rotation)
        cells = []
        for r0, c0, r1, c1 in _groups(found):
            texts = [str(found.df.iloc[r, c]).strip() for r in range(r0, r1) for c in range(c0, c1)]
            text = " ".join(t for t in texts if t)
            cells.append(NCell(r0, c0, rows=r1 - r0, cols=c1 - c0, text=text))
        x1, y1, x2, y2 = found._bbox  # noqa: SLF001 - Camelot's table box, y-up
        (ax, ay), (bx, by) = place(x1, y2), place(x2, y1)
        bbox = (min(ax, bx), min(ay, by), max(ax, bx), max(ay, by))
        out.append(NTable.filled(page=number, bbox=bbox, cells=cells))
    return out


if __name__ == "__main__":
    raise SystemExit(main(read))
