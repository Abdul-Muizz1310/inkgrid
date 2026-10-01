"""The command line every adapter shares: `python -m inkgrid_bench.adapters.<tool> IN OUT`.

A heavy tool's adapter runs as `... --batch MANIFEST` instead: one process reads every document of
the manifest in turn, its models loaded once (docs/specs/15-heavy-competitors.md section 3).
"""

import json
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path

from inkgrid_bench.tables import NPage, NTable

DONE = "inkgrid-bench done "
"""The line a batch prints after each document's output is written, then the document's index."""


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


def _write(out: Path, data: dict[str, object]) -> None:
    """The output, whole or not at all: a killed process leaves no half-written file."""
    part = out.with_suffix(".part")
    part.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8")
    part.replace(out)


def batch(read: Callable[[Path, Sequence[NPage]], list[NTable]]) -> int:
    """Read every document of the manifest named by argv[2], one at a time, in this process.

    Each manifest line is a JSON object: the PDF, its output path, and its pages' frames (box and
    rotation). A read that raises writes its error as that document's output; the batch goes on.
    """
    if sys.argv[1:2] != ["--batch"] or len(sys.argv) != 3:  # noqa: PLR2004 - prog, flag, manifest
        sys.stderr.write("usage: --batch MANIFEST\n")
        return 2
    lines = Path(sys.argv[2]).read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        entry = json.loads(line)
        frames = tuple(NPage(box=(p[0], p[1], p[2], p[3]), rotation=p[4]) for p in entry["pages"])
        start = time.perf_counter()
        try:
            tables = read(Path(entry["pdf"]), frames)
        except Exception as exc:  # noqa: BLE001 - any failure is this document's, not the batch's
            data: dict[str, object] = {"error": f"{type(exc).__name__}: {exc}"}
        else:
            seconds = time.perf_counter() - start
            data = {"tables": [asdict(t) for t in tables], "seconds": seconds}
        _write(Path(entry["out"]), data)
        sys.stdout.write(f"{DONE}{index}\n")
        sys.stdout.flush()
    return 0
