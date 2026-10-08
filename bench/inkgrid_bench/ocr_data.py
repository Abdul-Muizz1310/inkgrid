"""Each OCR benchmark's documents: their own ids, PDFs and groups (spec 18 section 1).

The listings read the benchmarks' own files (test records, truth) as fetched, so a document is
whatever the benchmark itself scores; a PDF the benchmark refers to but the cache lacks is refused.
"""

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

OLMOCR_SPLITS = {
    "headers_footers": "headers_footers.jsonl",
    "multi_column": "multi_column.jsonl",
    "tables": "table_tests.jsonl",
    "long_tiny_text": "long_tiny_text.jsonl",
}
PARSEBENCH_FILES = ("table.jsonl", "text_content.jsonl")
DIFFICULTY = frozenset({"easy", "hard"})  # ParseBench's other tags name the text's kind
CACHE = Path.home() / ".cache" / "inkgrid-bench"
# Where each benchmark is fetched to, and the revision it is pinned at (spec 18 section 0).
LOCATIONS = {
    "olmocr": (CACHE / "olmocr" / "bench_data", "54a96a6fb6a2bd3b297e59869491db4d3625b711"),
    "omnidocbench": (CACHE / "omnidocbench" / "v1_0", "f5f559bddf50e36f7f9899d842d0006f13ce8afc"),
    "parsebench": (CACHE / "parsebench" / "data", "2805a1d940f95a203e0ae4b88be9934f7765b3fc"),
    "dpbench": (
        CACHE / "dpbench" / "opendataloader-bench",
        "7af1d8f4d0c09f51ea1a5c6ba5f66e993286d109",
    ),
}


@dataclass(frozen=True, slots=True)
class BenchDoc:
    """A benchmark document: its benchmark, its id there, its PDF, and its group."""

    benchmark: str
    id: str
    pdf: Path
    group: str


def _rows(path: Path) -> Iterable[dict[str, object]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if not isinstance(row, dict):
                msg = f"{path}: a line that is not an object"
                raise TypeError(msg)
            yield row


def _checked(docs: Iterable[BenchDoc]) -> list[BenchDoc]:
    out = sorted(docs, key=lambda d: d.id)
    missing = [d.id for d in out if not d.pdf.is_file()]
    if missing:
        msg = f"{len(missing)} PDFs the benchmark refers to are missing: {', '.join(missing[:5])}"
        raise FileNotFoundError(msg)
    return out


def olmocr_docs(data: Path) -> list[BenchDoc]:
    """olmOCR-bench's PDFs in the four scored categories, each in its category (`bench_data/`)."""
    found: dict[str, BenchDoc] = {}
    for group, name in OLMOCR_SPLITS.items():
        for row in _rows(data / name):
            pdf = str(row["pdf"])
            found.setdefault(pdf, BenchDoc("olmocr", pdf, data / "pdfs" / pdf, group))
    return _checked(found.values())


def omnidocbench_docs(data: Path) -> list[BenchDoc]:
    """OmniDocBench v1.0's pages: id is the evaluated image's name, PDF its original slice."""
    pages = json.loads((data / "OmniDocBench.json").read_text(encoding="utf-8"))
    docs = []
    for page in pages:
        info = page["page_info"]
        stem = Path(str(info["image_path"])).name.removesuffix(".jpg")
        language = str(info["page_attribute"]["language"])
        docs.append(BenchDoc("omnidocbench", stem, data / "ori_pdfs" / f"{stem}.pdf", language))
    return _checked(docs)


def parsebench_docs(data: Path) -> list[BenchDoc]:
    """ParseBench's table pages and text documents, ids as its own test ids (`table/<stem>`)."""
    tags: dict[str, list[str]] = {}
    paths: dict[str, Path] = {}
    for name in PARSEBENCH_FILES:
        track = "table" if name == "table.jsonl" else "text"
        for row in _rows(data / name):
            rel = Path(str(row["pdf"]))
            doc_id = f"{track}/{rel.stem}"
            paths[doc_id] = data / rel
            row_tags = row.get("tags")
            for tag in row_tags if isinstance(row_tags, list) else []:
                tags.setdefault(doc_id, [])
                if tag not in tags[doc_id]:
                    tags[doc_id].append(str(tag))
    docs = []
    for doc_id, pdf in paths.items():
        if doc_id.startswith("table/"):
            group = "table"
        else:
            kind = next((t for t in tags.get(doc_id, []) if t not in DIFFICULTY), None)
            group = f"text_{kind}" if kind else "text"
        docs.append(BenchDoc("parsebench", doc_id, pdf, group))
    return _checked(docs)


def dpbench_docs(root: Path) -> list[BenchDoc]:
    """DP-Bench's 200 pages, as opendataloader-bench lays them out (`pdfs/<id>.pdf`)."""
    return _checked(BenchDoc("dpbench", p.stem, p, "page") for p in (root / "pdfs").glob("*.pdf"))


LISTERS = {
    "olmocr": olmocr_docs,
    "omnidocbench": omnidocbench_docs,
    "parsebench": parsebench_docs,
    "dpbench": dpbench_docs,
}


def documents(benchmark: str) -> list[BenchDoc]:
    """The benchmark's documents, from its fetched copy."""
    return LISTERS[benchmark](LOCATIONS[benchmark][0])
