"""Read ruled grids with Camelot's lattice parser. The only module that imports camelot.

Cells are read through their edge flags, never `Table.df`, and `copy_text` is never passed: a value
is never copied into a merged span (L1, L13). Every grid leaves here as cell rectangles in unrotated
page coordinates (docs/specs/06-ruled-tables.md section 2). `camelot.Table` exists only in the local
stub, so annotations here are postponed and never evaluated at runtime.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from inkgrid.model.document import Lattice
from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.geometry import Rect, Rotation, turn_point
from inkgrid.model.lattice import LatticeReading, PageFrame, RuledGrid

if TYPE_CHECKING:
    import camelot

Box = tuple[int, int, int, int]
"""A merged group as indices: first row, first column, end row, end column (exclusive)."""
Place = Callable[[float, float], tuple[float, float]]


@dataclass(frozen=True, slots=True)
class Edges:
    """Which edges of one Camelot cell are drawn."""

    left: bool
    right: bool
    top: bool
    bottom: bool


def _open_inside(edges: Sequence[Sequence[Edges]], box: Box) -> bool:
    """True when no edge inside the box is drawn, on either of its sides."""
    r0, c0, r1, c1 = box
    for r in range(r0, r1):
        for c in range(c0, c1):
            here = edges[r][c]
            if c + 1 < c1 and (here.right or edges[r][c + 1].left):
                return False
            if r + 1 < r1 and (here.bottom or edges[r + 1][c].top):
                return False
    return True


def merged_groups(edges: Sequence[Sequence[Edges]]) -> list[Box]:
    """The cells as merged groups, in reading order.

    Two neighbours belong together when the edge between them is drawn on neither side. A group
    that does not fill its bounding box exactly is split back into single cells: a guessed merge
    would fuse values (L2).
    """
    if not edges or not all(edges):
        return []  # a degenerate grid: no rows, or rows that hold no cells
    rows, cols = len(edges), len(edges[0])
    parent = {(r, c): (r, c) for r in range(rows) for c in range(cols)}

    def find(cell: tuple[int, int]) -> tuple[int, int]:
        while parent[cell] != cell:
            parent[cell] = parent[parent[cell]]
            cell = parent[cell]
        return cell

    for r in range(rows):
        for c in range(cols):
            here = edges[r][c]
            if c + 1 < cols and not here.right and not edges[r][c + 1].left:
                parent[find((r, c + 1))] = find((r, c))
            if r + 1 < rows and not here.bottom and not edges[r + 1][c].top:
                parent[find((r + 1, c))] = find((r, c))
    groups: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for cell in sorted(parent):
        groups.setdefault(find(cell), []).append(cell)
    boxes: list[Box] = []
    for members in groups.values():
        r0, c0 = min(r for r, _ in members), min(c for _, c in members)
        r1, c1 = max(r for r, _ in members) + 1, max(c for _, c in members) + 1
        if len(members) == (r1 - r0) * (c1 - c0) and _open_inside(edges, (r0, c0, r1, c1)):
            boxes.append((r0, c0, r1, c1))
        else:
            boxes.extend((r, c, r + 1, c + 1) for r, c in members)
    return sorted(boxes)


def _v_drawn(edges: Sequence[Sequence[Edges]], r: int, k: int) -> bool:
    """The vertical line k (between columns k - 1 and k) is drawn in row r."""
    return 0 < k < len(edges[0]) and (edges[r][k - 1].right or edges[r][k].left)


def _h_drawn(edges: Sequence[Sequence[Edges]], k: int, c: int) -> bool:
    """The horizontal line k (between rows k - 1 and k) is drawn in column c."""
    return 0 < k < len(edges) and (edges[k - 1][c].bottom or edges[k][c].top)


def _boundary_drawn(edges: Sequence[Sequence[Edges]], box: Box) -> bool:
    r0, c0, r1, c1 = box
    rows, cols = len(edges), len(edges[0])
    top = all(edges[r0][c].top or (r0 > 0 and edges[r0 - 1][c].bottom) for c in range(c0, c1))
    bottom = all(edges[r1 - 1][c].bottom or (r1 < rows and edges[r1][c].top) for c in range(c0, c1))
    left = all(edges[r][c0].left or (c0 > 0 and edges[r][c0 - 1].right) for r in range(r0, r1))
    right = all(edges[r][c1 - 1].right or (c1 < cols and edges[r][c1].left) for r in range(r0, r1))
    return top and bottom and left and right


def frame_core(edges: Sequence[Sequence[Edges]]) -> Box | None:
    """The closed table inside a frame's open ring, or None (spec 14 section 4.2).

    A core has its boundary drawn along its full length, no drawn line crossing into its span from
    the rows or columns around it, at least 2 x 2 cells, and the lattice reaching past it on the
    left, the right, and above or below. The largest one is returned.
    """
    if not edges or not all(edges):
        return None
    rows, cols = len(edges), len(edges[0])
    best: tuple[int, Box] | None = None
    for c0 in range(cols):
        for c1 in range(c0 + 2, cols + 1):
            drawn = [
                r for r in range(rows) if any(_v_drawn(edges, r, k) for k in range(c0 + 1, c1))
            ]
            if not drawn:
                continue
            r0, r1 = drawn[0], drawn[-1] + 1
            box: Box = (r0, c0, r1, c1)
            if r1 - r0 < 2 or not (c0 > 0 and c1 < cols and (r0 > 0 or r1 < rows)):  # noqa: PLR2004
                continue
            outside = (*range(c0), *range(c1, cols))
            if any(_h_drawn(edges, k, c) for c in outside for k in range(r0 + 1, r1)):
                continue
            if not _boundary_drawn(edges, box):
                continue
            area = (r1 - r0) * (c1 - c0)
            if best is None or area > best[0]:
                best = (area, box)
    return None if best is None else best[1]


def _placer(table: camelot.Table, frame: PageFrame) -> Place | None:
    """Camelot's y-up point to unrotated page coordinates, or None when it cannot be placed.

    Camelot works in the page's rotated frame when it turned the page: for /Rotate 180, and for 90
    or 270 when its page size comes back swapped (text upright only after the rotation).
    """
    width, height = table.pdf_size
    swapped = (width > height) != (frame.width > frame.height)
    match frame.rotation:
        case 0 if swapped:
            return None
        case 180:
            back: Rotation | None = 180
        case 90 if swapped:
            back = 270
        case 270 if swapped:
            back = 90
        case _:
            back = None
    if back is not None:
        turn = back

        def turned(x: float, y: float) -> tuple[float, float]:
            return turn_point(x, height - y, turn, width, height)

        return turned

    def upright(x: float, y: float) -> tuple[float, float]:
        return x, frame.height - y

    return upright


def _grid(table: camelot.Table, place: Place, page: int) -> RuledGrid:
    edges = [[Edges(c.left, c.right, c.top, c.bottom) for c in row] for row in table.cells]

    def rect(box: Box) -> Rect:
        r0, c0, r1, c1 = box
        first, last = table.cells[r0][c0], table.cells[r1 - 1][c1 - 1]
        x0, y0 = place(first.x1, first.y2)  # top-left, y-up
        x1, y1 = place(last.x2, last.y1)  # bottom-right, y-up
        return Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

    core = frame_core(edges)
    cells = tuple(rect(box) for box in merged_groups(edges))
    return RuledGrid(page=page, cells=cells, core=None if core is None else rect(core))


def read_lattice(
    data: bytes,  # the lattice copy (pymupdf_reader.lattice_copy): boxes equal, no encryption
    frames: Sequence[PageFrame],
    pages: Sequence[int],
    *,
    engine: Lattice,
    password: str | None,
) -> LatticeReading:
    """Camelot's lattice grids for `pages`, one page at a time so a failure costs only that page."""
    # Imported here, not at the top: pandas and OpenCV cost about 0.4 s to import, and a document
    # without ruled pages never needs them.
    import camelot  # noqa: PLC0415

    by_number = {frame.number: frame for frame in frames}
    grids: list[RuledGrid] = []
    findings: list[Finding] = []
    for number in pages:
        try:
            tables = camelot.read_pdf(
                data,
                pages=str(number),
                password=password,
                flavor="lattice",
                suppress_stdout=True,
                engine=engine,
            )
        # Camelot's failures are not typed, and any one of them must cost only this page (L18).
        except Exception as exc:  # noqa: BLE001
            detail = f"Camelot failed on this page: {type(exc).__name__}: {exc}"
            findings.append(Finding.of(FindingCode.LATTICE_FAILED, detail, page=number))
            continue
        for table in tables:
            if not table.cells or not all(table.cells):
                detail = "Camelot returned a table with no cells; it is skipped"
                findings.append(Finding.of(FindingCode.LATTICE_FAILED, detail, page=number))
                continue
            place = _placer(table, by_number[number])
            if place is None:
                detail = "Camelot turned an unrotated page; its grid cannot be placed"
                findings.append(Finding.of(FindingCode.LATTICE_FAILED, detail, page=number))
                continue
            grids.append(_grid(table, place, number))
    return LatticeReading(
        engine=engine,
        camelot=camelot.__version__,
        pages=tuple(pages),
        grids=tuple(grids),
        findings=tuple(findings),
    )
