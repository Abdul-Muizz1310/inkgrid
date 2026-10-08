"""MarkItDown's page Markdown from the text layer (pdfminer), plugins off (spec 18 section 3)."""

from pathlib import Path

from markitdown import MarkItDown

from inkgrid_bench.adapters._cli import main
from inkgrid_bench.tables import Output


def read(pdf: Path) -> Output:
    """The document as MarkItDown writes it."""
    return Output((), MarkItDown(enable_plugins=False).convert(str(pdf)).markdown)


if __name__ == "__main__":
    raise SystemExit(main(read))
