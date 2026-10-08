"""Docling's tables and page with its defaults (specs 15 and 18), in a batch.

The converter's pipeline is built, its models loaded, before the first document's clock starts.
`docling-ocr` is this adapter given an image-only copy of each PDF (section 3): Docling's forced
OCR still takes a text layer's words for its table cells (section 0).
"""

from collections.abc import Callable, Sequence
from pathlib import Path

from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.document_converter import DocumentConverter
from docling_core.transforms.serializer.html import HTMLTableSerializer
from docling_core.transforms.serializer.markdown import MarkdownDocSerializer

from inkgrid_bench.adapters._cli import batch
from inkgrid_bench.heavy import docling_tables
from inkgrid_bench.tables import NPage, Output

KEPT = frozenset({ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS})


def converter() -> DocumentConverter:
    """Docling's converter with its defaults, its models loaded."""
    conv = DocumentConverter()
    conv.initialize_pipeline(InputFormat.PDF)
    return conv


def reader(conv: DocumentConverter) -> Callable[[Path, Sequence[NPage]], Output]:
    """One document's tables and Markdown by `conv`; a failed conversion is the document's error.

    The Markdown is Docling's own serializer's, its tables written by Docling's HTML table
    serializer; it serializes the body layer only, so what Docling calls furniture stays out.
    """

    def read(pdf: Path, frames: Sequence[NPage]) -> Output:
        result = conv.convert(pdf)
        if result.status not in KEPT:
            msg = f"Docling's conversion ended {result.status.value}"
            raise RuntimeError(msg)
        doc = result.document
        markdown = MarkdownDocSerializer(
            doc=doc, table_serializer=HTMLTableSerializer()
        ).serialize()
        return Output(tuple(docling_tables(doc.export_to_dict(), frames)), markdown.text)

    return read


if __name__ == "__main__":
    raise SystemExit(batch(reader(converter())))
