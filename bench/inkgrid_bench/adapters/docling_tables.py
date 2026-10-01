"""Docling's tables with its defaults (docs/specs/15-heavy-competitors.md section 1), in a batch.

The converter's pipeline is built, its models loaded, before the first document's clock starts.
`docling-ocr` is this adapter given an image-only copy of each PDF (section 3): Docling's forced
OCR still takes a text layer's words for its table cells (section 0).
"""

from collections.abc import Callable, Sequence
from pathlib import Path

from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.document_converter import DocumentConverter

from inkgrid_bench.adapters._cli import batch
from inkgrid_bench.heavy import docling_tables
from inkgrid_bench.tables import NPage, NTable

KEPT = frozenset({ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS})


def converter() -> DocumentConverter:
    """Docling's converter with its defaults, its models loaded."""
    conv = DocumentConverter()
    conv.initialize_pipeline(InputFormat.PDF)
    return conv


def reader(conv: DocumentConverter) -> Callable[[Path, Sequence[NPage]], list[NTable]]:
    """One document's tables by `conv`; a failed conversion is the document's error."""

    def read(pdf: Path, frames: Sequence[NPage]) -> list[NTable]:
        result = conv.convert(pdf)
        if result.status not in KEPT:
            msg = f"Docling's conversion ended {result.status.value}"
            raise RuntimeError(msg)
        return docling_tables(result.document.export_to_dict(), frames)

    return read


if __name__ == "__main__":
    raise SystemExit(batch(reader(converter())))
