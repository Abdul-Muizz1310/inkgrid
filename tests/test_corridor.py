import math
import time
from unittest.mock import Mock

import pytest
from hypothesis import given
from hypothesis import strategies as st

import inkgrid.core.tables.corridor as corridor_module
import pdf_factory
from inkgrid.core.layout import Region
from inkgrid.core.lines import fragments, group_lines
from inkgrid.core.tables.corridor import (
    CorridorStage,
    Row,
    _blanks,
    _boundary,
    _row,
    _split,
    columns,
    corridor_table,
    corridor_tables,
    fold_rows,
    is_value_like,
    is_value_piece,
)
from inkgrid.core.tables.proto import ProtoTable
from inkgrid.model.config import Profile
from inkgrid.model.findings import FindingCode
from inkgrid.model.page import Rule, Word
from lattice_builder import read_with_tables
from layout_builder import P, place, text_line

PROFILE = Profile()


def words(text: str, *, marks: str = "") -> tuple[Word, ...]:
    ps = text_line(text.split(), x=72, y=100, size=9)
    if marks:
        end = ps[-1].x + ps[-1].width
        ps.append(P(marks, end + 0.5, 97, size=5, superscript=True))
    return place(ps)


@pytest.mark.parametrize(
    ("text", "marks"),
    [
        ("0.25 bp", ""),
        ("CHF 0.50", ""),
        ("$5,000 per month", ""),
        ("0.10 per contract", ""),
        ("-0.15bp", ""),
        ("\u00a330,000", "****"),
    ],
)
def test_VP1_value_pieces(text: str, marks: str) -> None:
    assert is_value_piece(words(text, marks=marks))


@pytest.mark.parametrize(
    "text",
    ["Section 2.1", "Tier 1", "1 \u2013 150", "Free", "-", "The fee is CHF 1.00 per trade", "62"],
)
def test_VP2_labels_and_weak_values_are_not_value_pieces(text: str) -> None:
    assert not is_value_piece(words(text))


@pytest.mark.parametrize(
    ("text", "like"),
    [
        ("1 \u2013 150", True),
        ("62", True),
        ("Free", True),
        ("-", True),
        ("Tier 1", False),
        ("Commitment", False),
    ],
)
def test_VP3_value_like_pieces_include_weak_values(text: str, like: bool) -> None:
    assert is_value_like(words(text)) is like


def rows_of(ps: list[P]) -> tuple[Row, ...]:
    return fold_rows(group_lines(place(ps), PROFILE), PROFILE)


def row_texts(rows: tuple[Row, ...]) -> list[list[str]]:
    return [[" ".join(w.text for w in line.words) for line in row.lines] for row in rows]


def test_RW1_a_wrapped_header_line_joins_its_row() -> None:
    ps = [P("Fee", 72, 100, size=9), P("Transac-", 200, 100, size=9), P("tion", 200, 109, size=9)]
    for n, y in enumerate((121, 133, 145)):
        ps += [P(f"Tier{n}", 72, y, size=9), P(f"0.{n}0", 200, y, size=9)]
    assert row_texts(rows_of(ps)) == [
        ["Fee Transac-", "tion"],
        ["Tier0 0.00"],
        ["Tier1 0.10"],
        ["Tier2 0.20"],
    ]


def value_rows(y: float, n: int) -> list[P]:
    """`n` value rows 20 pt apart: a label, and a value set at x 282."""
    return [
        p
        for k in range(n)
        for p in (P(f"Row{k}", 72, y + 20 * k, size=9), P(f"0.{k}5", 282, y + 20 * k, size=9))
    ]


def test_RW2_values_stacked_in_one_column_are_rows_of_their_own() -> None:
    band = [P("Band", 72, 160, size=9), P("\u20ac0.13", 282, 160, size=9)]
    stacked = [*band, P("\u20ac0.08", 282, 165, size=9)]
    assert len(rows_of(value_rows(100, 3) + stacked)) == 5
    beside = [*band, P("\u20ac0.08", 382, 165, size=9)]
    assert len(rows_of(value_rows(100, 3) + beside)) == 4


def test_RW3_a_centred_value_joins_its_two_line_label() -> None:
    ps = [P("Poster", 72, 80.8, size=10), P("0.10bp", 300, 80.8, size=10)]
    ps += [
        P("Value", 72, 100, size=10),
        P("0.45bp", 300, 105.1, size=10),
        P("scheme", 72, 110.2, size=10),
    ]
    ps += [P("Aggressor", 72, 129.5, size=10), P("0.20bp", 300, 129.5, size=10)]
    assert row_texts(rows_of(ps)) == [
        ["Poster 0.10bp"],
        ["Value", "0.45bp", "scheme"],
        ["Aggressor 0.20bp"],
    ]


