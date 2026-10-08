"""olmOCR-bench's born-digital pages, each tool's whole page as a candidate (spec 18 section 4).

A candidate is one `.md` per scored PDF (`<pdf without .pdf>_pg1_repeat1.md`), the tool's page
Markdown or, when it has no reading, an empty page: the scorer drops a candidate that misses one.
The driver in the scorer's environment returns every test's result with its group: the test file's
category, or `baseline` for the per-PDF baseline tests the benchmark's command adds.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path

from inkgrid_bench.scores.olmocr import candidate_path

GROUPS = {
    "headers_footers": "headers_footers.jsonl",
    "multi_column": "multi_column.jsonl",
    "tables": "table_tests.jsonl",
    "long_tiny_text": "long_tiny_text.jsonl",
}


def write_candidate(folder: Path, ids: Sequence[str], markdown: Mapping[str, str]) -> None:
    """One page per scored PDF: its Markdown, or an empty page when the tool has none."""
    for pdf in ids:
        page = folder / candidate_path(pdf)
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(markdown.get(pdf, ""), encoding="utf-8")


def pdf_counts(
    results: Mapping[str, Mapping[str, object]], ids: Sequence[str]
) -> dict[str, dict[str, float]]:
    """Each scored PDF's tests and passes per group; a scored PDF with no result is refused."""
    out: dict[str, dict[str, float]] = {pdf: {} for pdf in ids}
    for result in results.values():
        counts = out.get(str(result["pdf"]))
        if counts is None:
            continue  # a test of a PDF that is not scored
        group = str(result["group"])
        counts[f"olm_{group}_tests"] = counts.get(f"olm_{group}_tests", 0) + 1
        counts[f"olm_{group}_passed"] = counts.get(f"olm_{group}_passed", 0) + bool(
            result["passed"]
        )
    missing = [pdf for pdf, counts in out.items() if not counts]
    if missing:
        msg = f"no test result for {len(missing)} scored PDFs: {', '.join(missing[:5])}"
        raise ValueError(msg)
    return out
