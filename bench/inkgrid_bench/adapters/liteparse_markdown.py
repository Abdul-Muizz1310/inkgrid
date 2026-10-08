"""LiteParse's page Markdown from the text layer (PDFium), OCR off (spec 18 section 3)."""

from pathlib import Path

from liteparse import LiteParse

from inkgrid_bench.adapters._cli import main
from inkgrid_bench.tables import Output


def read(pdf: Path) -> Output:
    """The document as LiteParse writes it, its pages one after another."""
    result = LiteParse(ocr_enabled=False, output_format="markdown", quiet=True).parse(str(pdf))
    return Output((), "\n\n".join(page.markdown for page in result.pages))


if __name__ == "__main__":
    raise SystemExit(main(read))
