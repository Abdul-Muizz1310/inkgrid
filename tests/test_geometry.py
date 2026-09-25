import math
from itertools import pairwise

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from pydantic import TypeAdapter, ValidationError

from inkgrid.model.geometry import Interval, Rect, quantize

RECT = TypeAdapter(Rect)


def test_G1_quantize_rounds_to_hundredths() -> None:
    assert quantize(1.234567) == 1.23


def test_G2_quantize_follows_binary_representation() -> None:
    assert quantize(2.675) == 2.67


def test_G3_quantize_normalizes_negative_zero() -> None:
    q = quantize(-0.001)
    assert q == 0.0
    assert math.copysign(1.0, q) == 1.0


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_G4_quantize_rejects_non_finite(bad: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        quantize(bad)


@given(st.floats(min_value=-1e6, max_value=1e6, allow_nan=False))
@example(0.005)
@example(-0.005)
def test_G5_quantize_is_idempotent(x: float) -> None:
    assert quantize(quantize(x)) == quantize(x)


def test_G6_rect_measures() -> None:
    r = Rect(0, 0, 10, 5)
    assert (r.width, r.height, r.area, r.center) == (10.0, 5.0, 50.0, (5.0, 2.5))


@pytest.mark.parametrize(
    "coords", [(10, 0, 0, 5), (0, 5, 10, 0), (math.nan, 0, 1, 1)], ids=["x", "y", "nan"]
)
def test_G7_rect_rejects_inverted_or_nan(coords: tuple[float, float, float, float]) -> None:
    with pytest.raises(ValueError, match=r"inverted|finite"):
        Rect(*coords)


def test_G8_degenerate_rect_is_legal() -> None:
    assert Rect(0, 0, 0, 0).area == 0.0


def test_G9_rect_quantizes_on_construction() -> None:
    r = Rect(0.001, 0, 1.006, 1)
    assert (r.x0, r.x1) == (0.0, 1.01)


def test_G10_rect_ordering_is_checked_after_quantization() -> None:
    assert Rect(1.004, 0, 1.001, 1).width == 0.0


def test_G11_rect_inverted_after_quantization_is_rejected() -> None:
    with pytest.raises(ValueError, match="inverted"):
        Rect(1.006, 0, 1.001, 1)


@pytest.mark.parametrize(
    ("x", "y", "inside"),
    [(0, 0, True), (10, 5, False), (5, 10, False), (9.99, 9.99, True)],
)
def test_G12_contains_point_is_half_open(x: float, y: float, inside: bool) -> None:
    assert Rect(0, 0, 10, 10).contains_point(x, y) is inside


@st.composite
def tiling_and_point(draw: st.DrawFn) -> tuple[list[Rect], tuple[float, float]]:
    width = draw(st.integers(min_value=1, max_value=500))
    height = draw(st.integers(min_value=1, max_value=500))
    xs = sorted({0, width, *draw(st.lists(st.integers(1, max(1, width - 1)), max_size=6))})
    ys = sorted({0, height, *draw(st.lists(st.integers(1, max(1, height - 1)), max_size=6))})
    tiles = [Rect(x0, y0, x1, y1) for x0, x1 in pairwise(xs) for y0, y1 in pairwise(ys)]
    px = quantize(draw(st.floats(0, width, exclude_max=True)))
    py = quantize(draw(st.floats(0, height, exclude_max=True)))
    return tiles, (min(px, width - 0.01), min(py, height - 0.01))


@given(tiling_and_point())
def test_G13_tiling_contains_each_point_exactly_once(
    case: tuple[list[Rect], tuple[float, float]],
) -> None:
    tiles, (x, y) = case
    assert sum(t.contains_point(x, y) for t in tiles) == 1


def test_G14_intersects_requires_positive_area() -> None:
    assert not Rect(0, 0, 5, 5).intersects(Rect(5, 0, 10, 5))
    assert Rect(0, 0, 5, 5).intersects(Rect(4, 0, 10, 5))


def test_G15_union_and_union_all() -> None:
    a, b = Rect(0, 0, 5, 5), Rect(3, -2, 10, 4)
    assert a.union(b) == Rect(0, -2, 10, 5)
    assert Rect.union_all([a, b, Rect(1, 1, 2, 2)]) == Rect(0, -2, 10, 5)
    with pytest.raises(ValueError, match="empty"):
        Rect.union_all([])


def test_G16_contains_rect_is_closed() -> None:
    r = Rect(0, 0, 10, 10)
    assert r.contains_rect(r)
    assert not r.contains_rect(Rect(-1, 0, 10, 10))


def test_G17_rect_json_round_trip() -> None:
    assert RECT.validate_json("[0,0,10,5]") == Rect(0, 0, 10, 5)
    assert RECT.dump_json(Rect(0, 0, 10, 5)) == b"[0.0,0.0,10.0,5.0]"
    assert RECT.validate_python(Rect(1, 2, 3, 4)) == Rect(1, 2, 3, 4)
    assert RECT.validate_python((1, 2, 3, 4)) == Rect(1, 2, 3, 4)


@pytest.mark.parametrize("bad", ["[0,0,10]", "[10,0,0,5]", '["a",0,1,1]', '{"x0":0}'])
def test_G18_rect_json_rejects_bad_shapes(bad: str) -> None:
    with pytest.raises(ValidationError):
        RECT.validate_json(bad)


@pytest.mark.parametrize(("start", "end"), [(0, 0), (5, 1)])
def test_G19_interval_requires_positive_width(start: float, end: float) -> None:
    with pytest.raises(ValueError, match="positive width"):
        Interval(start, end)


@pytest.mark.parametrize(("v", "inside"), [(1, True), (4, False), (3.99, True)])
def test_G20_interval_contains_is_half_open(v: float, inside: bool) -> None:
    assert Interval(1, 4).contains(v) is inside


def test_G21_interval_overlaps() -> None:
    assert not Interval(0, 5).overlaps(Interval(5, 9))
    assert Interval(0, 5).overlaps(Interval(4, 9))


def test_interval_json_round_trip() -> None:
    adapter = TypeAdapter(Interval)
    assert adapter.validate_json("[1,4]") == Interval(1, 4)
    assert adapter.dump_json(Interval(1, 4)) == b"[1.0,4.0]"
    with pytest.raises(ValidationError):
        adapter.validate_json("[4,1]")
