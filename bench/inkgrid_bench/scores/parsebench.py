"""ParseBench's tables and text, scored by ParseBench itself (docs/specs/18-ocr-benchmarks.md s. 4).

Each tool's page is saved under ParseBench's example id, its GFM pipe tables written as HTML by the
one shared converter (ParseBench scores only HTML tables), and a provider in parse-bench's own
environment hands it back unchanged (`parsebench_driver`). The per-document values are read from
ParseBench's evaluation report, and a scored document missing from it is refused. One ParseBench
could not evaluate counts as ParseBench's own aggregates count it: an error of its evaluation
harness leaves the document out of the tool's means (`pb_unscored`), any other failure scores it 0
(`pb_failed`); the report lists both.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from inkgrid_bench.page_markdown import pipe_to_html, scorable
from inkgrid_bench.scores.parsebench_names import saved_name

TABLE_METRICS = ("grits_trm_composite", "grits_con", "table_record_match")
TEXT_METRICS = ("content_faithfulness", "normalized_text_correctness", "normalized_order")
# The errors ParseBench's runner treats as its own harness's, never padded with 0 (runner.py).
HARNESS_ERRORS = ("Worker error:", "Evaluation error:", "Task execution error:")


def write_saved(folder: Path, ids: Sequence[str], markdown: Mapping[str, str]) -> None:
    """Each scored example's page, pipe tables as HTML; an empty page when the tool has none."""
    folder.mkdir(parents=True, exist_ok=True)
    for doc in ids:
        text = pipe_to_html(scorable(markdown.get(doc, "")))
        (folder / saved_name(doc)).write_text(text, encoding="utf-8")


def document_scores(
    report: Mapping[str, Any], ids: Sequence[str], metrics: Sequence[str]
) -> dict[str, dict[str, float]]:
    """Each scored document's metrics, from ParseBench's evaluation report."""
    found = {str(e["test_id"]): e for e in report["per_example_results"]}
    missing = [doc for doc in ids if doc not in found]
    if missing:
        msg = (
            f"ParseBench reported no result for {len(missing)} documents: {', '.join(missing[:5])}"
        )
        raise ValueError(msg)
    out: dict[str, dict[str, float]] = {}
    for doc in ids:
        entry = found[doc]
        counts: dict[str, float] = {"pb_unscored": 0, "pb_failed": 0}
        if entry["success"]:
            values = {str(m["metric_name"]): m["value"] for m in entry["metrics"]}
            for name in metrics:
                value = values.get(name)
                counts[f"pb_{name}"] = 0.0 if value is None else float(value)
                counts[f"pb_{name}_n"] = 0 if value is None else 1
        else:
            error = str(entry.get("error") or "")
            harness = error.startswith(HARNESS_ERRORS) and "not LayoutOutput" not in error
            own = harness or "No layout data" in error
            counts["pb_unscored" if own else "pb_failed"] = 1
            for name in metrics:
                counts[f"pb_{name}"] = 0.0
                counts[f"pb_{name}_n"] = 0 if own else 1
        out[doc] = counts
    return out
