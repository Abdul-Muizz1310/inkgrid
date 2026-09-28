"""Each page's frame as every table is placed in it: its box in PDF user space and its rotation.

The box is PDFium's page bounding box, the CropBox clipped to the MediaBox, as inkgrid's own reader
and verifier use it; every tool's tables are placed in this box, unrotated, origin at its top left.
"""

from pathlib import Path

import pypdfium2 as pdfium
from pypdfium2 import raw

from inkgrid_bench.tables import NPage


def frames(pdf: Path) -> tuple[NPage, ...]:
    """Every page's frame, in page order."""
    doc = pdfium.PdfDocument(pdf.read_bytes())
    try:
        out = []
        for i in range(len(doc)):
            page = doc[i]
            r = raw.FS_RECTF()
            raw.FPDF_GetPageBoundingBox(page.raw, r)
            out.append(NPage(box=(r.left, r.bottom, r.right, r.top), rotation=page.get_rotation()))
        return tuple(out)
    finally:
        doc.close()