def test_RW4_lines_at_the_blocks_own_pitch_are_rows() -> None:
    ps = [
        p
        for n in range(4)
        for p in (P(f"Row{n}", 72, 100 + 19 * n), P(f"0.{n}5", 200, 100 + 19 * n))
    ]
    assert len(rows_of(ps)) == 4


def test_RW5_weak_values_stacked_in_one_column_are_rows_of_their_own() -> None:
    ranges = [
        *text_line(["151", "\u2013", "500"], x=72, y=160, size=9),
        P("0.95", 282, 160, size=9),
    ]
    ranges += text_line(["501", "\u2013", "1,000"], x=72, y=165, size=9)
    assert len(rows_of(value_rows(100, 3) + ranges)) == 5


def corridor(ps: list[P]) -> ProtoTable | None:
    rows = rows_of(ps)
    return corridor_table(rows, columns(rows), PROFILE, page=1, frame=0)


def cell_map(table: ProtoTable) -> dict[str, tuple[int, int, int]]:
    """Each non-empty cell by its text: (row, col, col_span)."""
    return {
        " ".join(w.text for w in c.words): (c.cell.row, c.cell.col, c.cell.col_span)
        for c in table.cells
        if c.words
    }


def right(text: str, end: float, y: float, size: float = 9) -> list[P]:
    """Words laid out so the piece ends at `end` (right-aligned money)."""
    width = sum(0.5 * size * len(t) for t in text.split()) + 0.3 * size * (len(text.split()) - 1)
    return text_line(text.split(), x=end - width, y=y, size=size)


def six_rows(y: float = 120) -> list[P]:
    """Two SIX value rows: a label, Floor ending 285, Scale ending 345, Cap ending 404."""
    out: list[P] = []
    for n, (label, floor, scale) in enumerate(
        [("a) Poster", "-", "1.00 bp"), ("b) Aggressor", "CHF 0.50", "0.55 bp")]
    ):
        at = y + 12 * n
        out += text_line(label.split(), x=72, y=at, size=9)
        out += right(floor, 285, at) + right(scale, 345, at) + right("-", 404, at)
    return out


def test_CB1_columns_come_from_the_value_rows() -> None:
    rows = rows_of(six_rows())
    assert len(columns(rows)) == 4


def voted(lo: float, hi: float, rows: list[Row]) -> float:
    """Section 4's vote, scored the slow way: every candidate against every row and every edge."""
    blanks = [_blanks(row, lo, hi) for row in rows]
    candidates = [(lo + hi) / 2, *((a + b) / 2 for row in blanks for a, b in row)]
    edges = [e for row in rows for w in row.words for e in (w.bbox.x0, w.bbox.x1)]

    def score(x: float) -> tuple[int, float]:
        votes = sum(1 if any(a <= x <= b for a, b in row) else -1 for row in blanks if row)
        return votes, min((abs(x - e) for e in edges), default=0.0)

    return max(candidates, key=score)


row_words = st.lists(
    st.tuples(st.integers(60, 420), st.integers(1, 6)),
    min_size=1,
    max_size=5,
    unique_by=lambda t: t[0],
)


@given(st.lists(row_words, min_size=1, max_size=6), st.integers(60, 400), st.integers(2, 80))
def test_CB4_the_boundary_is_the_votes_winner(
    rows: list[list[tuple[int, int]]], lo: int, width: int
) -> None:
    built = [
        _row(
            group_lines(place([P("w" * n, x, 100 + 20 * r, size=9) for x, n in words]), PROFILE),
            PROFILE,
        )
        for r, words in enumerate(rows)
    ]
    assert _boundary(lo, lo + width, built) == voted(lo, lo + width, built)


def test_CB2_a_long_label_keeps_its_column() -> None:
    label = text_line(["Securities", "in", "the", "uncleared", "market"], x=72, y=144, size=9)
    table = corridor(six_rows() + label + right("Free", 285, 144))
    assert table is not None
    assert cell_map(table)["Securities in the uncleared market"] == (2, 0, 1)
    assert cell_map(table)["Free"] == (2, 1, 1)


def test_CB3_a_word_across_a_corridor_with_no_blank_spans_both_columns() -> None:
    header = [P("Transaction-fee-schedule-heading", 110, 100, size=9)]
    table = corridor(header + six_rows())
    assert table is not None
    assert cell_map(table)["Transaction-fee-schedule-heading"] == (0, 0, 2)


