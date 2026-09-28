"""PyMuPDF's tables: `page.find_tables()` with its defaults (spec 12 section 2)."""

from pathlib import Path

import pymupdf

from inkgrid_bench.adapters._cli import main
from inkgrid_bench.tables import Box, NCell, NTable, cells_from_boxes


def read(pdf: Path) -> list[NTable]:
    """Every table PyMuPDF finds, spans from its cell boxes; an internal header row is marked."""
    out = []
    doc = pymupdf.open(stream=pdf.read_bytes(), filetype="pdf")
    try:
        for number, page in enumerate(doc, start=1):
            for found in page.find_tables().tables:
                boxes: list[list[Box | None]] = [
                    [None if c is None else (c[0], c[1], c[2], c[3]) for c in row.cells]
                    for row in found.rows
                ]
                cells = cells_from_boxes(boxes, found.extract())
                if not found.header.external:
                    cells = [
                        NCell(c.row, c.col, c.rows, c.cols, c.text, header=c.row == 0)
                        for c in cells
                    ]
                # PyMuPDF measures in the displayed page; its derotation matrix undoes the turn.
                r = pymupdf.Rect(*found.bbox) * page.derotation_matrix
                out.append(NTable.filled(page=number, bbox=(r.x0, r.y0, r.x1, r.y1), cells=cells))
    finally:
        doc.close()
    return out


if __name__ == "__main__":
    raise SystemExit(main(read))
