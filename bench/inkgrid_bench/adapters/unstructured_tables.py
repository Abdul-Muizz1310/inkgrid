"""unstructured's `hi_res` tables and page, OCR by Tesseract (specs 15 and 18).

Its layout and table models are loaded before the first document's clock starts; the runner puts
the pinned Tesseract first on the `PATH`.
"""

from collections.abc import Sequence
from pathlib import Path

from unstructured.partition.pdf import partition_pdf
from unstructured_inference.models.base import get_model
from unstructured_inference.models.tables import load_agent

from inkgrid_bench.adapters._cli import batch
from inkgrid_bench.heavy import unstructured_markdown, unstructured_tables
from inkgrid_bench.tables import NPage, Output


def read(pdf: Path, frames: Sequence[NPage]) -> Output:
    """One document's tables and its page Markdown."""
    elements = partition_pdf(filename=str(pdf), strategy="hi_res", infer_table_structure=True)
    dicts = [e.to_dict() for e in elements]
    return Output(tuple(unstructured_tables(dicts, frames)), unstructured_markdown(dicts))


if __name__ == "__main__":
    get_model()
    load_agent()
    raise SystemExit(batch(read))