def five_columns(y: float) -> list[P]:
    """SIX's STI/OTI value rows: a label and four right-aligned CHF columns."""
    out: list[P] = []
    for n in range(2):
        at = y + 12 * n
        out += text_line([f"Row{n}"], x=57, y=at, size=9)
        for end in (250, 349, 447, 546):
            out += right("CHF 1.00", end, at)
    return out


def test_CG1_a_spanning_header_keeps_its_span() -> None:
    header = right("Trades executed via STI", 348, 100) + right("Trades executed via OTI", 546, 100)
    table = corridor(header + five_columns(120))
    assert table is not None
    spans = cell_map(table)
    assert spans["Trades executed via STI"] == (0, 1, 2)
    assert spans["Trades executed via OTI"] == (0, 3, 2)


def test_CG2_a_column_break_inside_a_fragment_splits_it() -> None:
    header = right("During continuous", 250, 100)
    header += text_line(["Auction", "&", "TAL"], x=255, y=100, size=9)
    table = corridor(header + five_columns(120))
    assert table is not None
    spans = cell_map(table)
    assert spans["During continuous"] == (0, 1, 1)
    assert spans["Auction & TAL"][:2] == (0, 2)


def test_CG3_a_trailing_wide_cell_spans_and_leaves_an_empty_cell() -> None:
    commitment = text_line(["Commitment"], x=72, y=144, size=9) + right(
        "No commitment required", 404, 144
    )
    table = corridor(six_rows() + commitment)
    assert table is not None
    assert cell_map(table)["No commitment required"] == (2, 2, 2)
    empty = [(c.cell.row, c.cell.col) for c in table.cells if not c.words]
    assert (2, 1) in empty


def test_CG4_two_values_in_one_cell_is_no_table() -> None:
    fused = (
        text_line(["Label"], x=72, y=120, size=9)
        + right("0.10", 218, 120)
        + right("0.20", 258, 120)
    )
    wide = text_line(["Other"], x=72, y=132, size=9) + text_line(
        ["$1,000", "per", "month"], x=200, y=132, size=9
    )
    assert corridor(fused + wide) is None


def stage(*regions: list[P]) -> CorridorStage:
    placed: list[Region] = []
    first = 0
    for ps in regions:
        words = place(ps, first_id=first)
        first += len(words)
        placed.append(Region("rows", group_lines(words, PROFILE)))
    return corridor_tables(placed, PROFILE, page=1, frame=0)


def texts_of(region: Region) -> list[str]:
    return [" ".join(w.text for w in line.words) for line in region.lines]


def header_row(y: float, bold: bool = True) -> list[P]:
    out = text_line(["Asymmetrical:"], x=72, y=y, size=9, bold=bold)
    for text, end in (("Floor", 285), ("Scale", 345), ("Cap", 404)):
        out += [P(text, end - 4.5 * len(text), y, size=9, bold=bold)]
    return out


def test_EX1_a_larger_heading_stays_out_of_the_table() -> None:
    heading = text_line(["1.2", "Ad", "valorem", "fee"], x=72, y=80, size=10, bold=True)
    result = stage(heading + header_row(100) + six_rows(112))
    (table,) = result.tables
    assert len(table.shape.row_edges) - 1 == 3
    assert [texts_of(r) for r in result.regions] == [["1.2 Ad valorem fee"]]


def test_EX2_a_caption_and_a_header_are_the_first_rows() -> None:
    caption = text_line(["Standard", "tariff"], x=72, y=88, size=9)
    (table,) = stage(caption + header_row(100) + six_rows(112)).tables
    assert table.header_rows == 2
    first = [" ".join(w.text for w in c.words) for c in table.cells if c.cell.row == 0 and c.words]
    assert first == ["Standard tariff"]


def test_EX3_a_sentence_past_the_columns_stays_out() -> None:
    # One piece, starting where column 0 starts: only the table's width keeps it out.
    text = (
        "The standard fees for members trading on the order book are set out in the schedule below"
    )
    sentence = text_line(text.split(), x=72, y=88, size=9)
    assert sentence[-1].x > 404  # past the last column's end
    result = stage(sentence + header_row(100) + six_rows(112))
    (table,) = result.tables
    assert len(table.shape.row_edges) - 1 == 3


