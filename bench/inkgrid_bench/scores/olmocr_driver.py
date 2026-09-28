"""olmOCR-bench's own scoring code on one candidate, reporting every test's result.

Runs inside the scorer's pinned environment (`olmocr[bench]` 0.4.27):
`python -m inkgrid_bench.scores.olmocr_driver BENCH_DATA CANDIDATE OUT.json`. It calls the function
the benchmark's command line calls for each candidate, `evaluate_candidate`, on the table tests
without the baseline tests (`--skip_baseline`), and keeps what the command line prints only in
aggregate: each test's pass, and every error it met.
"""

import json
import sys
from pathlib import Path

from olmocr.bench.benchmark import evaluate_candidate
from olmocr.bench.tests import load_tests


def main() -> int:
    """Score the candidate folder named by argv[2] under the benchmark folder argv[1]."""
    data, candidate, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    pdf_folder = data / "pdfs"
    pdfs = [str(p.relative_to(pdf_folder)) for p in sorted(pdf_folder.rglob("*.pdf"))]
    tests = [t for t in load_tests(str(data / "table_tests.jsonl")) if t.type != "baseline"]
    score, total, errors, _, _, _, results = evaluate_candidate(str(data / candidate), tests, pdfs)
    passed = {
        test.id: bool(ok)
        for by_page in results.values()
        for entries in by_page.values()
        for test, ok, _ in entries
    }
    report = {"score": score, "tests": total, "errors": errors, "passed": passed}
    out.write_text(json.dumps(report, ensure_ascii=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
