import pytest

from inkgrid.core.lexicon import enumerator, is_bullet, note_label, section_number
from inkgrid.model.config import Lexicon

LEXICON = Lexicon()


@pytest.mark.parametrize(
    ("token", "expected"),
    [("\u2022", True), ("-", True), ("\u25a0", True), ("--", False), ("a", False)],
)
def test_CF6_is_bullet(token: str, expected: bool) -> None:
    assert is_bullet(token, LEXICON) is expected


@pytest.mark.parametrize("token", ["1.", "12)", "(3)", "a)", "(b)", "iv.", "(ii)", "A."])
def test_CF7_enumerators_are_returned_as_printed(token: str) -> None:
    assert enumerator(token) == token


@pytest.mark.parametrize("token", ["1", "(12", "$1.", "1.5", "abc.", "(1)(2)", "1234."])
def test_CF8_non_labels_are_not_enumerators(token: str) -> None:
    assert enumerator(token) is None


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("2.", "2."),
        ("2.1", "2.1"),
        ("2.1.10", "2.1.10"),
        ("C.", "C."),
        ("2026", None),
        ("1999.", "1999."),
        ("2.a", None),
    ],
)
def test_CF9_section_number(token: str, expected: str | None) -> None:
    assert section_number(token) == expected


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("3", "3"),
        ("(3)", "(3)"),
        ("*", "*"),
        ("\u2020\u2021", "\u2020\u2021"),
        ("12a", None),
        ("1234", None),
    ],
)
def test_CF10_note_label(token: str, expected: str | None) -> None:
    assert note_label(token) == expected
