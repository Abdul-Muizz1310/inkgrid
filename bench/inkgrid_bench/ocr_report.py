"""The OCR benchmarks' report (docs/specs/18-ocr-benchmarks.md section 5).

Pure: each benchmark's per-document counts, and each document's group, half and stratum, in;
Markdown out. Each section is one benchmark's documents, each part one group of them with its
metrics; every number has spec 12's interval, and inkgrid's paired difference from each tool is a
finding only when its interval excludes 0. A tuned run reports the dev and test halves apart.
Nothing is pooled across benchmarks, and no number is called a benchmark's whole score.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, assert_never

from inkgrid_bench.report import (
    SPEED,
    MetricSpec,
    markdown_differences,
    markdown_table,
    score,
)
from inkgrid_bench.scores.metrics import Counts, Metric, macro, mean_of, pooled
from inkgrid_bench.stats import RESAMPLES

type OcrLabel = Literal["baseline", "tuned"]
type Info = Mapping[str, Any]
type Keep = Callable[[Info], bool]

TOOLS = (
    "inkgrid",
    "pymupdf4llm",
    "markitdown",
    "liteparse",
    "docling",
    "marker",
    "docling-ocr",
    "unstructured",
    "inkgrid-ocr",
)
"""Every tool the OCR run reads with, in its row order: inkgrid, the text-layer converters, then
the layout and OCR tools (spec 18 section 3)."""
TEXT_LAYER = ("inkgrid", "pymupdf4llm", "markitdown", "liteparse")
OCR = ("docling-ocr", "unstructured", "inkgrid-ocr")
BENCHMARKS = {
    "olmocr": "olmOCR-bench",
    "omnidocbench": "OmniDocBench",
    "parsebench": "ParseBench",
    "dpbench": "DP-Bench",
}
CLASSES = (
    ("born_digital", "Born-digital"),
    ("no_text", "No text"),
    ("image_backed", "Image-backed"),
    ("ocr_layer", "OCR layer"),
)


def _rate(group: str) -> Metric:
    return pooled(f"olm_{group}_passed", f"olm_{group}_tests")


def _mean(prefix: str) -> Metric:
    return mean_of(prefix, f"{prefix}_n")


OLMOCR_PASS = (
    MetricSpec("olm_headers_footers", "Headers and footers", _rate("headers_footers")),
    MetricSpec("olm_multi_column", "Multi-column", _rate("multi_column")),
    MetricSpec("olm_tables", "Tables", _rate("tables")),
    MetricSpec(
        "olm_macro",
        "Born-digital macro",
        macro(_rate("headers_footers"), _rate("multi_column"), _rate("tables")),
    ),
    MetricSpec("olm_baseline", "Baseline tests", _rate("baseline")),
)
OLMOCR_TINY = (
    MetricSpec("olm_long_tiny_text", "Long tiny text", _rate("long_tiny_text")),
    MetricSpec("olm_baseline", "Baseline tests", _rate("baseline")),
)
OMNI_TEXT = (
    MetricSpec("omni_text", "Text Edit distance", mean_of("omni_text_edit", "omni_text_len")),
)
OMNI_TABLES = (
    MetricSpec("omni_teds", "Table TEDS", pooled("omni_teds_sum", "omni_teds_n")),
    MetricSpec(
        "omni_table_edit", "Table Edit distance", mean_of("omni_table_edit", "omni_table_len")
    ),
)
OMNI_ORDER = (
    MetricSpec(
        "omni_order", "Reading-order Edit distance", mean_of("omni_order_edit", "omni_order_len")
    ),
)
PARSEBENCH_TABLE = ("grits_trm_composite", "grits_con", "table_record_match")
PARSEBENCH_TEXT = ("content_faithfulness", "normalized_text_correctness", "normalized_order")
PB_TABLES = tuple(
    MetricSpec(f"pb_{m}", label, _mean(f"pb_{m}"))
    for m, label in zip(PARSEBENCH_TABLE, ("GTRM", "GriTS-Con", "TableRecordMatch"), strict=True)
)
PB_TEXT = tuple(
    MetricSpec(f"pb_{m}", label, _mean(f"pb_{m}"))
    for m, label in zip(
        PARSEBENCH_TEXT, ("Content faithfulness", "Text correctness", "Order"), strict=True
    )
)
DP = tuple(
    MetricSpec(f"dp_{k}", label, _mean(f"dp_{k}"))
    for k, label in (("nid", "NID"), ("teds", "TEDS"), ("mhs", "MHS"))
)

LOWER = (
    "Lower is better for an Edit distance, so a negative difference favours inkgrid; a page whose "
    "truth holds nothing of this kind is left out.\n"
)
OLMOCR_NOTE = (
    "Each category's pass rate pools its tests; the born-digital macro is the mean of the "
    "headers-and-footers, multi-column and table rates. A headers-and-footers test checks only "
    "that a page's furniture is absent, so an empty page passes it; the benchmark's baseline "
    "test, one a page, fails a page with no text, one ending in repeated words, or one with "
    "characters the benchmark disallows.\n"
)
OMNI_TABLE_NOTE = (
    "TEDS is pooled over the truth's tables, as the scorer pools it; a table Edit distance is each "
    "page's own, and lower is better for it, so there a negative difference favours inkgrid.\n"
)
DP_NOTE = (
    "NID scores the page's text in reading order; TEDS only pages whose truth has a table, and "
    "MHS only pages whose truth has a heading.\n"
)
PB_TABLE_NOTE = (
    "GTRM is ParseBench's headline table metric, the mean of GriTS-Con and TableRecordMatch; "
    "every page is scored, a page whose reading has no table at 0.\n"
)


@dataclass(frozen=True, slots=True)
class Part:
    """One group of a section's documents, with its metrics and what they do not measure."""

    title: str
    keep: Keep
    specs: tuple[MetricSpec, ...]
    note: str = ""


