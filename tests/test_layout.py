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


RIGHT_X = 72 + COLUMN_WIDTH + 24


def fee_table(y: float) -> list[P]:
    """Five rows: a label left of the gutter, two values right of it."""
    out: list[P] = []
    for n, label in enumerate(["Customer", "Firm", "Broker", "Member", "Agent"]):
        row_y = y + PITCH * n
        out += [
            P(label, 72, row_y),
            P(f"0.{n}0", RIGHT_X + 20, row_y),
            P(f"0.{n}5", RIGHT_X + 120, row_y),
        ]
    return out


def test_LY12_a_table_below_the_columns_is_cut_away() -> None:
    left, right = two_columns(y=100)
    table = fee_table(100 + 6 * PITCH + 8)
    regions = layout(place(left + right + table), PROFILE, BODY)
    assert read_order(regions) == [
        ("prose", texts(left)),
        ("prose", texts(right)),
        ("rows", texts(table)),
    ]


def test_LY13_a_table_above_the_columns_is_cut_away() -> None:
    table = fee_table(100)
    left, right = two_columns(y=100 + 5 * PITCH + 8)
    regions = layout(place(table + left + right), PROFILE, BODY)
    assert read_order(regions) == [
        ("rows", texts(table)),
        ("prose", texts(left)),
        ("prose", texts(right)),
    ]


def paragraph_above(y: float) -> list[P]:
    return [
        *text_line(["words"] * 12, x=72, y=y),
        *text_line(["end", "of", "it."], x=72, y=y + PITCH),
    ]


def test_LY14_a_paragraphs_last_line_stays_with_it_above_columns() -> None:
    para = paragraph_above(70)
    left, right = two_columns(y=70 + 2 * PITCH + 6)
    regions = layout(place(para + left + right), PROFILE, BODY)
    assert read_order(regions) == [
        ("prose", texts(para)),
        ("prose", texts(left)),
        ("prose", texts(right)),
    ]


def test_LY15_a_paragraphs_last_line_stays_with_it_above_a_table() -> None:
    para = paragraph_above(70)
    table = fee_table(70 + 2 * PITCH + 6)
    regions = layout(place(para + table), PROFILE, BODY)
    assert read_order(regions) == [("prose", texts(para)), ("rows", texts(table))]


def test_LY16_a_flush_right_date_above_columns_reads_first() -> None:
    date = text_line(["Effective", "2026"], x=72 + 2 * COLUMN_WIDTH + 24 - 70, y=80)
    left, right = two_columns(y=100)
    regions = layout(place(date + left + right), PROFILE, BODY)
    assert read_order(regions) == [
        ("prose", texts(date)),
        ("prose", texts(left)),
        ("prose", texts(right)),
    ]


# --- Prose columns (docs/specs/19-ocr-benchmark-fixes.md section 2) ---------------------------

HAN = ("\u4e2d", "\u6587")  # one character for each Chinese column, so the two read apart


def han_column(n: int, *, x: float, y: float, chars: int = 21, side: int = 0) -> list[P]:
    """`n` lines of Chinese prose, each one word of `chars` characters (no spaces between)."""
    return [P(HAN[side] * (chars - 2) + f"{i:02d}", x, y + PITCH * i) for i in range(n)]


def test_PC1_two_chinese_prose_columns_read_left_then_right() -> None:
    # Each line is one word, 105 pt (10.5 em) wide; the columns are 24 pt apart.
    left = han_column(8, x=72, y=100)
    right = han_column(8, x=72 + 105 + 24, y=100, side=1)
    regions = layout(place(left + right), PROFILE, BODY)
    assert read_order(regions) == [("prose", texts(left)), ("prose", texts(right))]


def test_PC2_a_table_of_one_word_cells_stays_rows() -> None:
    ps: list[P] = []
    for i in range(8):
        y = 100 + PITCH * i
        ps += [P(f"Tier{i}", 72, y), P(f"Band{i}", 200, y), P(f"Fee{i}", 330, y)]
    assert read_order(layout(place(ps), PROFILE, BODY)) == [("rows", texts(ps))]


def test_PC3_a_stray_in_the_margin_reads_after_the_columns() -> None:
    left, right = two_columns(n=8)
    stray = [P("12", 72 + 2 * COLUMN_WIDTH + 24 + 30, 100 + 3 * PITCH)]
    regions = layout(place(left + right + stray), PROFILE, BODY)
    assert read_order(regions) == [
        ("prose", texts(left)),
        ("prose", texts(right)),
        ("prose", ["12"]),
    ]


def rows_order(*columns: list[P]) -> list[str]:
    """The columns' words read row by row, across the columns, as a `rows` region holds them."""
    placed = sorted((p for col in columns for p in col), key=lambda p: (p.y, p.x))
    return [p.text for p in placed]


def test_PC4_a_prose_column_beside_values_stays_rows() -> None:
    prose = column("a", 8, x=72, y=100)
    values = [P(f"{i},250.00", RIGHT_X + 40, 100 + PITCH * i) for i in range(8)]
    regions = layout(place(prose + values), PROFILE, BODY)
    assert read_order(regions) == [("rows", rows_order(prose, values))]


