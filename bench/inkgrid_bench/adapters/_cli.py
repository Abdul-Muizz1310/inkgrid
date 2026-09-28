"""The command line every adapter shares: `python -m inkgrid_bench.adapters.<tool> IN OUT`."""

import json
import sys
import time
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from inkgrid_bench.tables import NTable


def main(read: Callable[[Path], list[NTable]]) -> int:
    """Read the PDF named by argv[1]; write its tables and the read's seconds to argv[2] as JSON.

    The seconds are the read's own, the interpreter and the tool's imports already paid for.
    """
    pdf, out = Path(sys.argv[1]), Path(sys.argv[2])
    start = time.perf_counter()
    tables = read(pdf)
    seconds = time.perf_counter() - start
    data = {"tables": [asdict(t) for t in tables], "seconds": seconds}
    out.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8")
    return 0