@dataclass(frozen=True, slots=True)
class Section:
    """One benchmark's documents, or one stratum of them, in parts."""

    benchmark: str
    title: str
    keep: Keep
    parts: tuple[Part, ...]


def _every(_info: Info) -> bool:
    return True


def _groups(*names: str) -> Keep:
    return lambda info: info["group"] in names


def _primary(info: Info) -> bool:
    return bool(info["primary"])


def _half(half: str) -> Keep:
    return lambda info: info["half"] == half


SPEED_PART = Part("Speed", _every, SPEED)


def _omni_parts(*, speed: bool) -> tuple[Part, ...]:
    return (
        Part("Text, English pages", _groups("english"), OMNI_TEXT, LOWER),
        Part(
            "Text, Chinese pages (simplified Chinese and mixed)",
            _groups("simplified_chinese", "en_ch_mixed"),
            OMNI_TEXT,
            LOWER,
        ),
        Part("Tables", _every, OMNI_TABLES, OMNI_TABLE_NOTE),
        Part("Reading order", _every, OMNI_ORDER, LOWER),
        *((SPEED_PART,) if speed else ()),
    )


SECTIONS = (
    Section(
        "olmocr",
        "olmOCR-bench",
        _every,
        (
            Part(
                "Pass rates",
                _groups("headers_footers", "multi_column", "tables"),
                OLMOCR_PASS,
                OLMOCR_NOTE,
            ),
            Part("Long tiny text, reported apart", _groups("long_tiny_text"), OLMOCR_TINY),
            SPEED_PART,
        ),
    ),
    Section(
        "omnidocbench",
        "OmniDocBench v1.0, primary stratum: born-digital pages with no masked area",
        _primary,
        _omni_parts(speed=False),
    ),
    Section(
        "omnidocbench",
        "OmniDocBench v1.0, every born-digital page",
        _every,
        _omni_parts(speed=True),
    ),
    Section(
        "parsebench",
        "ParseBench",
        _every,
        (
            Part("Tables", _groups("table"), PB_TABLES, PB_TABLE_NOTE),
            Part(
                "Text (simple, multi-column, misc, dense, sparse)",
                _groups(
                    "text_simple", "text_multicolumns", "text_misc", "text_dense", "text_sparse"
                ),
                PB_TEXT,
            ),
            Part("Text, multilingual", _groups("text_multilang"), PB_TEXT),
            SPEED_PART,
        ),
    ),
    Section(
        "dpbench",
        "DP-Bench",
        _every,
        (Part("Text, tables and headings", _every, DP, DP_NOTE), SPEED_PART),
    ),
)
"""The report's sections in order (spec 18 sections 2 and 4)."""