def test_EX4_a_trailing_commitment_row_is_in() -> None:
    commitment = text_line(["Commitment"], x=72, y=136, size=9) + right(
        "No commitment required", 404, 136
    )
    (table,) = stage(header_row(100) + six_rows(112) + commitment).tables
    assert len(table.shape.row_edges) - 1 == 4


def test_EX5_a_trailing_bullet_past_the_columns_is_out() -> None:
    bullet = [
        P("\u25a0", 72, 136, size=9),
        *text_line(
            ["Members", "paying", "the", "fee", "are", "billed", "each", "month"],
            x=100,
            y=136,
            size=9,
        ),
    ]
    bullet += [P("afterwards", 470, 136, size=9)]
    result = stage(header_row(100) + six_rows(112) + bullet)
    (table,) = result.tables
    assert len(table.shape.row_edges) - 1 == 3
    assert len(result.regions) == 1


def test_EX6_a_banner_between_value_rows_is_in() -> None:
    banner = text_line(["Liquidity", "Provider", "Scheme"], x=72, y=136, size=9, bold=True)
    (table,) = stage(header_row(100) + six_rows(112) + banner + six_rows(148)).tables
    assert len(table.shape.row_edges) - 1 == 6
    assert table.banner_rows == (3,)


def test_EX7_a_table_across_two_rows_regions_is_one() -> None:
    commitment = text_line(["Commitment"], x=72, y=136, size=9) + right(
        "No commitment required", 404, 136
    )
    result = stage(header_row(100) + six_rows(112), commitment)
    (table,) = result.tables
    assert len(table.shape.row_edges) - 1 == 4
    assert result.regions == ()


def test_EX8_an_unaligned_line_between_two_tables_parts_them() -> None:
    note = text_line(["Rates", "for", "the", "second", "book"], x=100, y=136, size=9)
    result = stage(header_row(100) + six_rows(112) + note + header_row(160) + six_rows(172))
    assert len(result.tables) == 2
    assert [texts_of(r) for r in result.regions] == [["Rates for the second book"]]


def test_EX9_a_header_over_one_value_row_is_a_table() -> None:
    value = text_line(["Reporting"], x=72, y=112, size=9) + right("CHF 0.50", 285, 112)
    value += right("0.25 bp", 345, 112) + right("CHF 25", 404, 112)
    (table,) = stage(header_row(100) + value).tables
    assert len(table.shape.row_edges) - 1 == 2


def test_NT1_a_hanging_list_mentioning_fees_is_not_a_table() -> None:
    items = []
    for n, label in enumerate(["a)", "b)", "c)"]):
        items += [P(label, 72, 100 + 12 * n, size=9)]
        items += text_line(
            ["The", "fee", "is", "CHF", "5", "per", "trade."], x=100, y=100 + 12 * n, size=9
        )
    assert stage(items).tables == ()


def test_NT2_a_table_of_contents_is_not_a_table() -> None:
    entries = []
    for n, title in enumerate(["Transaction fees", "Ad valorem fee", "Annual fee"]):
        entries += text_line([f"1.{n}", *title.split()], x=72, y=100 + 12 * n, size=9)
        entries += [P(str(7 + n), 500, 100 + 12 * n, size=9)]
    assert stage(entries).tables == ()


def test_NT3_a_lone_value_row_is_not_a_table() -> None:
    value = text_line(["Standard"], x=72, y=100, size=9) + right("CHF 1.00", 285, 100)
    prose = text_line(
        ["Members", "pay", "this", "fee", "on", "every", "trade", "they", "make."],
        x=100,
        y=112,
        size=9,
    )
    assert stage(value + prose).tables == ()


def test_NT4_a_single_column_of_values_is_not_a_table() -> None:
    column = [p for n in range(3) for p in right(f"CHF {n}.00", 285, 100 + 12 * n)]
    assert stage(column).tables == ()


def test_RW6_rows_at_ordinary_leading_whose_boxes_overlap_stay_apart() -> None:
    ps = header_row(100)
    ps = [P(p.text, p.x, p.y, size=12.4, bold=True) for p in ps]
    for n in range(3):
        at = 112 + 12 * n
        ps += [P(f"Tier{n}", 72, at, size=12.4), P(f"0.{n}0", 300, at, size=12.4)]
    assert len(rows_of(ps)) == 4


