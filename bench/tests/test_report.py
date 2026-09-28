import math

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