def _named(names: Sequence[str]) -> str:
    """`a`, `a and b`, `a, b and c`."""
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _kept(data: Mapping[str, Any]) -> str:
    """How many of each benchmark's documents the census kept."""
    kept = [
        f"{len(data['documents'][b]):,} of {name}'s {data['census'][b]['documents']:,}"
        for b, name in BENCHMARKS.items()
        if b in data["documents"]
    ]
    return f"The census kept {_named(kept)} documents."


def _modes(tools: Sequence[str]) -> str:
    """What each tool read."""
    ocr = [t for t in tools if t in OCR]
    text = [t for t in tools if t in TEXT_LAYER]
    parts = []
    if text:
        parts.append(f"{_named(text)} read the PDF's text layer")
    if "docling" in tools:
        parts.append("docling read it, with OCR only for a page's regions without text")
    if "marker" in tools:
        parts.append("marker read it with OCR off")
    if ocr:
        parts.append(f"{_named(ocr)} read the pages with OCR")
    if not parts:
        return ""
    return (
        f" {'; '.join(parts)}. `inkgrid-ocr` is inkgrid with Tesseract's words for its own. The "
        "heavy tools' seconds are a warm process's, its models loaded."
    )


def heading(label: OcrLabel, data: Mapping[str, Any], *, head: str, date: str) -> list[str]:
    """The title and first paragraph: what is scored, whether inkgrid is tuned, the census."""
    tools = [t for t in TOOLS if any(t in by_tool for by_tool in data["counts"].values())]
    scope = (
        f"Measured on {date} at commit `{head}` by `bench/inkgrid_bench/run.py --datasets ocr`, "
        "under the pre-registered protocol of `docs/specs/18-ocr-benchmarks.md`. **Only "
        "born-digital pages and the benchmarks' text and table tests are scored**: a census taken "
        "before any tool read a page leaves out every page that is a scan, carries an OCR layer, "
        "is backed by a page-size image or holds almost no text, and the benchmarks' formula, "
        "chart and handwriting tests are not run, so no number here stands for a benchmark as a "
        f"whole. {_kept(data)}"
    )
    match label:
        case "baseline":
            return [
                "# inkgrid on OCR benchmarks: born-digital text and tables, the M7a baseline\n",
                (
                    f"{scope} **inkgrid's numbers are its baseline**: its reading as released in "
                    "0.1.0, before any fix designed from these benchmarks' failures (DR-0023). "
                    f"Later runs are labelled tuned.{_modes(tools)}\n"
                ),
            ]
        case "tuned":
            return [
                "# inkgrid on OCR benchmarks: born-digital text and tables, tuned (M7b)\n",
                (
                    f"{scope} **inkgrid's numbers are tuned on the dev halves**: its reading after "
                    "the fixes M7b designed from its failures on each benchmark's dev half, so "
                    "there they overstate it; each benchmark's test half, which no fix has looked "
                    "at, is reported apart and is the measure of whether they carry."
                    f"{_modes(tools)}\n"
                ),
            ]
        case _:
            assert_never(label)


