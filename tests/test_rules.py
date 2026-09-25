import random

import pytest

from inkgrid.model.page import Rule
from inkgrid.read.raw import CurveItem, LineItem, PathItem, QuadItem, RawPath, RectItem
from inkgrid.read.rules import extract_rules

BLACK = (0.0, 0.0, 0.0)


def stroked(
    *items: PathItem,
    width: float | None = 1.0,
    color: tuple[float, ...] | None = BLACK,
    opacity: float | None = 1.0,
) -> RawPath:
    return RawPath(
        kind="s",
        width=width,
        color=color,
        stroke_opacity=opacity,
        fill=None,
        fill_opacity=None,
        items=items,
    )


def filled(
    *items: PathItem, fill: tuple[float, ...] | None = BLACK, opacity: float | None = 1.0
) -> RawPath:
    return RawPath(
        kind="f",
        width=None,
        color=None,
        stroke_opacity=None,
        fill=fill,
        fill_opacity=opacity,
        items=items,
    )


def h(at: float, start: float, end: float, thickness: float) -> Rule:
    return Rule(page=1, axis="h", at=at, start=start, end=end, thickness=thickness)


def v(at: float, start: float, end: float, thickness: float) -> Rule:
    return Rule(page=1, axis="v", at=at, start=start, end=end, thickness=thickness)


def test_R1_stroked_line_with_its_closing_segment_is_one_rule() -> None:
    path = stroked(LineItem((50, 200), (150, 200)), LineItem((150, 200), (50, 200)), width=0.8)
    assert extract_rules([path], page=1) == (h(200, 50, 150, 0.8),)


def test_R2_slant_tolerance() -> None:
    assert extract_rules([stroked(LineItem((50, 200), (150, 200.4)))], page=1) == (
        h(200.2, 50, 150, 1),
    )
    assert extract_rules([stroked(LineItem((50, 200), (150, 200.6)))], page=1) == ()


def test_R3_too_short_line_is_not_a_rule() -> None:
    assert extract_rules([stroked(LineItem((50, 200), (51.9, 200)))], page=1) == ()


def test_R4_thin_filled_rect_is_a_rule_on_its_centre_line() -> None:
    assert extract_rules([filled(RectItem((50, 100, 150, 101)))], page=1) == (
        h(100.5, 50, 150, 1.0),
    )


def test_thin_stroked_rect_adds_the_stroke_width() -> None:
    path = stroked(RectItem((50, 100, 150, 101)), width=0.5)
    assert extract_rules([path], page=1) == (h(100.5, 50, 150, 1.5),)


def test_R5_stroked_cell_rect_gives_four_edges() -> None:
    assert extract_rules([stroked(RectItem((200, 200, 300, 260)))], page=1) == (
        h(200, 200, 300, 1),
        h(260, 200, 300, 1),
        v(200, 200, 260, 1),
        v(300, 200, 260, 1),
    )


def test_R6_filled_background_is_not_a_rule() -> None:
    assert extract_rules([filled(RectItem((200, 200, 300, 260)))], page=1) == ()


def test_R7_axis_aligned_quad_from_a_closed_polyline() -> None:
    quad = QuadItem(((50, 50), (50, 80), (150, 50), (150, 80)))
    assert extract_rules([stroked(quad, width=0.5)], page=1) == (
        h(50, 50, 150, 0.5),
        h(80, 50, 150, 0.5),
        v(50, 50, 80, 0.5),
        v(150, 50, 80, 0.5),
    )


def test_R8_rotated_quad_is_not_a_rule() -> None:
    diamond = QuadItem(((100, 50), (50, 100), (150, 100), (100, 150)))
    assert extract_rules([stroked(diamond)], page=1) == ()


@pytest.mark.parametrize(
    "path",
    [
        stroked(LineItem((50, 200), (150, 200)), color=None),
        stroked(LineItem((50, 200), (150, 200)), opacity=0.0),
        filled(RectItem((50, 100, 150, 101)), fill=None),
        filled(RectItem((50, 100, 150, 101)), opacity=0.0),
    ],
    ids=["no-color", "transparent-stroke", "no-fill", "transparent-fill"],
)
def test_R9_invisible_paths_yield_nothing(path: RawPath) -> None:
    assert extract_rules([path], page=1) == ()


def test_R10_line_in_a_fill_only_path_is_not_a_rule() -> None:
    assert extract_rules([filled(LineItem((50, 200), (150, 200)))], page=1) == ()


def test_R11_curve_is_not_a_rule() -> None:
    assert extract_rules([stroked(CurveItem())], page=1) == ()


def test_R12_duplicates_keep_the_greatest_thickness() -> None:
    thin = stroked(LineItem((50, 200), (150, 200)), width=0.5)
    thick = stroked(LineItem((50, 200), (150, 200)), width=1.0)
    assert extract_rules([thin, thick], page=1) == (h(200, 50, 150, 1.0),)


def test_R13_thin_vertical_rect() -> None:
    assert extract_rules([filled(RectItem((100, 50, 101, 130)))], page=1) == (v(100.5, 50, 130, 1),)


def test_R14_output_is_sorted_whatever_the_input_order() -> None:
    paths = [
        stroked(LineItem((0, 300), (100, 300))),
        stroked(LineItem((50, 0), (50, 90))),
        stroked(LineItem((0, 100), (100, 100))),
        stroked(LineItem((10, 0), (10, 90))),
    ]
    expected = extract_rules(paths, page=1)
    assert [(r.axis, r.at) for r in expected] == [("h", 100), ("h", 300), ("v", 10), ("v", 50)]
    for seed in range(5):
        shuffled = paths[:]
        random.Random(seed).shuffle(shuffled)
        assert extract_rules(shuffled, page=1) == expected


def test_rules_carry_their_page() -> None:
    assert extract_rules([stroked(LineItem((0, 5), (50, 5)))], page=3)[0].page == 3
