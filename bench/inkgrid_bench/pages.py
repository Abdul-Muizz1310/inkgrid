"""Each page's frame as every table is placed in it: its box in PDF user space and its rotation.

The box is PDFium's page bounding box, the CropBox clipped to the MediaBox, as inkgrid's own reader
and verifier use it; every tool's tables are placed in this box, unrotated, origin at its top left.
"""

import io
from pathlib import Path

import pymupdf
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


def image_only(pdf: Path, out: Path, dpi: int = 300) -> Path:
    """An image-only copy of the PDF: each page rendered as it displays, sized so, unturned.

    A tool given the copy can read its text only by OCR (docs/specs/15-heavy-competitors.md s. 3);
    its boxes come back in each page's displayed frame, which the original's frames turn back.
    """
    source = pdfium.PdfDocument(pdf.read_bytes())
    copy = pymupdf.open()
    try:
        for index in range(len(source)):
            page = source[index]
            width, height = page.get_size()
            png = io.BytesIO()
            page.render(scale=dpi / 72).to_pil().save(png, format="PNG")
            blank = copy.new_page(width=width, height=height)
            blank.insert_image(blank.rect, stream=png.getvalue())
        copy.save(out)
    finally:
        copy.close()
        source.close()
    return out
