import math
from collections.abc import Sequence

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from inkgrid_bench.scores.metrics import Counts, mean_of, pooled
from inkgrid_bench.stats import Interval, bootstrap, paired

DOCS = {
    "a": {"num": 3, "den": 4},
    "b": {"num": 0, "den": 5},
    "c": {"num": 5, "den": 5},
}


def test_BS1_a_constant_metric_has_the_constant_as_its_interval() -> None:
    assert bootstrap(DOCS, lambda docs: 0.5, resamples=200) == Interval(0.5, 0.5, 0.5)
    same = {k: {"num": 2, "den": 4} for k in "abcd"}
    assert bootstrap(same, pooled("num", "den"), resamples=200) == Interval(0.5, 0.5, 0.5)
    # a constant with no exact binary form stays exactly itself (found by the property below)
    one = {"a": {"num": 5, "den": 11}}
    assert bootstrap(one, pooled("num", "den"), resamples=50) == Interval(5 / 11, 5 / 11, 5 / 11)


def test_BS2_identical_results_differ_by_zero_with_a_zero_width_interval() -> None:
    assert paired(DOCS, DOCS, pooled("num", "den"), resamples=200) == Interval(0.0, 0.0, 0.0)


def test_BS3_the_same_seed_gives_the_same_interval() -> None:
    once = bootstrap(DOCS, pooled("num", "den"), resamples=300, seed=7)
    again = bootstrap(dict(reversed(DOCS.items())), pooled("num", "den"), resamples=300, seed=7)
    assert once == again
    assert once.low < once.point < once.high


def test_BS_resamples_are_whole_documents_the_same_for_both_sides() -> None:
    seen: list[Sequence[Counts]] = []

    def spy(docs: Sequence[Counts]) -> float:
        seen.append(docs)
        return 0.0

    paired(DOCS, {k: dict(v) for k, v in DOCS.items()}, spy, resamples=50)
    draws = seen[2:]  # after the two point estimates, each resample: side a, then side b
    assert len(draws) == 100
    originals = {id(v) for v in DOCS.values()}
    for side_a, side_b in zip(draws[::2], draws[1::2], strict=True):
        assert len(side_a) == len(side_b) == len(DOCS)
        assert all(id(d) in originals for d in side_a)
        assert [dict(d) for d in side_a] == [dict(d) for d in side_b]


def test_BS_mismatched_or_empty_documents_are_errors() -> None:
    with pytest.raises(ValueError, match="same documents"):
        paired(DOCS, {"a": DOCS["a"]}, pooled("num", "den"), resamples=10)
    with pytest.raises(ValueError, match="no documents"):
        bootstrap({}, pooled("num", "den"), resamples=10)


def test_BS_undefined_resamples_are_left_out_and_an_undefined_point_is_nan() -> None:
    # "b" detected nothing: a resample of only "b" has no precision
    docs = {"a": {"num": 1, "den": 2}, "b": {"num": 0, "den": 0}}
    interval = bootstrap(docs, mean_of("num", "den"), resamples=200)
    assert interval == Interval(0.5, 0.5, 0.5)
    nothing = bootstrap({"b": docs["b"]}, mean_of("num", "den"), resamples=20)
    assert all(math.isnan(v) for v in (nothing.point, nothing.low, nothing.high))


counts = st.integers(min_value=1, max_value=50).flatmap(
    lambda den: st.fixed_dictionaries({"num": st.integers(0, den), "den": st.just(den)})
)


@settings(max_examples=60, deadline=None)
@given(
    st.dictionaries(st.text("abcdefgh", min_size=1, max_size=3), counts, min_size=1, max_size=12)
)
def test_BS_the_interval_contains_the_point_estimate(docs: dict[str, dict[str, int]]) -> None:
    for metric in (pooled("num", "den"), mean_of("num", "den")):
        interval = bootstrap(docs, metric, resamples=400)
        assert interval.low <= interval.point <= interval.high
