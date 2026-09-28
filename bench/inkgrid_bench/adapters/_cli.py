"""The command line every adapter shares: `python -m inkgrid_bench.adapters.<tool> IN OUT`."""

import json
import sys
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from inkgrid_bench.tables import NTable


def main(read: Callable[[Path], list[NTable]]) -> int:
    """Read the PDF named by argv[1] and write its tables to argv[2] as JSON."""
    pdf, out = Path(sys.argv[1]), Path(sys.argv[2])
    tables = read(pdf)
    out.write_text(json.dumps([asdict(t) for t in tables], ensure_ascii=True), encoding="utf-8")
    return 0
