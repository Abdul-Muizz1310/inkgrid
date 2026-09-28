"""inkgrid's verifier on a benchmark PDF: its defects and advisories by class (spec 12 section 4.5).

`python -m inkgrid_bench.adapters.inkgrid_verify IN.pdf OUT.json`
"""

import json
import sys
from collections import Counter
from pathlib import Path

import inkgrid


def main() -> int:
    """Read and verify the PDF named by argv[1]; write the counts to argv[2]."""
    pdf, out = Path(sys.argv[1]), Path(sys.argv[2])
    report = inkgrid.verify(inkgrid.read(pdf), pdf)
    counts = {
        "defects": dict(sorted(Counter(str(d.code) for d in report.defects).items())),
        "advisories": dict(sorted(Counter(str(d.code) for d in report.advisories).items())),
    }
    out.write_text(json.dumps(counts, ensure_ascii=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
