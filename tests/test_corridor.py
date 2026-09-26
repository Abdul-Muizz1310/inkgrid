import pytest

from inkgrid.core.layout import Region
from inkgrid.core.lines import group_lines
from inkgrid.core.tables.corridor import (
    CorridorStage,
    Row,
    columns,
    corridor_table,
    corridor_tables,
    fold_rows,
    is_value_like,
    is_value_piece,
)
from inkgrid.core.tables.proto import ProtoTable
from inkgrid.model.config import Profile
from inkgrid.model.page import Rule, Word
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


def test_RW2_values_stacked_in_one_column_are_rows_of_their_own() -> None:
    ps = []
    for n, y in enumerate((100.0, 109.5, 119.0)):
        ps += [P(f"Band{n}", 72, y, size=9), P(f"\u20ac0.1{n}", 200, y, size=9)]
    assert len(rows_of(ps)) == 3


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
    ps = [
        *text_line(["151", "\u2013", "500"], x=72, y=100),
        *text_line(["501", "\u2013", "1,000"], x=72, y=110),
    ]
    assert len(rows_of(ps)) == 2


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
    sentence = text_line(
        ["The", "standard", "fees", "for", "members", "trading", "on", "the", "book", "are:"],
        x=72,
        y=88,
        size=9,
    )
    wide = [*sentence, P("follows", 520, 88, size=9)]
    result = stage(wide + header_row(100) + six_rows(112))
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
    # Two rows of three lines 5 pt apart; without the rule, `above` would fold into the first row.
    ps = [
        P("Requestor", 72, 100, size=9),
        P("\u20ac2", 300, 105, size=9),
        P("below", 72, 110, size=9),
    ]
    ps += [P("above", 72, 115, size=9), P("\u20ac0", 300, 120, size=9), P("limit", 72, 125, size=9)]
    ps += [
        p
        for n in range(6)
        for p in (
            P(f"Other{n}", 72, 140 + 15 * n, size=9),
            P(f"\u20ac{n}", 300, 140 + 15 * n, size=9),
        )
    ]
    rule = Rule(page=1, axis="h", at=117, start=60, end=320, thickness=0.5)
    ruled = fold_rows(group_lines(place(ps), PROFILE), PROFILE, rules=(rule,))
    assert row_texts(ruled)[:2] == [
        ["Requestor", "\u20ac2", "below"],
        ["above", "\u20ac0", "limit"],
    ]
    unruled = fold_rows(group_lines(place(ps), PROFILE), PROFILE)
    assert row_texts(unruled)[0] == ["Requestor", "\u20ac2", "below", "above"]


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