def test_EX10_the_headings_pitch_does_not_set_the_tables() -> None:
    ps: list[P] = []
    for n, y in enumerate((60, 85, 110)):
        ps += text_line([f"1.{n}", "Heading"], x=72, y=y, size=10, bold=True)
    ps += header_row(135)
    for n in range(2):
        at = 150 + 15 * n
        ps += text_line([f"Tier{n}"], x=72, y=at, size=9) + right(f"CHF {n}.50", 285, at)
        ps += right("0.25 bp", 345, at) + right("-", 404, at)
    for n, y in enumerate((200, 225, 250)):
        ps += text_line([f"2.{n}", "Heading"], x=72, y=y, size=10, bold=True)
    (table,) = stage(ps).tables
    assert len(table.shape.row_edges) - 1 == 3
    assert table.header_rows == 1


def test_RW7_a_drawn_rule_ends_a_row() -> None:
    ps = [
        P("Requestor", 72, 100, size=9),
        P("\u20ac2", 300, 105, size=9),
        P("below", 72, 110, size=9),
    ]
    ps += [P("above", 72, 115, size=9), P("\u20ac0", 300, 125, size=9)]
    for n in range(4):
        at = 146 + 21 * n
        ps += [P(f"Other{n}", 72, at, size=9), P(f"\u20ac{n}", 300, at, size=9)]
    rule = Rule(page=1, axis="h", at=117, start=60, end=320, thickness=0.5)
    ruled = fold_rows(group_lines(place(ps), PROFILE), PROFILE, rules=(rule,))
    assert row_texts(ruled)[:2] == [["Requestor", "\u20ac2", "below"], ["above", "\u20ac0"]]
    unruled = fold_rows(group_lines(place(ps), PROFILE), PROFILE)
    assert row_texts(unruled)[:2] == [["Requestor", "\u20ac2", "below", "above"], ["\u20ac0"]]


def test_EX11_a_two_row_table_in_a_prose_region_is_found() -> None:
    ps = text_line(["First", "1,000", "executed", "orders"], x=72, y=100, size=9) + right(
        "\u20ac0.60", 404, 100
    )
    ps += text_line(["Subsequent", "executed", "orders"], x=72, y=112, size=9) + right(
        "\u20ac0.30", 404, 112
    )
    words = place(ps)
    region = Region("prose", group_lines(words, PROFILE))
    (table,) = corridor_tables([region], PROFILE, page=1, frame=0).tables
    assert len(table.shape.row_edges) - 1 == 2


def test_EX12_side_by_side_columns_are_never_one_candidate() -> None:
    left = [
        p
        for n in range(3)
        for p in text_line(["Fee", "band", f"{n}"], x=72, y=100 + 12 * n, size=9)
    ]
    right_col = [p for n in range(3) for p in right(f"CHF {n}.50", 540, 100 + 12 * n)]
    lw = place(left)
    rw = place(right_col, first_id=len(lw))
    regions = [Region("prose", group_lines(lw, PROFILE)), Region("prose", group_lines(rw, PROFILE))]
    stage_ = corridor_tables(regions, PROFILE, page=1, frame=0)
    assert stage_.tables == ()
    assert stage_.regions == tuple(regions)


def test_EX13_regions_whose_boxes_overlap_still_stack() -> None:
    caption = text_line(["Standard", "tariff"], x=72, y=100, size=9)
    body = header_row(108) + six_rows(120)  # the header's box overlaps the caption's by 1 pt
    first = place(caption)
    rest = place(body, first_id=len(first))
    regions = [
        Region("prose", group_lines(first, PROFILE)),
        Region("rows", group_lines(rest, PROFILE)),
    ]
    (table,) = corridor_tables(regions, PROFILE, page=1, frame=0).tables
    assert {w.text for w in table.words} >= {"Standard", "tariff"}


def test_EX14_a_centred_header_wider_than_its_column_is_in() -> None:
    header = text_line(["Category"], x=72, y=100, size=9)
    title = ["Maximum", "number"]
    width = sum(4.5 * len(t) for t in title) + 2.7
    header += text_line(title, x=399.5 - width / 2, y=100, size=9)  # centred on the last column
    rows: list[P] = []
    for n in range(2):
        at = 112 + 12 * n
        rows += text_line([f"Band{n}"], x=72, y=at, size=9) + right(f"CHF {n}.50", 285, at)
        rows += right("12", 404, at)
    (table,) = stage(header + rows).tables
    assert table.header_rows == 1
    assert len(table.shape.row_edges) - 1 == 3


