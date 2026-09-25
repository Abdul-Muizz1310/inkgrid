"""Fail if total coverage, or any measured file under src/, is below its floor.

Reads the JSON report written by pytest-cov (`--cov-report=json`). `percent_covered` combines
statements and branches when branch coverage is on. Stdlib only.

Exit codes: 0 all floors met, 1 a floor missed, 2 the report has no branch data.
"""

from __future__ import annotations

import json
import sys
from fnmatch import fnmatch
from pathlib import Path

DEFAULT_FLOOR = 80.0
TOTAL_FLOOR = 80.0
# Per-file overrides: first matching glob wins. Keep this list short and justified.
OVERRIDES: dict[str, float] = {}


def floor_for(path: str) -> float:
    """Return the coverage floor for one source file."""
    for pattern, floor in OVERRIDES.items():
        if fnmatch(path, pattern):
            return floor
    return DEFAULT_FLOOR


def main(report: Path = Path("coverage.json")) -> int:
    """Check the floors in `report` and return the exit code."""
    data = json.loads(report.read_text(encoding="utf-8"))
    if not data["meta"]["branch_coverage"]:
        print("coverage.json was produced without branch coverage", file=sys.stderr)
        return 2
    failures = []
    for raw_path, info in sorted(data["files"].items()):
        path = Path(raw_path).as_posix()
        if not path.startswith("src/"):
            continue
        pct = float(info["summary"]["percent_covered"])
        floor = floor_for(path)
        if pct < floor:
            failures.append(f"{path}: {pct:.1f}% < floor {floor:.1f}%")
    total = float(data["totals"]["percent_covered"])
    if total < TOTAL_FLOOR:
        failures.append(f"total: {total:.1f}% < floor {TOTAL_FLOOR:.1f}%")
    for line in failures:
        print(line, file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(*(Path(a) for a in sys.argv[1:2])))
