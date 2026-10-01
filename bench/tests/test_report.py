import json
import math
from pathlib import Path

from inkgrid_bench import report
from inkgrid_bench.scores.metrics import pooled
from inkgrid_bench.stats import Interval

SPECS = (report.MetricSpec("rate", "Pass rate", pooled("passed", "tests")),)


def counts(passed: list[int]) -> dict[str, dict[str, float]]:
    return {f"d{i}": {"passed": p, "tests": 4} for i, p in enumerate(passed)}


def test_every_tool_is_scored_and_differenced_against_the_baseline() -> None:
    tools = {
        "inkgrid": counts([4, 4, 4, 3, 4, 4]),
        "peer": counts([0, 1, 0, 1, 0, 0]),
        "twin": counts([4, 4, 4, 3, 4, 4]),
    }
    scored = report.score(tools, SPECS, resamples=300)
    assert scored.values["inkgrid"]["rate"].point == 23 / 24
    assert scored.values["peer"]["rate"].point == 2 / 24
    assert set(scored.differences) == {"peer", "twin"}
    assert report.finding(scored.differences["peer"]["rate"])
    assert not report.finding(scored.differences["twin"]["rate"])


def test_a_difference_is_a_finding_only_when_its_interval_excludes_zero() -> None:
    assert report.finding(Interval(0.2, 0.1, 0.3))
    assert report.finding(Interval(-0.2, -0.3, -0.1))
    assert not report.finding(Interval(0.2, -0.01, 0.3))
    assert not report.finding(Interval(math.nan, math.nan, math.nan))


def test_numbers_print_with_their_interval_and_undefined_ones_as_na() -> None:
    assert report.fmt(Interval(0.8123, 0.7711, 0.8504)) == "0.812 [0.771, 0.850]"
    assert report.fmt(Interval(math.nan, math.nan, math.nan)) == "n/a"
    assert report.fmt(Interval(0.5, math.nan, math.nan)) == "0.500 [n/a]"


def test_the_table_lists_tools_in_order_and_marks_findings() -> None:
    tools = {"inkgrid": counts([4, 4, 4, 4]), "peer": counts([0, 0, 0, 1])}
    scored = report.score(tools, SPECS, resamples=200)
    text = report.markdown_table(scored, SPECS)
    lines = text.splitlines()
    assert lines[0] == "| Tool | Pass rate |"
    assert lines[2].startswith("| inkgrid | 1.000 [1.000, 1.000]")
    assert lines[3].startswith("| peer | 0.062 [")
    diff = report.markdown_differences(scored, SPECS)
    assert "| inkgrid - peer | +0.938 [" in diff
    assert "] * |" in diff  # the finding is marked


def test_the_reproduction_table_says_how_many_numbers_are_within_a_hundredth() -> None:
    docs = {"d": {"pred": 2, "gt": 2, "tp": 2, "top": 1.8, "con": 1.6, "teds": 1.5}}
    close = {"d": {"pred": 2, "gt": 2, "tp": 2, "top": 1.81, "con": 1.6, "teds": 1.5}}
    far = {"d": {"pred": 2, "gt": 2, "tp": 2, "top": 1.8, "con": 1.6, "teds": 1.46}}
    text = report.reproduction_table(
        {"cam": {"here": docs, "released": close}, "doc": {"here": docs, "released": far}}
    )
    assert "| Camelot | 1.0000 / 1.0000 | 0.9000 / 0.9050 |" in text
    assert text.rstrip().endswith(
        "Within 0.01 of their released results: 7 of 8 (largest gap 0.0200)."
    )


def test_TR1_a_tuned_report_says_so_in_its_title_and_first_paragraph() -> None:
    title, first = report.heading("tuned", head="abc1234", date="2026-09-30")[:2]
    assert "tuned on these documents" in title
    assert "tuned on these documents" in first
    assert "`abc1234`" in first
    assert "pinned versions" in first
    assert "unchanged" not in first  # measured again, not compared
    title, first = report.heading("baseline", head="abc1234", date="2026-09-30")[:2]
    assert "baseline" in title
    assert "tuned" not in title


BASELINE_RUN = Path(__file__).parents[1] / "results" / "2026-09-29-b33b3cb"


def test_TR1_the_whole_report_renders_under_its_label() -> None:
    data = {
        "counts": json.loads((BASELINE_RUN / "counts.json").read_text(encoding="utf-8")),
        **json.loads((BASELINE_RUN / "checks.json").read_text(encoding="utf-8")),
    }
    text = report.document(data, head="abc1234", date="2026-09-30", label="tuned", resamples=20)
    assert text.startswith("# inkgrid benchmark: tuned on these documents")
    for dataset, (title, groups) in report.DATASETS.items():
        if dataset not in data["counts"]:
            assert f"## {title} (" not in text  # a run reports the datasets it holds
            continue
        assert f"## {title} (" in text
        assert all(f"### {name}\n" in text for name, _ in groups)
    assert "## Held-out fee set" not in text


def test_RP1_the_heavy_competitors_get_rows_and_paired_differences() -> None:
    data = {
        "counts": json.loads((BASELINE_RUN / "counts.json").read_text(encoding="utf-8")),
        **json.loads((BASELINE_RUN / "checks.json").read_text(encoding="utf-8")),
    }
    for dataset in data["counts"].values():
        for tool in ("docling", "docling-ocr", "marker", "unstructured", "inkgrid-ocr"):
            dataset[tool] = dataset["camelot"]  # any counts: the rows, not the numbers, are tested
    text = report.document(data, head="abc1234", date="2026-10-01", label="tuned", resamples=20)
    for tool in ("docling", "docling-ocr", "marker", "unstructured", "inkgrid-ocr"):
        assert f"\n| {tool} |" in text
        assert f"\n| inkgrid - {tool} |" in text
    first = text.split("\n\n")[1]
    assert "tuned" in first
    assert "docling-ocr, unstructured, and inkgrid-ocr read the pages with OCR" in first
    assert "docling OCRs only" in first
    assert "marker reads with OCR off" in first
    assert "warm process" in first


def test_RP2_an_earlier_run_renders_its_four_tools() -> None:
    data = {
        "counts": json.loads((BASELINE_RUN / "counts.json").read_text(encoding="utf-8")),
        **json.loads((BASELINE_RUN / "checks.json").read_text(encoding="utf-8")),
    }
    text = report.document(data, head="abc1234", date="2026-10-01", resamples=20)
    assert "\n| camelot |" in text
    assert "docling" not in text.split("## Soric et al.")[0]
    assert "with OCR" not in text
