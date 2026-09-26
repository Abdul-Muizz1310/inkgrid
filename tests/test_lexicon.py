import pytest

from inkgrid.core.lexicon import (
    enumerator,
    is_bullet,
    is_strong_value,
    is_value,
    note_label,
    section_number,
)
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


@pytest.mark.parametrize(
    "text", ["0.40", "1,234.5", "1.234,5", "1 234", "1'234", "\u22120.10", "12"]
)
def test_VL1_numbers_are_values(text: str) -> None:
    assert is_value(text)


@pytest.mark.parametrize(
    "text",
    [
        "$0.40",
        "R 0.00",
        "0.13 EUR",
        "20,000 \u20ac",
        "\u20ac1.4bn",
        "-0.15bp",
        "0.45bp*",
        "12%",
        "CHF 25",
        "$575/port/month",
        "0.10/contract",
    ],
)
def test_VL2_money_and_units_are_values(text: str) -> None:
    assert is_value(text)


@pytest.mark.parametrize(
    "text", ["(47)", "($0.10)", "0.10 - 0.20", "1\u20135", "\u2014", "n/a", "Free"]
)
def test_VL3_negatives_ranges_and_placeholders_are_values(text: str) -> None:
    assert is_value(text)


@pytest.mark.parametrize(
    "text", ["2026", "Tier 1", "Monthly", "0.10 per contract", "ZAR (Ex VAT)", "", "1.2.3"]
)
def test_VL4_labels_are_not_values(text: str) -> None:
    assert not is_value(text)


@pytest.mark.parametrize(
    ("token", "strong"),
    [
        ("$0.00", True),
        ("0.0030", True),
        ("5,000", True),
        ("12%", True),
        ("0.25bp", True),
        ("R0.00", True),
        ("1", False),
        ("12", False),
        ("(47)", False),
        ("\u2014", False),
        ("n/a", False),
        ("2026", False),
        ("1-5", False),
    ],
)
def test_VL5_strong_values_carry_a_unit_decimal_or_grouping(token: str, strong: bool) -> None:
    assert is_strong_value(token) is strong


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("LPS2", False),
        ("CAT 1", False),
        ("SEC 31", False),
        ("MAX 10", False),
        ("VAT 15%", False),
        ("LPS2 CLOB tariff", False),
        ("NOK 1,200", True),
        ("ZAR 5", True),
        ("0.13 EUR", True),
    ],
)
def test_VL6_only_iso_4217_codes_are_currencies(text: str, value: bool) -> None:
    assert is_value(text) is value
