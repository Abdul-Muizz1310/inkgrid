"""olmOCR-bench's own scoring code on one candidate over the scored PDFs (spec 18 section 4).

Runs inside the scorer's pinned environment (`olmocr[bench]` 0.4.27): `python -m
inkgrid_bench.scores.olmocr_pages_driver BENCH_DATA CANDIDATE PDFS.txt OUT.json GROUP=FILE...`.
It loads the named test files' tests of the scored PDFs, adds a baseline test for each scored PDF
that has none (as the benchmark's command does), calls `evaluate_candidate`, and writes every test's
result with its group.
"""

import json
import sys
from pathlib import Path

from olmocr.bench.benchmark import evaluate_candidate
from olmocr.bench.tests import BaselineTest, load_tests


def main() -> int:
    """Score the candidate folder argv[2] under argv[1] on the PDFs listed in argv[3]."""
    data, candidate, listing, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), sys.argv[4]
    groups = dict(arg.split("=", 1) for arg in sys.argv[5:])
    scored = sorted(set(listing.read_text(encoding="utf-8").split()))
    tests, group_of = [], {}
    for group, name in groups.items():
        for test in load_tests(str(data / name)):
            if test.pdf in scored:
                tests.append(test)
                group_of[test.id] = group
    for pdf in scored:
        if not any(t.type == "baseline" and t.pdf == pdf for t in tests):
            test = BaselineTest(id=f"{pdf}_baseline", pdf=pdf, page=1, type="baseline")
            tests.append(test)
            group_of[test.id] = "baseline"
    _, _, errors, _, _, _, results = evaluate_candidate(str(data / candidate), tests, scored)
    passed = {
        test.id: bool(ok)
        for by_page in results.values()
        for entries in by_page.values()
        for test, ok, _ in entries
    }
    unscored = [t.id for t in tests if t.id not in passed]
    if unscored:
        msg = f"{len(unscored)} tests have no result, first {unscored[0]}"
        raise RuntimeError(msg)
    report = {
        "errors": errors,
        "results": {
            t.id: {"pdf": t.pdf, "group": group_of[t.id], "passed": passed[t.id]} for t in tests
        },
    }
    Path(out).write_text(json.dumps(report, ensure_ascii=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
