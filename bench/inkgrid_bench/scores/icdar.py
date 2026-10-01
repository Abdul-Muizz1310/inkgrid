"""The ICDAR-2013 competition jar: its command lines and its output as per-document counts.

Structure mode prints one line per ground-truth table: its relation counts when a result table
matched it, or `no matching result found`, which carries no ground-truth size; that size comes from
scoring the ground truth against itself. Each result table that matched none follows as a false
positive with its relations, all detected and none correct. Region mode prints per ground-truth
region its character counts, and every unmatched result region as a false positive, its characters
detected wrongly.
"""

import os
import re
from collections.abc import Mapping
from pathlib import Path

MAIN = "at.ac.tuwien.dbai.pdfwrap.MeasureRecognitionPerformance"
# The jar's comparators predate Java 7's TimSort, which rejects them on some pages (practice
# eu-014); every run uses the merge sort they were written for.
LEGACY_SORT = "-Djava.util.Arrays.useLegacyMergeSort=true"
# Region mode reads the PDF and needs these beside the jar (the jar bundles PDFBox 1.8.2 only);
# PDFBox opens an encrypted PDF (held-out tfex-usd) only with the BouncyCastle its pom names, 1.44.
CLASSPATH = (
    "dataset-tools-20180206.jar",
    "jai-1_1_3/lib/jai_core.jar",
    "fontbox-1.8.2.jar",
    "commons-collections-3.2.2.jar",
    "bcprov-jdk15-1.44.jar",
)

# Not anchored to a line start: the jar prints ground-truth warnings to stdout without a newline.
_MATCHED = re.compile(r"Table (\d+):\s+GT size: (\d+) corrDet: (\d+) detected: (\d+)\s")
_UNMATCHED = re.compile(r"Table (\d+): no matching result found")
_FP_TABLES = re.compile(r"(\d+) FALSE POSITIVE TABLES FOUND")
_FP_TABLE = re.compile(r"FP table with (\d+) adjacency relations")
_REGION = re.compile(
    r"Region: (\d+)\s+GT Items: (\d+)(?:\s+correct items: (\d+)\s+result items: (\d+))?"
)
# Every false-positive region is on one line, each `FP Region: k  items: n`, then `FP items: total`.
_FP = re.compile(r"FP Region: \d+\s+items: (\d+)")
_FP_TOTAL = re.compile(r"FP items: (\d+)")
_GT_REGIONS = re.compile(r"^GT Regions: (\d+)", re.MULTILINE)
_FP_COUNT = re.compile(r"^FP regions: (\d+)", re.MULTILINE)


def command(java: Path, tools: Path, mode: str, *, gt: Path, result: Path, pdf: Path) -> list[str]:
    """The jar's command line for `mode` (`-str` or `-reg`), run in the files' directory."""
    if mode not in ("-str", "-reg"):
        msg = f"unknown mode {mode!r}"
        raise ValueError(msg)
    classpath = os.pathsep.join(str(tools / part) for part in CLASSPATH)
    return [str(java), LEGACY_SORT, "-cp", classpath, MAIN, mode, gt.name, result.name, pdf.name]


def gt_sizes(stdout: str) -> dict[int, int]:
    """Each ground-truth table's relation count, from the ground truth scored against itself."""
    if _UNMATCHED.search(stdout):
        msg = "the ground truth did not match itself"
        raise ValueError(msg)
    sizes = {int(m[1]): int(m[2]) for m in _MATCHED.finditer(stdout)}
    if not sizes:
        msg = "no table in the jar's output"
        raise ValueError(msg)
    return sizes


def structure_counts(stdout: str, sizes: Mapping[int, int]) -> dict[str, int]:
    """A document's relations, correct, detected, and in the ground truth, over its tables."""
    correct = detected = gt = 0
    seen: set[int] = set()
    for m in _MATCHED.finditer(stdout):
        table, size = int(m[1]), int(m[2])
        if table in seen:
            msg = f"table {table} is reported twice"
            raise ValueError(msg)
        if sizes.get(table) != size:
            msg = f"table {table}: GT size {size}, expected {sizes.get(table)}"
            raise ValueError(msg)
        seen.add(table)
        correct, detected, gt = correct + int(m[3]), detected + int(m[4]), gt + size
    for m in _UNMATCHED.finditer(stdout):
        table = int(m[1])
        if table in seen:
            msg = f"table {table} is reported twice"
            raise ValueError(msg)
        if table not in sizes:
            msg = f"table {table} is not in the ground truth"
            raise ValueError(msg)
        seen.add(table)
        gt += sizes[table]
    missing = sorted(set(sizes) - seen)
    if missing:
        msg = f"table {missing[0]} is missing from the jar's output"
        raise ValueError(msg)
    fps = [int(m[1]) for m in _FP_TABLE.finditer(stdout)]
    declared = _FP_TABLES.search(stdout)
    if (int(declared[1]) if declared else 0) != len(fps):
        msg = f"{declared[1] if declared else 0} FALSE POSITIVE TABLES declared, {len(fps)} listed"
        raise ValueError(msg)
    return {"correct": correct, "detected": detected + sum(fps), "gt": gt}


def region_counts(stdout: str) -> dict[str, int]:
    """A document's characters: correct, detected (with false positives'), in the ground truth."""
    regions = list(_REGION.finditer(stdout))
    declared = _GT_REGIONS.search(stdout)
    if declared is None or int(declared[1]) != len(regions):
        msg = f"GT Regions: {declared[1] if declared else 'none'}, {len(regions)} reported"
        raise ValueError(msg)
    fps = [int(m[1]) for m in _FP.finditer(stdout)]
    fp_declared = _FP_COUNT.search(stdout)
    if fp_declared is None or int(fp_declared[1]) != len(fps):
        msg = f"FP regions: {fp_declared[1] if fp_declared else 'none'}, {len(fps)} reported"
        raise ValueError(msg)
    total = _FP_TOTAL.search(stdout)
    if fps and (total is None or int(total[1]) != sum(fps)):
        msg = f"FP items: {total[1] if total else 'none'}, the regions sum to {sum(fps)}"
        raise ValueError(msg)
    correct = sum(int(m[3] or 0) for m in regions)
    detected = sum(int(m[4] or 0) for m in regions) + sum(fps)
    return {"correct": correct, "detected": detected, "gt": sum(int(m[2]) for m in regions)}
