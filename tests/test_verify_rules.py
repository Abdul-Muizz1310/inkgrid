from inkgrid.verify.ink import InkRule, Point
from inkgrid.verify.rules import InkPath, InkSubpath, extract_rules, merge_rules


def stroke(*points: Point | None, closed: bool = False) -> InkPath:
    return InkPath(stroke=True, fill=False, subpaths=(InkSubpath(points, closed=closed),))


def fill(x0: float, y0: float, x1: float, y1: float) -> InkPath:
    box = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    return InkPath(stroke=False, fill=True, subpaths=(InkSubpath(box, closed=True),))


def test_VR9_a_stroked_segment_may_slant_up_to_one_point() -> None:
    assert extract_rules([stroke((0, 0), (20, 0.9))]) == (InkRule("h", 0.45, 0, 20),)
    assert extract_rules([stroke((0, 0), (20, 1.1))]) == ()
    assert extract_rules([stroke((5, 0), (5.5, 30))]) == (InkRule("v", 5.25, 0, 30),)


def test_VR9_a_rule_is_at_least_three_points_long() -> None:
    assert extract_rules([stroke((0, 0), (2.9, 0))]) == ()
    assert extract_rules([stroke((0, 0), (3.0, 0))]) == (InkRule("h", 0, 0, 3.0),)


def test_VR10_a_thin_filled_box_is_a_rule_and_a_wide_one_is_shading() -> None:
    assert extract_rules([fill(10, 0, 13, 40)]) == (InkRule("v", 11.5, 0, 40),)
    assert extract_rules([fill(0, 10, 40, 13)]) == (InkRule("h", 11.5, 0, 40),)
    assert extract_rules([fill(10, 0, 13.1, 40)]) == ()


def test_VR10_a_stroked_box_gives_its_four_edges() -> None:
    box = stroke((0, 0), (40, 0), (40, 20), (0, 20), closed=True)
    assert extract_rules([box]) == (
        InkRule("h", 0, 0, 40),
        InkRule("h", 20, 0, 40),
        InkRule("v", 0, 0, 20),
        InkRule("v", 40, 0, 20),
    )


def test_VR10_an_open_subpath_has_no_closing_segment() -> None:
    assert extract_rules([stroke((0, 0), (40, 0), (40, 20), (0, 20))]) == (
        InkRule("h", 0, 0, 40),
        InkRule("h", 20, 0, 40),
        InkRule("v", 40, 0, 20),
    )


def test_VR10_an_invisible_path_draws_nothing() -> None:
    hidden = InkPath(stroke=False, fill=False, subpaths=(InkSubpath(((0, 0), (40, 0)), False),))
    assert extract_rules([hidden]) == ()


def test_VR10_a_curve_breaks_a_straight_run() -> None:
    assert extract_rules([stroke((0, 0), None, (20, 0))]) == ()


def test_VR11_collinear_segments_merge_across_a_small_gap() -> None:
    assert merge_rules([InkRule("h", 5, 0, 10), InkRule("h", 5, 10.8, 20)]) == (
        InkRule("h", 5, 0, 20),
    )
    assert merge_rules([InkRule("h", 5, 0, 10), InkRule("h", 5, 11.2, 20)]) == (
        InkRule("h", 5, 0, 10),
        InkRule("h", 5, 11.2, 20),
    )


def test_VR11_segments_merge_only_when_nearly_collinear() -> None:
    assert merge_rules([InkRule("v", 5, 0, 10), InkRule("v", 5.4, 5, 20)]) == (
        InkRule("v", 5, 0, 20),
    )
    assert len(merge_rules([InkRule("v", 5, 0, 10), InkRule("v", 5.6, 5, 20)])) == 2


def test_VR11_merging_never_crosses_axes() -> None:
    assert len(merge_rules([InkRule("h", 5, 0, 10), InkRule("v", 5, 0, 10)])) == 2


def test_VR11_a_table_drawn_cell_by_cell_becomes_whole_rules() -> None:
    cells = [fill(x, 99.5, x + 50, 100.5) for x in (0, 50, 100)]
    assert extract_rules(cells) == (InkRule("h", 100, 0, 150),)