def test_EX15_a_second_tables_header_starts_the_second_table() -> None:
    first = text_line(["Monthly", "fee"], x=72, y=100, size=9) + right("CHF 6,000", 404, 100)
    first += text_line(["Setup", "fee"], x=72, y=112, size=9) + right("CHF 1,000", 404, 112)
    second = (
        text_line(["Band"], x=72, y=124, size=9)
        + right("Variable", 285, 124)
        + right("Minimum", 404, 124)
    )
    for n in range(2):
        at = 136 + 12 * n
        second += text_line([f"Tier{n}"], x=72, y=at, size=9) + right(f"0.{n}0 bp", 285, at)
        second += right(f"CHF {n}.60", 404, at)
    tables = stage(first + second).tables
    assert len(tables) == 2
    assert tables[1].header_rows == 1


def test_EX16_a_wrapped_banner_is_not_a_new_header() -> None:
    banner = text_line(
        ["Aggressive", "executions", "qualifying", "under", "the", "scheme"],
        x=72,
        y=136,
        size=9,
        bold=True,
    )
    banner += text_line(["for", "equities"], x=72, y=145, size=9, bold=True)
    (table,) = stage(header_row(100) + six_rows(112) + banner + six_rows(160)).tables
    assert len(table.shape.row_edges) - 1 == 6


def test_EX17_the_downward_rows_never_run_into_the_next_table() -> None:
    tables = stage(header_row(100) + six_rows(112) + header_row(148) + six_rows(160)).tables
    assert len(tables) == 2
    assert [len(t.shape.row_edges) - 1 for t in tables] == [3, 3]
    assert tables[1].header_rows == 1


def long_table(n: int, *, fused: bool = False) -> list[P]:
    """`n` rows 12 pt apart: a label and three right-aligned fees; `fused` ends it in CG4's pair."""
    ps: list[P] = []
    for i in range(n):
        y = 100 + 12 * i
        ps += text_line([f"Band{i}"], x=72, y=y, size=9)
        for c in range(3):
            ps += right(f"{i % 97}.{i % 10}0", 250 + 90 * c, y)
    if fused:  # `$1,000 per month` bridges `0.10` and `0.20` into one column
        y = 100 + 12 * n
        ps += (
            text_line(["Label"], x=72, y=y, size=9) + right("0.10", 218, y) + right("0.20", 250, y)
        )
        ps += text_line(["Other"], x=72, y=y + 12, size=9)
        ps += text_line(["$1,000", "per", "month"], x=180, y=y + 12, size=9)
    return ps


def test_EX18_a_fusing_row_ends_the_table_and_is_reported() -> None:
    result = stage(long_table(4, fused=True))
    (table,) = result.tables
    assert len(table.shape.row_edges) - 1 == 5  # the four bands and `Label`
    assert [texts_of(region) for region in result.regions] == [["Other $1,000 per month"]]
    (left,) = [f for f in result.findings if f.code is FindingCode.TABLE_LEFT_AS_TEXT]
    assert left.page == 1
    assert left.detail.startswith("1 row of a table left as text")


def test_EX19_a_refused_table_costs_a_few_attempts_not_one_per_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = Mock(wraps=corridor_module.corridor_table)
    monkeypatch.setattr(corridor_module, "corridor_table", spy)
    (table,) = stage(long_table(200, fused=True)).tables
    assert len(table.shape.row_edges) - 1 == 201
    assert spy.call_count <= 4 * math.log2(200)


def test_EX20_a_long_table_costs_about_its_length() -> None:
    def best(n: int) -> float:
        ps = long_table(n)
        times = []
        for _ in range(3):  # the best of three: a slow run is the machine, not the code
            started = time.perf_counter()
            (table,) = stage(ps).tables
            times.append(time.perf_counter() - started)
        assert len(table.shape.row_edges) - 1 == n
        return min(times)

    # Eight times the rows: linear work grows 8 times, n log n about 11, quadratic 64.
    assert best(4000) < 16 * best(500)


def test_CG6_a_part_whose_widest_word_is_not_its_last_stays_in_its_cells() -> None:
    doc = read_with_tables(pdf_factory.chained_edge())
    for table in doc.tables():
        for cell in table.grid.cells:
            assert all(w in table.word_ids for w in cell.word_ids)


@pytest.mark.parametrize("text", ["CHF 250", "5 bp", "500 CHF", "10 %"])
def test_VP4_integer_money_with_a_separate_code_or_unit_is_a_value_piece(text: str) -> None:
    assert is_value_piece(words(text))


