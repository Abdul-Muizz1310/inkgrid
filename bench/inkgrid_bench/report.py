"""The report: every metric of spec 12 section 4 with its interval, and inkgrid's differences.

Pure: per-document counts in, intervals and Markdown out. A difference is marked a finding only when
its interval excludes 0 (spec 12 section 5); nothing is pooled across datasets.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from inkgrid_bench.scores.metrics import Counts, Metric, dice, harmonic, mean_of, pooled
from inkgrid_bench.stats import RESAMPLES, SEED, Interval, bootstrap, paired

BASELINE = "inkgrid"


@dataclass(frozen=True, slots=True)
class MetricSpec:
    """One reported number: its key in the results, its column label, and its formula."""

    key: str
    label: str
    metric: Metric


def _dar(prefix: str, name: str) -> tuple[MetricSpec, ...]:
    p = mean_of(f"{prefix}_correct", f"{prefix}_detected")
    r = mean_of(f"{prefix}_correct", f"{prefix}_gt")
    return (
        MetricSpec(f"{prefix}_p", f"{name} P", p),
        MetricSpec(f"{prefix}_r", f"{name} R", r),
        MetricSpec(f"{prefix}_f", f"{name} F", harmonic(p, r)),
        MetricSpec(
            f"{prefix}_pooled_p",
            f"{name} P (pooled)",
            pooled(f"{prefix}_correct", f"{prefix}_detected"),
        ),
        MetricSpec(
            f"{prefix}_pooled_r", f"{name} R (pooled)", pooled(f"{prefix}_correct", f"{prefix}_gt")
        ),
    )


STRUCTURE = _dar("str", "Structure")
REGIONS = _dar("reg", "Regions")
SORIC = (
    MetricSpec("soric_bbox", "F1-bbox", dice("soric_tp", "soric_pred", "soric_gt")),
    MetricSpec("soric_top", "F1-GriTS-Top", dice("soric_top", "soric_pred", "soric_gt")),
    MetricSpec("soric_con", "F1-GriTS-Con", dice("soric_con", "soric_pred", "soric_gt")),
    MetricSpec("soric_teds", "F1-TEDS", dice("soric_teds", "soric_pred", "soric_gt")),
)
BINDING = (
    MetricSpec("bind_strict", "Bound", pooled("bind_bound", "bind_paths")),
    MetricSpec("bind_leaf", "Leaf-bound", pooled("bind_leaf", "bind_paths")),
    MetricSpec("bind_value", "Value recall", pooled("bind_value", "bind_paths")),
)
OLMOCR = (
    MetricSpec("olm_all", "All tests", pooled("olm_passed", "olm_tests")),
    MetricSpec("olm_heading", "Heading tests", pooled("olm_heading_passed", "olm_heading")),
    MetricSpec("olm_neighbour", "Neighbour tests", pooled("olm_neighbour_passed", "olm_neighbour")),
)
SPEED = (MetricSpec("seconds_per_page", "Seconds per page", pooled("seconds", "pages")),)


@dataclass(frozen=True, slots=True)
class Scored:
    """Each tool's metrics with intervals, and the baseline's paired differences from each tool."""

    tools: tuple[str, ...]
    documents: int
    values: dict[str, dict[str, Interval]]
    differences: dict[str, dict[str, Interval]]


def score(
    counts: Mapping[str, Mapping[str, Counts]],
    specs: Sequence[MetricSpec],
    *,
    baseline: str | None = BASELINE,
    resamples: int = RESAMPLES,
    seed: int = SEED,
) -> Scored:
    """Every metric for every tool; with a baseline, its difference from each other tool."""
    tools = tuple(counts)
    docs = {len(c) for c in counts.values()}
    if len(docs) != 1:
        msg = f"the tools cover different numbers of documents: {sorted(docs)}"
        raise ValueError(msg)
    values = {
        tool: {
            s.key: bootstrap(counts[tool], s.metric, resamples=resamples, seed=seed) for s in specs
        }
        for tool in tools
    }
    differences: dict[str, dict[str, Interval]] = {}
    if baseline is not None:
        for tool in tools:
            if tool != baseline:
                differences[tool] = {
                    s.key: paired(
                        counts[baseline], counts[tool], s.metric, resamples=resamples, seed=seed
                    )
                    for s in specs
                }
    return Scored(tools=tools, documents=docs.pop(), values=values, differences=differences)


def finding(diff: Interval) -> bool:
    """Whether a difference's interval excludes 0."""
    return not math.isnan(diff.low) and (diff.low > 0 or diff.high < 0)


