"""DP-Bench through opendataloader-bench's Markdown evaluator (spec 18 section 4).

The evaluator scores every ground-truth document it can and silently leaves out one it fails on, so
the driver refuses a result that lacks a scored document. TEDS is defined only where the truth has a
table and MHS only where it has a heading: a document without one counts 0 of 0 there.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

SCORES = ("nid", "teds", "mhs")


def write_predictions(
    root: Path, engine: str, ids: Sequence[str], markdown: Mapping[str, str]
) -> Path:
    """The engine's `markdown/<id>.md` under `root`, one per scored document, empty if unread."""
    folder = root / engine / "markdown"
    folder.mkdir(parents=True, exist_ok=True)
    for doc in ids:
        (folder / f"{doc}.md").write_text(markdown.get(doc, ""), encoding="utf-8")
    return folder


def document_scores(
    evaluation: Mapping[str, Any], ids: Sequence[str]
) -> dict[str, dict[str, float]]:
    """Each scored document's NID, TEDS and MHS with their counts; a dropped document is refused."""
    by_id = {str(d["document_id"]): d["scores"] for d in evaluation["documents"]}
    missing = [doc for doc in ids if doc not in by_id]
    if missing:
        msg = f"the evaluator left out {len(missing)} documents: {', '.join(missing[:5])}"
        raise ValueError(msg)
    out: dict[str, dict[str, float]] = {}
    for doc in ids:
        counts: dict[str, float] = {}
        for key in SCORES:
            value = by_id[doc].get(key)
            counts[f"dp_{key}"] = 0.0 if value is None else float(value)
            counts[f"dp_{key}_n"] = 0 if value is None else 1
        out[doc] = counts
    return out
