"""unstructured's `hi_res` tables, OCR by Tesseract (docs/specs/15-heavy-competitors.md s. 1).

Its layout and table models are loaded before the first document's clock starts; the runner puts
the pinned Tesseract first on the `PATH`.
"""

from collections.abc import Sequence
from pathlib import Path

from unstructured.partition.pdf import partition_pdf
from unstructured_inference.models.base import get_model
from unstructured_inference.models.tables import load_agent

from inkgrid_bench.adapters._cli import batch
from inkgrid_bench.heavy import unstructured_tables
from inkgrid_bench.tables import NPage, NTable


def read(pdf: Path, frames: Sequence[NPage]) -> list[NTable]:
    """One document's tables."""
    elements = partition_pdf(filename=str(pdf), strategy="hi_res", infer_table_structure=True)
    return unstructured_tables([e.to_dict() for e in elements], frames)


if __name__ == "__main__":
    get_model()
    load_agent()
    raise SystemExit(batch(read))
