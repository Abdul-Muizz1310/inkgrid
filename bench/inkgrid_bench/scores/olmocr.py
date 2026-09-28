"""olmOCR-bench's table tests: the candidate pages its scorer reads and its results per PDF.

A candidate is one `.md` per PDF page, `<pdf path without .pdf>_pg1_repeat1.md`, holding every table
as HTML with the tool's header rows (spec 12 section 3.2); a crash is an empty page, never a missing
one, since the scorer zeroes a candidate with a missing page. A heading test names `top_heading` or
`left_heading`; every other table test is a neighbour test.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from inkgrid_bench.render import table_html
from inkgrid_bench.tables import NDocument

KEYS = ("tests", "passed", "heading", "heading_passed", "neighbour", "neighbour_passed")


def page_markdown(doc: NDocument) -> str:
    """Every table the tool found, as HTML, in reading order."""
    return "\n\n".join(table_html(t, header=True) for t in doc.tables)


def candidate_path(pdf: str) -> str:
    """The page file the scorer looks for, relative to the candidate folder."""
    if not pdf.endswith(".pdf"):
        msg = f"not a PDF path: {pdf!r}"
        raise ValueError(msg)
    return pdf.removesuffix(".pdf") + "_pg1_repeat1.md"


def is_heading(test: Mapping[str, Any]) -> bool:
    """Whether a table test checks a heading rather than a neighbour."""
    return bool(test.get("top_heading") or test.get("left_heading"))


def result_counts(
    tests: Sequence[Mapping[str, Any]], passed: Mapping[str, bool]
) -> dict[str, dict[str, float]]:
    """Each PDF's table tests and passes, all, heading, and neighbour."""
    out: dict[str, dict[str, float]] = {}
    for test in tests:
        if test["type"] != "table":
            continue
        if test["id"] not in passed:
            msg = f"test {test['id']} has no result"
            raise ValueError(msg)
        counts = out.setdefault(test["pdf"], dict.fromkeys(KEYS, 0))
        kind = "heading" if is_heading(test) else "neighbour"
        ok = passed[test["id"]]
        counts["tests"] += 1
        counts["passed"] += ok
        counts[kind] += 1
        counts[f"{kind}_passed"] += ok
    return out
