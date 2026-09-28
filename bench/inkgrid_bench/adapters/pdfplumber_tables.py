"""pdfplumber's tables: `page.find_tables()` with its defaults (spec 12 section 2)."""

from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
from pypdfium2 import raw

from inkgrid_bench.adapters._cli import main
from inkgrid_bench.tables import Box, NTable, cells_from_boxes


def _unturn(x: float, y: float, rotation: int, width: float, height: float) -> tuple[float, float]:
    """A point of the displayed page back in the unrotated one (`width` x `height`)."""
    if rotation == 90:  # noqa: PLR2004
        return y, height - x
    if rotation == 180:  # noqa: PLR2004
        return width - x, height - y
    if rotation == 270:  # noqa: PLR2004
        return width - y, x
    return x, y


def _frame(pdf: Path, number: int) -> tuple[int, float, float, float, float]:
    """The page's rotation, its MediaBox's size, and the shift from pdfplumber's frame to ours.

    pdfplumber's x is PDF user x, and its `top` runs down from the MediaBox's height: measured on a
    plain page, a cropped one, and one whose MediaBox starts at (-100, -100).
    """
    page = pdfium.PdfDocument(pdf.read_bytes())[number - 1]
    mx0, my0, mx1, my1 = page.get_mediabox()
    r = raw.FS_RECTF()
    raw.FPDF_GetPageBoundingBox(page.raw, r)
    return page.get_rotation(), mx1 - mx0, my1 - my0, r.left, (my1 - my0) - r.top


def read(pdf: Path) -> list[NTable]:
    """Every table pdfplumber finds, spans from its cell boxes, placed in the unrotated page box.

    pdfplumber measures from the MediaBox's top left in the page's displayed orientation.
    """
    out = []
    with pdfplumber.open(pdf) as doc:
        for number, page in enumerate(doc.pages, start=1):
            rotation, width, height, dx, dy = _frame(pdf, number)
            for found in page.find_tables():
                boxes: list[list[Box | None]] = [
                    [None if c is None else (c[0], c[1], c[2], c[3]) for c in row.cells]
                    for row in found.rows
                ]
                cells = cells_from_boxes(boxes, found.extract())
                x0, y0, x1, y1 = found.bbox
                (ax, ay), (bx, by) = (
                    _unturn(x0, y0, rotation, width, height),
                    _unturn(x1, y1, rotation, width, height),
                )
                bbox = (min(ax, bx) - dx, min(ay, by) - dy, max(ax, bx) - dx, max(ay, by) - dy)
                out.append(NTable.filled(page=number, bbox=bbox, cells=cells))
    return out


if __name__ == "__main__":
    raise SystemExit(main(read))
