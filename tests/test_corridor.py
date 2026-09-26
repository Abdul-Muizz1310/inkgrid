import pytest

from inkgrid.core.lines import group_lines
from inkgrid.core.tables.corridor import Row, fold_rows, is_value_like, is_value_piece
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
