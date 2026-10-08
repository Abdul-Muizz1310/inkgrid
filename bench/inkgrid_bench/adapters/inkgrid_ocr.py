"""inkgrid fed Tesseract's words: the text-layer ablation (docs/specs/15-heavy-competitors.md s. 4).

Each page is rendered at 300 DPI as it displays (pypdfium2) and read by the pinned Tesseract
(`tsv`, page segmentation mode 3, English); the words replace the text layer's, all else kept.
"""

import io
import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pypdfium2 as pdfium

from inkgrid_bench import pages
from inkgrid_bench.ablation import DPI, ocr_document
from inkgrid_bench.adapters._cli import main
from inkgrid_bench.adapters.inkgrid_read import tables_of
from inkgrid_bench.fetch import TESSERACT
from inkgrid_bench.page_markdown import inkgrid_markdown
from inkgrid_bench.tables import Output

ARGS = ("--psm", "3", "-l", "eng", "tsv")


def _tesseract(doc: pdfium.PdfDocument) -> Callable[[int], str]:
    env = {**os.environ, "TESSDATA_PREFIX": str(TESSERACT / "share" / "tessdata")}

    def page_tsv(number: int) -> str:
        image = doc[number - 1].render(scale=DPI / 72).to_pil()
        png = io.BytesIO()
        image.save(png, format="PNG")
        done = subprocess.run(  # noqa: S603 - the pinned binary, fixed arguments
            [str(TESSERACT / "bin" / "tesseract"), "stdin", "stdout", *ARGS],
            input=png.getvalue(),
            capture_output=True,
            check=True,
            env=env,
        )
        return done.stdout.decode("utf-8")

    return page_tsv


def read(pdf: Path) -> Output:
    """The tables and the page Markdown inkgrid reads with Tesseract's words for its own."""
    data = pdf.read_bytes()
    rendered = pdfium.PdfDocument(data)
    try:
        doc = ocr_document(data, pages.frames(pdf), _tesseract(rendered))
    finally:
        rendered.close()
    return Output(tuple(tables_of(doc)), inkgrid_markdown(doc))


if __name__ == "__main__":
    raise SystemExit(main(read))
