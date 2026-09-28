"""Soric et al.'s evaluator: the predictions it reads and its results as per-document counts.

Their evaluator reads `predictions_<model>.json`, one entry per page image (`<doc>_<page>.jpg`,
the page 0-based) with the table boxes in image pixels and one HTML table per box. Every tool is
written in the layout of their `pymu` model (each box's HTML wrapped in a list), the one that model
name unpacks; the name selects nothing else. Their results list every prediction on their pages with
its IoU and, when matched, its GriTS and TEDS scores; a match counts at IoU >= 0.5 (spec 12 4.2).
"""

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from inkgrid_bench.render import soric_box, table_html
from inkgrid_bench.tables import NDocument

MODEL = "pymu"
MATCH_IOU = 0.5
SCORES = ("top", "con", "teds")

Prediction = dict[str, list[Any]]


def predictions(docs: Mapping[str, NDocument]) -> dict[str, Prediction]:
    """Each page image's boxes and HTML, for the pages where the tool found a table."""
    out: dict[str, Prediction] = {}
    for stem, doc in docs.items():
        for table in doc.tables:
            entry = out.setdefault(f"{stem}_{table.page - 1}.jpg", {"boxes": [], "html": []})
            entry["boxes"].append(list(soric_box(table.bbox, doc.pages[table.page - 1])))
            entry["html"].append([table_html(table, header=False)])
    return out


def _doc(image: str) -> str:
    match = re.fullmatch(r"(.+)_\d+\.jpg", image)
    if match is None:
        msg = f"not a page image name: {image!r}"
        raise ValueError(msg)
    return match[1]


def gt_counts(dataset: Path) -> dict[str, int]:
    """Each document's ground-truth tables as their loader pairs them: boxes with HTML, per page.

    Their loader reads the pages that have an image; on each it pairs the annotation's boxes with
    the page's HTML files one to one, and counts the pairs.
    """
    images = {p.stem for p in (dataset / "images").glob("*.jpg")}
    html = [p.name for p in (dataset / "html").glob("*.html")]
    out: dict[str, int] = {}
    for annotation in sorted((dataset / "test").glob("*.xml")):
        page = annotation.stem
        if page not in images:
            continue
        boxes = annotation.read_text(encoding="utf-8").count("<object>")
        files = sum(name.startswith(page + "_") for name in html)
        doc = _doc(page + ".jpg")
        out[doc] = out.get(doc, 0) + min(boxes, files)
    return out


def result_counts(results: Mapping[str, Any], gt: Mapping[str, int]) -> dict[str, dict[str, float]]:
    """Each document's predictions, ground truths, matches, and summed match scores."""
    if results["ground_truths"] != sum(gt.values()):
        msg = f"{results['ground_truths']} ground truths scored, {sum(gt.values())} expected"
        raise ValueError(msg)
    out: dict[str, dict[str, float]] = {
        doc: {"pred": 0, "gt": n, "tp": 0, "top": 0, "con": 0, "teds": 0} for doc, n in gt.items()
    }
    entries = results["all"]
    if not entries:
        return out
    names = entries["img_name"][0]
    if not all(len(entries[k]) == len(names) for k in ("iou", *SCORES)):
        msg = "the results' columns differ in length"
        raise ValueError(msg)
    for i, image in enumerate(names):
        doc = _doc(image)
        if doc not in out:
            msg = f"{image} is not a ground-truth document's page"
            raise ValueError(msg)
        counts = out[doc]
        counts["pred"] += 1
        if entries["iou"][i] >= MATCH_IOU:
            counts["tp"] += 1
            for key in SCORES:
                counts[key] += entries[key][i]
    return out
