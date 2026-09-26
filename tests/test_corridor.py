import pytest

from inkgrid.core.lines import group_lines
from inkgrid.core.tables.corridor import (
    Row,
    columns,
    corridor_table,
    fold_rows,
    is_value_like,
    is_value_piece,
)
from inkgrid.core.tables.proto import ProtoTable
from inkgrid.model.config import Profile
from inkgrid.model.page import Word
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