def _section_parts(
    section: Section,
    keep: Keep,
    data: Mapping[str, Any],
    tools: Sequence[str],
    resamples: int,
) -> tuple[int, list[str]]:
    """A section's document count and its parts' Markdown, over the documents `keep` admits."""
    infos: Mapping[str, Info] = data["documents"][section.benchmark]
    counts: Mapping[str, Mapping[str, Counts]] = data["counts"][section.benchmark]
    ids = [d for d, info in infos.items() if section.keep(info) and keep(info)]
    out: list[str] = []
    for part in section.parts:
        mine = [d for d in ids if part.keep(infos[d])]
        if not mine:
            out.append(f"### {part.title}\n\nNo documents in this part.\n")
            continue
        try:
            by_tool = {t: {d: counts[t][d] for d in mine} for t in tools}
        except KeyError as exc:
            msg = f"{section.benchmark}: a tool has no counts for document {exc}"
            raise ValueError(msg) from exc
        scored = score(by_tool, part.specs, resamples=resamples)
        out += [
            f"### {part.title} ({len(mine)} documents)\n",
            markdown_table(scored, part.specs),
            markdown_differences(scored, part.specs),
        ]
        if part.note:
            out.append(part.note)
    return len(ids), out


def _row(cells: Sequence[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def census_table(data: Mapping[str, Any]) -> str:
    """Each benchmark's documents by class, and how many are scored."""
    head = ["Benchmark", "Documents", *(label for _, label in CLASSES), "Scored"]
    lines = [_row(head), _row(["---"] * len(head))]
    for b, name in BENCHMARKS.items():
        if b not in data["census"]:
            continue
        c = data["census"][b]
        classes = [f"{c['classes'].get(k, 0):,}" for k, _ in CLASSES]
        lines.append(
            _row([name, f"{c['documents']:,}", *classes, f"{len(data['documents'][b]):,}"])
        )
    return "\n".join(lines) + "\n"


def crash_table(crashes: Mapping[str, Mapping[str, Sequence[Sequence[str]]]]) -> str:
    """Each tool's crashed or timed-out documents per benchmark, or `None.`."""
    rows = [_row(["Tool", "Benchmark", "Documents"]), _row(["---"] * 3)]
    for tool, by_benchmark in crashes.items():
        for b, docs in by_benchmark.items():
            listed = "; ".join(f"{d} ({e})" for d, e in docs)
            rows.append(_row([tool, BENCHMARKS.get(b, b), f"{len(docs)}: {listed}"]))
    return "\n".join(rows) + "\n" if len(rows) > 2 else "None.\n"  # noqa: PLR2004


def document(
    data: Mapping[str, Any],
    *,
    head: str,
    date: str,
    label: OcrLabel = "baseline",
    resamples: int = RESAMPLES,
) -> str:
    """The whole report: the census, each benchmark's sections, and the crashes.

    Raises:
        ValueError: a tool without counts for a document another tool has (nothing is scored on
            a different set of documents).
    """
    parts = [
        *heading(label, data, head=head, date=date),
        (
            "Each cell is the point estimate and its 95% interval from 10,000 resamples of "
            "documents (seed 20260928). A difference is inkgrid's number minus the tool's; one "
            "marked `*` has an interval that excludes 0, and only those are findings.\n"
        ),
        "## The census\n",
        census_table(data),
    ]
    halves: tuple[tuple[str, Keep], ...] = (("", _every),)
    if label == "tuned":
        halves = ((", dev half", _half("dev")), (", test half", _half("test")))
    for section in SECTIONS:
        if section.benchmark not in data["counts"]:
            continue
        by_tool = data["counts"][section.benchmark]
        tools = [t for t in TOOLS if t in by_tool]
        for suffix, keep in halves:
            n, body = _section_parts(section, keep, data, tools, resamples)
            parts += [f"## {section.title}{suffix} ({n} documents)\n", *body]
    parts += [
        "## Crashes and timeouts (each scored as an empty page)\n",
        crash_table(data["crashes"]),
    ]
    return "\n".join(parts)