def _num(v: float, *, sign: bool = False) -> str:
    return "n/a" if math.isnan(v) else (f"{v:+.3f}" if sign else f"{v:.3f}")


def fmt(interval: Interval, *, sign: bool = False) -> str:
    """`point [low, high]`, three decimals; `n/a` for what is undefined."""
    if math.isnan(interval.point):
        return "n/a"
    if math.isnan(interval.low):
        return f"{_num(interval.point, sign=sign)} [n/a]"
    low, high = _num(interval.low, sign=sign), _num(interval.high, sign=sign)
    return f"{_num(interval.point, sign=sign)} [{low}, {high}]"


def _row(cells: Sequence[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def markdown_table(scored: Scored, specs: Sequence[MetricSpec]) -> str:
    """One row per tool, one column per metric."""
    lines = [_row(["Tool", *(s.label for s in specs)]), _row(["---"] * (len(specs) + 1))]
    lines += [
        _row([tool, *(fmt(scored.values[tool][s.key]) for s in specs)]) for tool in scored.tools
    ]
    return "\n".join(lines) + "\n"


def markdown_differences(scored: Scored, specs: Sequence[MetricSpec]) -> str:
    """The baseline minus each tool; a finding (its interval excludes 0) is marked `*`."""
    lines = [_row(["Difference", *(s.label for s in specs)]), _row(["---"] * (len(specs) + 1))]
    for tool, diffs in scored.differences.items():
        cells = []
        for s in specs:
            d = diffs[s.key]
            cells.append(fmt(d, sign=True) + (" *" if finding(d) else ""))
        lines.append(_row([f"{BASELINE} - {tool}", *cells]))
    return "\n".join(lines) + "\n"


TOOLS = ("inkgrid", "pdfplumber", "pymupdf", "camelot")
CHECK = "ground-truth"
DATASETS: dict[str, tuple[str, tuple[tuple[str, tuple[MetricSpec, ...]], ...]]] = {
    "competition": (
        "ICDAR-2013 competition",
        (
            ("Structure (the competition's DAR)", STRUCTURE),
            ("Regions", REGIONS),
            ("Soric et al.'s protocol", SORIC),
            ("Speed", SPEED),
        ),
    ),
    "practice": (
        "ICDAR-2013 practice",
        (
            ("Structure (the competition's DAR)", STRUCTURE),
            ("Regions", REGIONS),
            ("Binding (the access paths)", BINDING),
            ("Speed", SPEED),
        ),
    ),
    "olmocr": ("olmOCR-bench tables, all PDFs", (("Table tests", OLMOCR), ("Speed", SPEED))),
    "olmocr-text-layer": (
        "olmOCR-bench tables, PDFs with a text layer",
        (("Table tests", OLMOCR),),
    ),
}
SORIC_KEYS = (
    ("tp", "F1-bbox"),
    ("top", "F1-GriTS-Top"),
    ("con", "F1-GriTS-Con"),
    ("teds", "F1-TEDS"),
)


REPRODUCTION_TOLERANCE = 0.01  # spec 12 section 7


def reproduction_table(reproduction: Mapping[str, Mapping[str, Mapping[str, Counts]]]) -> str:
    """Soric et al.'s released predictions re-scored here against their released results."""
    names = {"cam": "Camelot", "pymu": "PyMuPDF", "plum": "pdfplumber", "doc": "Docling"}
    head = [
        "Their predictions",
        *(f"{label} here / theirs" for _, label in SORIC_KEYS),
        "Largest gap",
    ]
    lines = [_row(head), _row(["---"] * len(head))]
    gaps: list[float] = []
    for model, runs in reproduction.items():
        cells, row_gaps = [], []
        for key, _ in SORIC_KEYS:
            here = dice(key, "pred", "gt")(list(runs["here"].values()))
            theirs = dice(key, "pred", "gt")(list(runs["released"].values()))
            cells.append(f"{here:.4f} / {theirs:.4f}")
            row_gaps.append(abs(here - theirs))
        gaps += row_gaps
        lines.append(_row([names.get(model, model), *cells, f"{max(row_gaps):.4f}"]))
    within = sum(g <= REPRODUCTION_TOLERANCE for g in gaps)
    lines.append(
        f"\nWithin 0.01 of their released results: {within} of {len(gaps)} "
        f"(largest gap {max(gaps):.4f})."
    )
    return "\n".join(lines) + "\n"


def document(data: Mapping[str, Any], *, head: str, date: str, resamples: int = RESAMPLES) -> str:
    """The whole report: every dataset's tables, the checks, crashes, and inkgrid's defects."""
    counts = data["counts"]
    parts = [
        "# inkgrid benchmark: the M5b baseline\n",
        (
            f"Measured on {date} at commit `{head}` by `bench/inkgrid_bench/run.py`, under the "
            "pre-registered protocol of `docs/specs/12-benchmark.md`. **inkgrid's numbers are its "
            "baseline**: its reading before any fix for errors found on these documents "
            "(DR-0023); later runs are labelled as tuned on them.\n"
        ),
        (
            "Each cell is the point estimate and its 95% interval from 10,000 resamples of "
            "documents (seed 20260928). A difference marked `*` has an interval that excludes 0; "
            "only those are findings. `ground-truth` is the ICDAR ground truth read as a tool: a "
            "check on the pipeline and on each metric's ceiling, not a competitor.\n"
        ),
    ]
    for dataset, (title, groups) in DATASETS.items():
        four = {t: counts[dataset][t] for t in TOOLS}
        n = len(next(iter(four.values())))
        parts.append(f"## {title} ({n} documents)\n")
        for label, specs in groups:
            scored = score(four, specs, resamples=resamples)
            parts += [
                f"### {label}\n",
                markdown_table(scored, specs),
                markdown_differences(scored, specs),
            ]
            if CHECK in counts[dataset]:
                check = score(
                    {CHECK: counts[dataset][CHECK]}, specs, baseline=None, resamples=resamples
                )
                parts.append(
                    "Check, the ICDAR ground truth read as a tool:\n\n"
                    + markdown_table(check, specs)
                )
    parts += [
        "## Soric et al.'s released predictions, re-scored here\n",
        reproduction_table(data["reproduction"]),
    ]
    parts.append("## Crashes and timeouts (each scored as no tables)\n")
    crash_rows = [_row(["Tool", "Dataset", "Documents"]), _row(["---"] * 3)]
    for tool, by_dataset in data["crashes"].items():
        for dataset, docs in by_dataset.items():
            listed = "; ".join(f"{d} ({e})" for d, e in docs)
            crash_rows.append(_row([tool, dataset, f"{len(docs)}: {listed}"]))
    parts.append("\n".join(crash_rows) + "\n" if len(crash_rows) > 2 else "None.\n")  # noqa: PLR2004
    parts.append("## inkgrid's verifier on these documents (spec 11 section 5)\n")
    defect_rows = [
        _row(["Dataset", "Documents with defects", "Defects by class"]),
        _row(["---"] * 3),
    ]
    for dataset, d in data["defects"].items():
        classes = ", ".join(f"{k} {v}" for k, v in sorted(d["by_code"].items())) or "none"
        unverified = f" ({d['errors']} not verified)" if d["errors"] else ""
        defect_rows.append(_row([dataset, f"{d['documents_with_defects']}{unverified}", classes]))
    parts.append("\n".join(defect_rows) + "\n")
    errors = {t: e for t, e in data["olmocr_errors"].items() if e}
    if errors:
        parts.append("## olmOCR scorer errors\n")
        parts += [f"- {t}: {len(e)} (first: {e[0]})\n" for t, e in errors.items()]
    return "\n".join(parts)
