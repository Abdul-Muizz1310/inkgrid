"""olmOCR-bench's table tests: the candidate pages its scorer reads and its results per PDF.

A candidate is one `.md` per PDF page, `<pdf path without .pdf>_pg1_repeat1.md`, holding every table
as HTML with the tool's header rows (spec 12 section 3.2); a crash is an empty page, never a missing
one, since the scorer zeroes a candidate with a missing page. A heading test names `top_heading` or
`left_heading`; every other table test is a neighbour test.
"""

import re
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


_CLI_SCORE = r"^{name}\s+: Average Score: (?:([\d.]+)%|(FAILED) \(errors\))"
ROUNDING = 0.05  # the command line prints one decimal of a percentage


def cli_score(stdout: str, candidate: str, *, passed: int, total: int) -> float:
    """The score olmOCR's command line printed, checked against the tests' own pass rate.

    Raises:
        ValueError: it printed no score, failed the candidate with errors, or disagrees.
    """
    match = re.search(_CLI_SCORE.format(name=re.escape(candidate)), stdout, re.MULTILINE)
    if match is None:
        msg = f"olmOCR's command line printed no score for {candidate}"
        raise ValueError(msg)
    if match[2]:
        msg = f"olmOCR's command line failed {candidate} with errors"
        raise ValueError(msg)
    score = float(match[1])
    if abs(score - 100 * passed / total) > ROUNDING:
        msg = f"{candidate}: the command line says {score}%, the tests {passed}/{total}"
        raise ValueError(msg)
    return score
