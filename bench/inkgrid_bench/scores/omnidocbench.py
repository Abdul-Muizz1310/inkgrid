"""OmniDocBench v1.0's end-to-end evaluation on the born-digital pages (spec 18 section 4).

The scorer reads `<page>.md` predictions and a ground-truth JSON; the driver gives it only the
scored pages (it skips a page with no prediction, so every scored page gets one, empty when the tool
has none) and rebuilds each page's counts from the scorer's per-sample results: a page's edit
distance is its summed edits over its summed lengths, and its TEDS the mean over its tables, each
averaged over pages as the scorer averages them; `check` holds the pages to the scorer's own page
averages.
"""

import json
import math
import re
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path
from typing import Any

from inkgrid_bench.page_markdown import scorable
from inkgrid_bench.scores.metrics import Counts, Metric, mean_of

MATCH = "quick_match"
# What the scorer prints when a page's text match passes its 30 s and falls back to the simple
# match (so a page's match can depend on the machine's load), and when a page has no prediction.
FALLBACK = re.compile(r"^Time out for plain text match of (.+)\.jpg, ", re.MULTILINE)
UNPREDICTED = re.compile(r"^!!!WARNING: No prediction for (.+)\.jpg$", re.MULTILINE)
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
        (folder / f"{page}.md").write_text(scorable(markdown.get(page, "")), encoding="utf-8")


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


AVERAGES: dict[str, tuple[Metric, tuple[str, ...]]] = {
    "text Edit distance": (
        mean_of("omni_text_edit", "omni_text_len"),
        ("text_block", "all", "Edit_dist", "ALL_page_avg"),
    ),
    "table TEDS": (mean_of("omni_teds_sum", "omni_teds_n"), ("table", "page", "TEDS", "ALL")),
    "table Edit distance": (
        mean_of("omni_table_edit", "omni_table_len"),
        ("table", "all", "Edit_dist", "ALL_page_avg"),
    ),
    "reading-order Edit distance": (
        mean_of("omni_order_edit", "omni_order_len"),
        ("reading_order", "all", "Edit_dist", "ALL_page_avg"),
    ),
}
LANGUAGES = ("english", "simplified_chinese")  # the text averages reported by language
TOLERANCE = 1e-9


def _theirs(result: Mapping[str, Any], path: Sequence[str]) -> float:
    """The scorer's number at `path`, NaN where it has none (its own "NaN" included)."""
    node: Any = result
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            return math.nan
        node = node[key]
    return float(node)


def _differ(ours: float, theirs: float) -> bool:
    if math.isnan(ours) or math.isnan(theirs):
        return math.isnan(ours) != math.isnan(theirs)
    return abs(ours - theirs) > TOLERANCE


def check(
    pages: Mapping[str, Counts], languages: Mapping[str, str], result: Mapping[str, Any]
) -> list[str]:
    """Where the pages' averages differ from the scorer's own (`*_metric_result.json`)."""
    out = []
    docs = list(pages.values())
    for name, (metric, path) in AVERAGES.items():
        ours, theirs = metric(docs), _theirs(result, path)
        if _differ(ours, theirs):
            out.append(f"{name}: {ours} here, {theirs} by the scorer")
    text = AVERAGES["text Edit distance"][0]
    for language in LANGUAGES:
        ours = text([c for page, c in pages.items() if languages[page] == language])
        path = ("text_block", "page", "Edit_dist", f"language: {language}")
        theirs = _theirs(result, path)
        if _differ(ours, theirs):
            out.append(f"text Edit distance, {language} pages: {ours} here, {theirs} by the scorer")
    return out


def fallbacks(log: str) -> set[str]:
    """The pages whose text the scorer matched the simple way, from its output."""
    return set(FALLBACK.findall(log))


def unpredicted(log: str) -> list[str]:
    """The pages the scorer found no prediction for, from its output."""
    return UNPREDICTED.findall(log)
