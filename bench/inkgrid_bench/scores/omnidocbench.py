"""OmniDocBench v1.0's end-to-end evaluation on the born-digital pages (spec 18 section 4).

The scorer reads `<page>.md` predictions and a ground-truth JSON; the driver gives it only the
scored pages (it skips a page with no prediction, so every scored page gets one, empty when the tool
has none) and rebuilds each page's counts from the scorer's per-sample results: a page's edit
distance is its summed edits over its summed lengths, and TEDS is pooled over tables, as the scorer
computes them.
"""

import json
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path
from typing import Any

MATCH = "quick_match"
ELEMENTS = {
    "text_block": ("omni_text_edit", "omni_text_len"),
    "table": ("omni_table_edit", "omni_table_len"),
    "reading_order": ("omni_order_edit", "omni_order_len"),
}
KEYS = (*(k for pair in ELEMENTS.values() for k in pair), "omni_teds_sum", "omni_teds_n")


def page_id(page: Mapping[str, Any]) -> str:
    """A ground-truth page's id: its image's name without `.jpg`."""
    return Path(str(page["page_info"]["image_path"])).name.removesuffix(".jpg")


def subset(pages: Sequence[Mapping[str, Any]], ids: Collection[str]) -> list[Mapping[str, Any]]:
    """The ground-truth pages that are scored, in their order."""
    return [p for p in pages if page_id(p) in ids]


def write_predictions(folder: Path, ids: Sequence[str], markdown: Mapping[str, str]) -> None:
    """One `<page>.md` per scored page: the tool's Markdown, or empty when it has none."""
    folder.mkdir(parents=True, exist_ok=True)
    for page in ids:
        (folder / f"{page}.md").write_text(markdown.get(page, ""), encoding="utf-8")


def config_yaml(ground_truth: Path, predictions: Path) -> str:
    """The end-to-end task's configuration: text, tables and reading order; no formulas."""
    return f"""end2end_eval:
  metrics:
    text_block:
      metric:
        - Edit_dist
    table:
      metric:
        - TEDS
        - Edit_dist
    reading_order:
      metric:
        - Edit_dist
  dataset:
    dataset_name: end2end_dataset
    ground_truth:
      data_path: {ground_truth}
    prediction:
      data_path: {predictions}
    match_method: {MATCH}
"""


def save_name(predictions: Path) -> str:
    """The prefix the scorer gives its result files for a prediction folder."""
    return f"{predictions.name}_{MATCH}"


def page_counts(result: Path, name: str, ids: Sequence[str]) -> dict[str, dict[str, float]]:
    """Each scored page's edits and lengths per element and its tables' TEDS, from the samples."""
    out: dict[str, dict[str, float]] = {page: dict.fromkeys(KEYS, 0.0) for page in ids}
    for element, (edits, lengths) in ELEMENTS.items():
        rows = json.loads((result / f"{name}_{element}_result.json").read_text(encoding="utf-8"))
        for row in rows:
            page = str(row["image_name"]).removesuffix(".jpg")
            if page not in out:
                msg = f"a {element} sample of page {page}, which is not scored"
                raise ValueError(msg)
            if "Edit_num" in row:
                out[page][edits] += row["Edit_num"]
                out[page][lengths] += row["upper_len"]
            if element == "table":
                metric = row["metric"]
                if not isinstance(metric, dict):
                    msg = f"a table sample of page {page} without its TEDS"
                    raise TypeError(msg)
                out[page]["omni_teds_sum"] += metric["TEDS"]
                out[page]["omni_teds_n"] += 1
    return out
