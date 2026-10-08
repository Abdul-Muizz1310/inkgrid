"""pymupdf4llm's page Markdown from the text layer, OCR off, tables as HTML (spec 18 section 3).

It runs in its own pinned environment: pymupdf4llm loads PyMuPDF Layout, which inkgrid's process
must never import. Its layout model labels page headers and footers but keeps them by default;
`header=False, footer=False` leaves them out, as the other tools that recognise furniture do.
"""

from pathlib import Path

import pymupdf4llm

from inkgrid_bench.adapters._cli import main
from inkgrid_bench.tables import Output


def read(pdf: Path) -> Output:
    """The document as pymupdf4llm writes it."""
    markdown = pymupdf4llm.to_markdown(
        str(pdf), table_output="html", use_ocr=False, header=False, footer=False
    )
    return Output((), markdown)


if __name__ == "__main__":
    raise SystemExit(main(read))
