import pytest

from inkgrid.core.tables.chart import chart_evidence, number
from inkgrid.model.geometry import Rect
from inkgrid.model.page import Rule
from layout_builder import P, place

BOX = Rect(100, 300, 520, 540)


def bars(values: list[float], k: float = 1.88, base: float = 500.0) -> tuple[list[Rect], list[P]]:
    rects, labels = [], []
    for i, v in enumerate(values):
        x = 160.0 + 64 * i
        rects.append(Rect(x, base - k * v, x + 25, base))
        labels.append(P(f"{v:.1f}", x + 4, base - k * v - 14, size=8))
    return rects, labels


def test_CH1_proportional_bars_are_a_chart() -> None:
    rects, labels = bars([1.4, 7.8, 20.0, 44.4, 20.9])
    assert chart_evidence(BOX, place(labels), (), rects) == "bars"


def test_CH2_a_numeric_axis_with_a_tick_at_every_label_is_a_chart() -> None:
    labels = [P(str(v), 100, 480 - 40 * i, size=8) for i, v in enumerate((0, 10, 20, 30))]
    words = place(labels)
    ticks = tuple(
        Rule(
            page=1,
            axis="h",
            at=w.bbox.center[1],
            start=w.bbox.x1 + 2,
            end=w.bbox.x1 + 6,
            thickness=0.5,
        )
        for w in words
    )
    assert chart_evidence(BOX, words, ticks, ()) == "axis"
    assert chart_evidence(BOX, words, ticks[:3], ()) is None  # one label without its tick


def test_CH3_shading_sharing_an_edge_is_no_chart_unless_proportional() -> None:
    # fee tables: shaded rows share the table's left edge and differ in length, not by their values
    rects = [Rect(100, 300 + 20 * i, 100 + w, 312 + 20 * i) for i, w in enumerate((200, 180, 260))]
    labels = [P(v, 110, 302 + 20 * i, size=8) for i, v in enumerate(("0.30", "0.15", "1.00"))]
    assert chart_evidence(BOX, place(labels), (), rects) is None


def test_CH3_equal_fills_tiers_beside_rules_and_years_are_no_chart() -> None:
    equal, labels = bars([10.0, 10.0, 10.0])
    assert chart_evidence(BOX, place(labels), (), equal) is None
    tiers = place([P(str(t), 110, 320 + 20 * t, size=8) for t in (1, 2, 3, 4)])
    beside = tuple(
        Rule(page=1, axis="h", at=w.bbox.center[1], start=200, end=300, thickness=0.5)
        for w in tiers
    )  # sub-row rules drawn in the next column, far from the labels
    assert chart_evidence(BOX, tiers, beside, ()) is None
    column = tiers[0].bbox.x1 + 3  # a column rule between each tier and its sub-row rule
    near = tuple(
        Rule(page=1, axis="h", at=w.bbox.center[1], start=column + 3, end=300, thickness=0.5)
        for w in tiers
    )
    wall = Rule(page=1, axis="v", at=column, start=320, end=420, thickness=0.5)
    assert chart_evidence(BOX, tiers, (*near, wall), ()) is None
    assert chart_evidence(BOX, tiers, near, ()) == "axis"  # the same rules with no wall are ticks
    struck = tuple(
        Rule(page=1, axis="h", at=w.bbox.center[1], start=w.bbox.x0, end=300, thickness=0.5)
        for w in tiers
    )
    assert chart_evidence(BOX, tiers, struck, ()) is None  # a rule through a word is no tick
    years = place([P(str(y), 150 + 60 * i, 320, size=8) for i, y in enumerate((1995, 2000, 2005))])
    assert chart_evidence(BOX, years, (), ()) is None


def test_CH2_a_tick_may_lie_on_either_side_of_its_label() -> None:
    words = place([P(str(v), 200, 480 - 40 * i, size=8) for i, v in enumerate((0, 10, 20))])
    ticks = tuple(
        Rule(
            page=1,
            axis="h",
            at=w.bbox.center[1],
            start=w.bbox.x0 - 6,
            end=w.bbox.x0 - 2,
            thickness=0.5,
        )
        for w in words
    )  # an axis on the plot's right: the labels to the right of their ticks
    assert chart_evidence(BOX, words, ticks, ()) == "axis"


def test_CH3_bars_that_overlap_across_their_baseline_are_no_chart() -> None:
    # Each bar pairs with its own label and the lengths fit one factor: only the overlap refuses.
    overlapping = [
        Rect(160, 481.2, 185, 500),
        Rect(175, 462.4, 200, 500),
        Rect(190, 443.6, 215, 500),
    ]
    labels = place(
        [P("10", 161, 467.2, size=8), P("20", 176, 448.4, size=8), P("30", 201, 429.6, size=8)]
    )
    apart = [Rect(r.x0 + 30 * i, r.y0, r.x1 + 30 * i, r.y1) for i, r in enumerate(overlapping)]
    moved = place([P(w.text, w.bbox.x0 + 30 * i, w.bbox.y0, size=8) for i, w in enumerate(labels)])
    assert chart_evidence(BOX, moved, (), apart) == "bars"
    assert chart_evidence(BOX, labels, (), overlapping) is None


def test_CH3_bars_need_three_lengths_more_than_a_point_apart() -> None:
    rects, labels = bars([10.0, 10.3, 30.0], k=2.0)  # lengths 20, 20.6, 60
    assert chart_evidence(BOX, place(labels), (), rects) is None


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("1,400", 1400.0),
        ("1,4", 1.4),
        ("20,0", 20.0),
        ("(12.5%)", 12.5),
        ("$3", 3.0),
        ("\u22125", -5.0),
        (".5", 0.5),
        ("1,400,5", None),
        ("-", None),
        ("%", None),
        ("Poor", None),
    ],
)
def test_CH1_a_value_label_reads_as_its_number(text: str, value: float | None) -> None:
    assert number(text) == value