def test_CG7_rows_chained_by_a_centred_value_never_share_a_cell() -> None:
    doc = read_with_tables(pdf_factory.centred_span())
    for table in doc.tables():
        by_id = {w.id: w for w in doc.words}
        for cell in table.grid.cells:
            words = [by_id[w] for w in cell.word_ids]
            lines = group_lines(words, PROFILE)
            valued = [
                f for line in lines for f in fragments(line, PROFILE) if is_value_like(f.words)
            ]
            assert len(valued) <= 1, cell.text


def test_CG8_only_a_column_sized_gap_splits_a_piece() -> None:
    (line,) = group_lines(
        place(text_line(["Monthly", "minimum", "fee:"], x=150, y=100, size=9)), PROFILE
    )
    word_space = (line.words[0].bbox.x1 + line.words[1].bbox.x0) / 2
    assert len(_split(line, [word_space], 9.0)) == 1
    wide = [P("During", 200, 100, size=9), P("Auction", 232, 100, size=9)]  # 5 pt apart
    (apart,) = group_lines(place(wide), PROFILE)
    assert len(_split(apart, [229.5], 9.0)) == 2


def lse_rows(label_lines: int, *, value_on: float) -> list[P]:
    """A bold header over 4 rows whose labels are `label_lines` lines 10.9 pt apart.

    Rows are 19.3 pt apart; `value_on` is the label line the value sits on (0.5: centred between).
    """
    ps = [P("Scheme", 76, 100, size=9, bold=True), P("Charge", 494, 100, size=9, bold=True)]
    y = 122.0
    for n in range(4):
        ps += [P(f"label{n}line{i}", 76, y + 10.9 * i, size=9) for i in range(label_lines)]
        ps.append(P(f"0.{n}5bp", 494, y + 10.9 * value_on, size=9))
        y += 10.9 * (label_lines - 1) + 19.3
    return ps


def test_RW8_a_header_over_two_line_labels_stays_its_own_row() -> None:
    rows = rows_of(lse_rows(2, value_on=0.5))
    assert len(rows) == 5
    assert [w.text for w in rows[0].words] == ["Scheme", "Charge"]
    assert all(len(row.lines) == 3 for row in rows[1:])


def test_RW9_three_line_labels_are_one_row_each() -> None:
    rows = rows_of(lse_rows(3, value_on=1))
    assert len(rows) == 5
    for n, row in enumerate(rows[1:]):
        assert sorted(w.text for w in row.words if w.text.startswith("label")) == [
            f"label{n}line{i}" for i in range(3)
        ]


def test_RW10_headers_and_captions_never_join_distant_value_lines() -> None:
    ps: list[P] = []
    for n, y in enumerate((100, 180)):
        ps.append(P(f"OPTION{n}", 72, y, size=9, bold=True))
        ps += [P("Option", 200, y + 12, size=9), P("Other", 300, y + 12, size=9)]
        ps += [P("0.70bp", 200, y + 24, size=9), P("0.50bp", 300, y + 24, size=9)]
    rows = rows_of(ps)
    assert len(rows) == 6


def test_RW11_a_label_wrapped_under_a_top_value_stays_in_its_row() -> None:
    ps: list[P] = []
    y = 100.0
    for n in range(4):
        ps += [P(f"Post{n}", 76, y, size=9), P(f"\u00a3{n}05", 494, y, size=9)]
        if n == 1:
            ps += [P("CompID", 300, y + 7, size=9), P("only", 76, y + 14.8, size=9)]
            y += 14.8
        y += 19.3
    rows = rows_of(ps)
    assert [len(row.lines) for row in rows] == [1, 3, 1, 1]


def test_CG9_qualified_fees_stacked_in_one_column_are_two_rows() -> None:
    qualified = [
        P("Band", 72, 160, size=9),
        *text_line(["\u20ac10", "per", "million"], x=282, y=160, size=9),
    ]
    qualified += text_line(["\u20ac20", "per", "million"], x=282, y=165, size=9)
    rows = rows_of(value_rows(100, 3) + qualified)
    assert len(rows) == 5


def test_CG10_a_long_qualified_fee_under_another_is_never_its_cell() -> None:
    up_to = [
        *text_line(["Up", "to", "20,000"], x=72, y=160, size=9),
        P("\u20ac0", 300, 160, size=9),
    ]
    fee = ["\u20ac10", "per", "million", "on", "the", "value"]  # Euronext p25: six tokens
    between = text_line(["Between", "20,000", "and", "2m"], x=72, y=169, size=9)
    between += text_line(fee, x=282, y=169, size=9)
    ps = value_rows(100, 3) + up_to + between + value_rows(190, 2)
    assert len(rows_of(ps)) == 7
    cells = [cell for table in stage(ps).tables for cell in table.cells]
    assert not any({"\u20ac0", "\u20ac10"} <= {w.text for w in cell.words} for cell in cells)


