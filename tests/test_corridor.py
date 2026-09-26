import pytest

from inkgrid.core.tables.corridor import is_value_like, is_value_piece
from inkgrid.model.page import Word
from layout_builder import P, place, text_line


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
