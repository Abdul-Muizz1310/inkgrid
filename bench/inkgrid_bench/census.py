"""Which benchmark pages count: born-digital pages with a text layer (spec 18 section 2).

Pure classification over page statistics; the statistics come from PyMuPDF's text trace and image
placements, so no benchmarked tool decides which pages are scored. The split puts each document in
dev or test once, by a hash of its benchmark and id.
"""

import hashlib
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pymupdf

from inkgrid_bench.ocr_data import LOCATIONS, BenchDoc, documents

type PageClass = Literal["born_digital", "no_text", "ocr_layer", "image_backed"]
type Half = Literal["dev", "test"]
MIN_VISIBLE = 50  # visible non-whitespace characters a page needs to count as having text
IMAGE_SHARE = 0.9  # a raster image covering this much of the page makes it image-backed
INVISIBLE = 3  # the text render mode that draws nothing (an OCR layer)


@dataclass(frozen=True, slots=True)
class PageStats:
    """A page's visible and invisible characters, and the largest share of it one image covers."""

    visible: int
    invisible: int
    image_share: float


def classify(stats: PageStats) -> PageClass:
    """The page's class, the rules in order: too little text, an OCR layer, a page-size image."""
    if stats.visible < MIN_VISIBLE:
        return "no_text"
    if stats.invisible >= stats.visible:
        return "ocr_layer"
    if stats.image_share >= IMAGE_SHARE:
        return "image_backed"
    return "born_digital"


def document_class(pages: Sequence[PageClass]) -> PageClass:
    """Born-digital when every page is; otherwise the class of the first page that is not."""
    if not pages:
        msg = "a document with no pages has no class"
        raise ValueError(msg)
    return next((c for c in pages if c != "born_digital"), "born_digital")


def split(benchmark: str, doc_id: str) -> Half:
    """The document's half: dev when its hash's first hex digit is 0-7, test otherwise."""
    digit = hashlib.sha256(f"inkgrid-m7:{benchmark}:{doc_id}".encode()).hexdigest()[0]
    return "dev" if digit in "01234567" else "test"


def page_stats(page: pymupdf.Page) -> PageStats:
    """A page's statistics: characters by visibility, and the largest single image's coverage."""
    visible = invisible = 0
    for span in page.get_texttrace():
        count = sum(1 for c in span["chars"] if c[0] > 0 and not chr(c[0]).isspace())
        if span["type"] == INVISIBLE or span["opacity"] == 0:
            invisible += count
        else:
            visible += count
    rect = page.rect
    area = rect.width * rect.height
    share = 0.0
    for image in page.get_image_info():
        x0, y0, x1, y1 = image["bbox"]
        width = min(x1, rect.x1) - max(x0, rect.x0)
        height = min(y1, rect.y1) - max(y0, rect.y0)
        if width > 0 and height > 0 and area > 0:
            share = max(share, width * height / area)
    return PageStats(visible=visible, invisible=invisible, image_share=share)


def pdf_classes(pdf: Path) -> list[PageClass]:
    """Every page's class; a PDF that cannot be opened without a password has no text."""
    doc = pymupdf.open(stream=pdf.read_bytes(), filetype="pdf")
    try:
        if doc.needs_pass and not doc.authenticate(""):
            return ["no_text"] * max(doc.page_count, 1)
        return [classify(page_stats(page)) for page in doc]
    finally:
        doc.close()


def manifest(benchmark: str, revision: str, docs: Sequence[BenchDoc]) -> dict[str, Any]:
    """The census of a benchmark: per document, its PDF's hash, page classes, class and half."""
    entries: dict[str, dict[str, Any]] = {}
    for doc in sorted(docs, key=lambda d: d.id):
        pages = pdf_classes(doc.pdf)
        entries[doc.id] = {
            "sha256": hashlib.sha256(doc.pdf.read_bytes()).hexdigest(),
            "pages": pages,
            "class": document_class(pages),
            "half": split(benchmark, doc.id),
            "group": doc.group,
        }
    return {"benchmark": benchmark, "revision": revision, "documents": entries}


MANIFESTS = Path(__file__).resolve().parents[1] / "ocr"


def main(argv: Sequence[str] = sys.argv[1:]) -> int:
    """Write the census manifest of each benchmark named (all four by default) to `bench/ocr/`."""
    MANIFESTS.mkdir(exist_ok=True)
    for benchmark in argv or list(LOCATIONS):
        found = manifest(benchmark, LOCATIONS[benchmark][1], documents(benchmark))
        out = MANIFESTS / f"census-{benchmark}.json"
        out.write_text(json.dumps(found, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        classes = [d["class"] for d in found["documents"].values()]
        counts = {c: classes.count(c) for c in sorted(set(classes))}
        sys.stdout.write(f"{benchmark}: {len(classes)} documents {counts}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