def test_PC5_labels_beside_their_text_stay_rows() -> None:
    labels = [P(f"Label{i}", 72, 100 + PITCH * i) for i in range(8)]
    text = column("t", 8, x=160, y=100)
    regions = layout(place(labels + text), PROFILE, BODY)
    assert read_order(regions) == [("rows", rows_order(labels, text))]


def test_PC6_a_remainder_holding_columns_under_a_headline_is_laid_out_again() -> None:
    left = column("a", 8, x=72, y=100)
    x_b = RIGHT_X
    x_c = x_b + COLUMN_WIDTH + 24
    headline = text_line(["Headline"] * 13, x=x_b, y=100)
    assert headline[-1].x > x_c  # it crosses the remainder's own gutter
    b = column("b", 7, x=x_b, y=100 + PITCH)
    c = column("c", 7, x=x_c, y=100 + PITCH)
    regions = layout(place(left + headline + b + c), PROFILE, BODY)
    assert read_order(regions) == [
        ("prose", texts(left)),
        ("prose", texts(headline)),
        ("prose", texts(b)),
        ("prose", texts(c)),
    ]


def test_PC7_a_wide_column_read_across_three_columns_is_laid_out_again() -> None:
    prose = column("p", 8, x=72, y=100)
    x0 = RIGHT_X
    span = text_line(["Spanning"] * 20, x=x0, y=100)
    subs = [
        column(tag, 7, x=x0 + k * (110 + 12), y=100 + PITCH, words=4) for k, tag in enumerate("xyz")
    ]
    assert span[-1].x > x0 + 2 * (110 + 12)  # the spanning line crosses both inner gutters
    regions = layout(place(prose + span + subs[0] + subs[1] + subs[2]), PROFILE, BODY)
    assert read_order(regions) == [
        ("prose", texts(prose)),
        ("prose", texts(span)),
        *(("prose", texts(sub)) for sub in subs),
    ]


def split_column(n: int, *, x: float, y: float, split: set[int]) -> list[P]:
    """`n` prose lines of 8 words; the lines in `split` are two halves of 4, 2 em apart."""
    out: list[P] = []
    for i in range(n):
        words = [f"s{i:02d}{j:02d}"[:5] for j in range(8)]
        at = y + PITCH * i
        if i in split:
            out += text_line(words[:4], x=x, y=at) + text_line(words[4:], x=x + 109 + 20, y=at)
        else:
            out += text_line(words, x=x, y=at)
    return out


def test_PC9_a_column_split_on_more_than_half_its_lines_is_no_prose_column() -> None:
    # Every half line holds 4 words, so only the share of split lines tells the two apart.
    left = column("a", 8, x=72, y=100)
    half = split_column(8, x=RIGHT_X, y=100, split={1, 3, 5, 7})
    regions = layout(place(left + half), PROFILE, BODY)
    assert read_order(regions) == [("prose", texts(left)), ("prose", texts(half))]
    more = split_column(8, x=RIGHT_X, y=100, split={0, 1, 3, 5, 7})
    regions = layout(place(left + more), PROFILE, BODY)
    assert read_order(regions) == [("rows", rows_order(left, more))]


def filled_han_column(*, x: float, y: float, chars: int, side: int) -> list[P]:
    """8 Chinese lines, 4 of `chars` characters and 4 of a fifth as many: filled 0.6."""
    short = chars // 5
    out = []
    for i in range(8):
        n = chars if i % 2 == 0 else short
        out.append(P(HAN[side] * (n - 2) + f"{i:02d}", x, y + PITCH * i))
    return out


def test_PC10_a_column_ten_ems_wide_and_six_tenths_full_is_prose() -> None:
    left = filled_han_column(x=72, y=100, chars=20, side=0)  # 100 pt wide, mean 60 pt
    right = filled_han_column(x=72 + 100 + 24, y=100, chars=20, side=1)
    regions = layout(place(left + right), PROFILE, BODY)
    assert read_order(regions) == [("prose", texts(left)), ("prose", texts(right))]
    narrow_left = filled_han_column(x=72, y=100, chars=19, side=0)  # 95 pt: 9.5 em
    narrow_right = filled_han_column(x=72 + 95 + 24, y=100, chars=19, side=1)
    regions = layout(place(narrow_left + narrow_right), PROFILE, BODY)
    assert read_order(regions) == [("rows", rows_order(narrow_left, narrow_right))]


def test_PC8_a_stray_beside_a_single_prose_column_reads_as_before() -> None:
    # The stray opens a gutter from its own line down: the lines above it are plain prose, and
    # from its line on the section is `rows`, as 0.1.0 read it.
    prose = column("a", 8, x=72, y=100)
    stray = [P("12", 72 + COLUMN_WIDTH + 40, 100 + 3 * PITCH)]
    regions = layout(place(prose + stray), PROFILE, BODY)
    above, below = prose[: 3 * 6], prose[3 * 6 :]
    assert read_order(regions) == [("prose", texts(above)), ("rows", rows_order(below, stray))]