def test_RW12_a_banner_wrapped_onto_a_value_line_stays_one_row() -> None:
    banner = text_line(["Option", "2", "minimum", "fee"], x=72, y=160, size=9, bold=True)
    banner += text_line(["\u20ac250,000", "(monthly)"], x=72, y=172.2, size=9)  # Euronext p8 pitch
    rows = rows_of(value_rows(100, 3) + banner + value_rows(188, 2))
    assert len(rows) == 6
    assert [" ".join(w.text for w in line.words) for line in rows[3].lines] == [
        "Option 2 minimum fee",
        "\u20ac250,000 (monthly)",
    ]


def test_RW13_cells_under_a_paragraph_line_start_a_row() -> None:
    text = "If a member also joins the Best of Book programme the variable fee is"
    paragraph = text_line(text.split(), x=72, y=170, size=9)
    header = [P("Option", 100, 181, size=9), P("A", 128, 181, size=9)]
    header += [P("Option", 282, 181, size=9), P("B", 310, 181, size=9)]  # Euronext p15
    rows = rows_of(value_rows(100, 3) + paragraph + header + value_rows(200, 2))
    assert row_texts(rows)[3:5] == [
        ["If a member also joins the Best of Book programme the variable fee is"],
        ["Option A Option B"],
    ]


def test_RW14_a_bold_caption_over_a_regular_value_line_is_a_row_of_its_own() -> None:
    caption = [P("OPTION", 72, 161, size=9, bold=True), P("2", 102, 161, size=9, bold=True)]
    fee = [P("Monthly", 72, 170, size=9), P("fee", 110, 170, size=9), P("6,000", 282, 170, size=9)]
    rows = rows_of(value_rows(100, 3) + caption + fee + value_rows(190, 2))  # Euronext p21
    assert row_texts(rows)[3:5] == [["OPTION 2"], ["Monthly fee 6,000"]]


def test_RW15_a_bold_label_in_a_column_of_its_own_joins_its_value_row() -> None:
    below = [P("Total", 150, 160, size=9), P("below", 175, 160, size=9), P("1", 282, 160, size=9)]
    label = [P("REQUESTOR", 72, 167, size=9, bold=True)]
    above = [P("Total", 150, 180, size=9), P("above", 175, 180, size=9), P("0", 282, 180, size=9)]
    rows = rows_of(value_rows(100, 3) + below + label + above + value_rows(200, 2))  # Euronext p24
    assert row_texts(rows)[3:5] == [["Total below 1", "REQUESTOR"], ["Total above 0"]]


def test_RW16_a_bold_label_wrapped_onto_its_value_line_joins_it() -> None:
    label = text_line(["INTERMEDIARY", "AUTHORISED"], x=72, y=160, size=9, bold=True)
    value = text_line(["TO", "RESPOND"], x=72, y=168, size=9, bold=True)
    value += text_line(["\u20ac10", "per", "million"], x=282, y=168, size=9)  # Euronext p25
    rows = rows_of(value_rows(100, 3) + label + value + value_rows(188, 2))
    assert row_texts(rows)[3] == ["INTERMEDIARY AUTHORISED", "TO RESPOND \u20ac10 per million"]


def test_RW17_cells_wrapped_together_join_their_value_row() -> None:
    row = text_line(["Total", "value", "equal"], x=72, y=160, size=9)
    row += text_line(["0.15", "bps,"], x=282, y=160, size=9)
    wrap = text_line(["to", "or", "below", "\u20ac100,000:"], x=72, y=169, size=9)
    wrap += text_line(["min", "\u20ac2.5", "per", "executed", "order"], x=282, y=169, size=9)
    rows = rows_of(value_rows(100, 3) + row + wrap + value_rows(180, 2))  # Euronext p37
    assert row_texts(rows)[3] == [
        "Total value equal 0.15 bps,",
        "to or below \u20ac100,000: min \u20ac2.5 per executed order",
    ]


def test_RW18_a_bold_header_under_a_value_row_is_a_row_of_its_own() -> None:
    header = text_line(["Tier"], x=72, y=149, size=9, bold=True)
    header += text_line(["Charge"], x=282, y=149, size=9, bold=True)
    rows = rows_of(value_rows(100, 3) + header + value_rows(160, 2))
    assert row_texts(rows)[2:4] == [["Row2 0.25"], ["Tier Charge"]]
