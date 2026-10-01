"""Docling's tables with every page OCR'd in full (docs/specs/15-heavy-competitors.md section 1)."""

from inkgrid_bench.adapters._cli import batch
from inkgrid_bench.adapters.docling_tables import converter, reader

if __name__ == "__main__":
    raise SystemExit(batch(reader(converter(force_ocr=True))))
