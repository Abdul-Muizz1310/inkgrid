import time
from collections.abc import Sequence

from hypothesis import given
from hypothesis import strategies as st

from inkgrid.core.layout import Region, layout
from inkgrid.model.config import Profile
from layout_builder import P, place, text_line

PROFILE = Profile()
BODY = 10.0
PITCH = 12.0
COLUMN_WIDTH = 165.0  # six 5-letter words at 10 pt, 0.3 em apart


def column(tag: str, n: int, *, x: float, y: float, words: int = 6) -> list[P]:
    """`n` lines of distinct 5-letter words, one line every PITCH points."""
    out: list[P] = []
    for i in range(n):
        out += text_line([f"{tag}{i:02d}{j:02d}"[:5] for j in range(words)], x=x, y=y + PITCH * i)
    return out


def read_order(regions: Sequence[Region]) -> list[tuple[str, list[str]]]:
    return [(r.kind, [w.text for line in r.lines for w in line.words]) for r in regions]


def texts(ps: Sequence[P]) -> list[str]:
    return [p.text for p in ps]


def test_LY1_one_column_is_one_prose_region() -> None:
    ps = column("a", 8, x=72, y=100)
    regions = layout(place(ps), PROFILE, BODY)
    assert read_order(regions) == [("prose", texts(ps))]
    assert len(regions[0].lines) == 8


def two_columns(*, y: float = 100.0, offset: float = 0.0, n: int = 6) -> tuple[list[P], list[P]]:
    left = column("l", n, x=72, y=y)
    right = column("r", n, x=72 + COLUMN_WIDTH + 24, y=y + offset)
    return left, right


def test_LY2_two_prose_columns_read_left_then_right() -> None:
    left, right = two_columns()
    regions = layout(place(left + right), PROFILE, BODY)
    assert read_order(regions) == [("prose", texts(left)), ("prose", texts(right))]


def test_LY3_offset_baselines_still_read_by_column() -> None:
    left, right = two_columns(offset=PITCH / 2)
    regions = layout(place(left + right), PROFILE, BODY)
    assert read_order(regions) == [("prose", texts(left)), ("prose", texts(right))]


def test_LY4_full_width_lines_frame_the_columns() -> None:
    left, right = two_columns(y=100)
    width = 2 * COLUMN_WIDTH + 24
    title = text_line(["Title"] * 12, x=72, y=70)
    closing = text_line(["close"] * 12, x=72, y=100 + 6 * PITCH + 20)
    assert title[-1].x + title[-1].width >= 72 + width - 30
    regions = layout(place(title + left + right + closing), PROFILE, BODY)
    assert read_order(regions) == [
        ("prose", texts(title)),
        ("prose", texts(left)),
        ("prose", texts(right)),
        ("prose", texts(closing)),
    ]


def test_LY5_an_unruled_table_reads_row_by_row() -> None:
    ps: list[P] = []
    for i in range(5):
        y = 100 + PITCH * i
        ps += [*text_line(["Order", f"fee{i}"], x=72, y=y), P("0.10", 250, y), P("0.20", 350, y)]
    regions = layout(place(ps), PROFILE, BODY)
    assert read_order(regions) == [("rows", texts(ps))]


def test_LY6_a_hanging_indent_list_keeps_each_label_before_its_text() -> None:
    ps: list[P] = []
    for i in range(5):
        y = 100 + 2 * PITCH * i
        ps += [P(f"{i + 1}.", 72, y), *text_line(["charge", f"item{i}", "applies"], x=90, y=y)]
        ps += text_line(["continued", "text"], x=90, y=y + PITCH)
    regions = layout(place(ps), PROFILE, BODY)
    assert len(regions) == 1
    assert [w.text for line in regions[0].lines for w in line.words] == texts(ps)


def test_LY7_columns_too_short_to_count_stay_in_row_order() -> None:
    left, right = two_columns(n=2)
    regions = layout(place(left + right), PROFILE, BODY)
    rows = [left[:6] + right[:6], left[6:] + right[6:]]
    assert read_order(regions) == [("prose", [t for row in rows for t in texts(row)])]


def test_LY8_a_short_last_line_does_not_open_a_gutter() -> None:
    ps = column("a", 3, x=72, y=100, words=12)
    ps += text_line(["end", "of", "para"], x=72, y=100 + 3 * PITCH)
    ps += column("b", 3, x=72, y=100 + 4 * PITCH, words=12)
    assert read_order(layout(place(ps), PROFILE, BODY)) == [("prose", texts(ps))]


def test_LY9_vertical_words_are_a_region_after_the_others() -> None:
    body = column("a", 4, x=72, y=100)
    label = [P("Rotated", 40, 100, horizontal=False), P("label", 40, 140, horizontal=False)]
    regions = layout(place(label + body), PROFILE, BODY)
    assert read_order(regions) == [("prose", texts(body)), ("rows", texts(label))]


placements = st.lists(
    st.builds(
        P,
        text=st.text("abc", min_size=1, max_size=8),
        x=st.floats(0, 500),
        y=st.floats(0, 700),
        size=st.floats(5, 14),
        horizontal=st.booleans(),
    ),
    max_size=60,
)


@given(placements)
def test_LY10_every_word_is_in_exactly_one_region(ps: list[P]) -> None:
    words = place(ps)
    regions = layout(words, PROFILE, BODY)
    ids = [w.id for r in regions for line in r.lines for w in line.words]
    assert sorted(ids) == [w.id for w in words]


def test_LY11_a_dense_page_is_laid_out_quickly() -> None:
    ps: list[P] = []
    for i in range(1500):
        y = 10 + 11 * i
        ps += [P(f"r{i}", 72, y), P(f"{i}.10", 250, y), P(f"{i}.20", 350, y)]
    words = place(ps)
    start = time.perf_counter()
    regions = layout(words, PROFILE, BODY)
    assert time.perf_counter() - start < 2.0
    assert [r.kind for r in regions] == ["rows"]
