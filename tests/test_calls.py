import pytest

from inkgrid.core.calls import Candidate, calls_in, named_calls, parenthetical_calls
from inkgrid.model.page import Word
from layout_builder import P, place

REGISTER = frozenset(str(n) for n in range(1, 55))  # every label: the convention decides


def words(*ps: P) -> tuple[Word, ...]:
    return place(list(ps))


def accepted(text: str) -> list[str]:
    return [c.label for c in parenthetical_calls(text, REGISTER) if c.reason is None]


def rejected(text: str) -> list[tuple[str, str | None]]:
    return [
        (c.label, c.reason) for c in parenthetical_calls(text, REGISTER) if c.reason is not None
    ]


# --- Superscript calls (spec 09 section 2.1) -----------------------------------------------------


def test_SP1_a_raised_number_after_a_fee_is_a_call() -> None:
    ws = words(P("$0.40", 72, 100), P("2", 97, 96.5, size=6.5, superscript=True))
    assert calls_in("paragraph", ws, "$0.40 2", REGISTER) == [Candidate("2", "superscript")]


def test_SP2_lists_and_runs_of_marks_are_several_calls() -> None:
    ws = words(
        P("Fee", 72, 100),
        P("1,3,5", 90, 96.5, size=6.5, superscript=True),
        P("Cap", 120, 100),
        P("(2)(3)", 140, 96.5, size=6.5, superscript=True),
    )
    labels = [c.label for c in calls_in("paragraph", ws, "Fee 1,3,5 Cap (2)(3)", frozenset())]
    assert labels == ["1", "3", "5", "2", "3"]


def test_SP3_ordinals_and_trade_marks_are_no_calls() -> None:
    ws = words(
        P("2", 72, 100),
        P("nd", 78, 96.5, size=6.5, superscript=True),
        P("Nasdaq", 100, 100),
        P("SM", 140, 96.5, size=6.5, superscript=True),
    )
    assert calls_in("paragraph", ws, "2nd Nasdaq SM", REGISTER) == []


def test_SP4_a_footnotes_own_label_is_no_call() -> None:
    ws = words(P("^", 72, 99, size=7, superscript=True), P("Contra", 80, 100), P("fees", 120, 100))
    assert calls_in("footnote", ws, "^ Contra fees", REGISTER, own_label="^") == []


# --- Parenthetical calls: the prototype's nineteen text cases (spec 09 section 2.2) --------------


@pytest.mark.parametrize(
    ("case", "text", "calls"),
    [
        ("FC1", "AIM Agency/Primary (19)", ["19"]),
        ("FC2", "Customer (2)(8)(9)", ["2", "8", "9"]),
        ("FC3", "Sector Indexes (47)(11)", ["47", "11"]),
        ("FC4", "$0.00 (47)", ["47"]),
        ("FC5", "Volume Incentive Program (VIP)(6)(23)(36)", ["6", "23", "36"]),
        ("FC6", "Surcharge Fee (14) (Also applies to GTH)(37)(42)", ["14", "37", "42"]),
        (
            "FC7",
            "Rate Table - All Products Excluding Underlying Symbol List A (34) and Binary Options",
            ["34"],
        ),
        ("FC8", "Underlying Symbol List A (34) (except RLG, RLV, RUI, and UKXM)", ["34"]),
        ("FC9", "involves a complex order with at least five (5) different series", []),
        ("FC10", "for a period of two (2) years from the date of enrollment", []),
        (
            "FC11",
            "as that term is defined in Section 202(a)(11) of the Investment Advisers Act",
            [],
        ),
        (
            "FC12",
            "transaction fees in all products except (1) Underlying Symbol List A (34), DJX",
            ["34"],
        ),
        ("FC13", "(2) volume executed in open outcry, (3) volume executed via AIM Responses", []),
        ("FC14", "organization; (2) if the trading floor reopens mid-month", []),
        ("FC15", "calendar month; and (9) the AIM Contra Surcharge", []),
        ("FC16", "(1) TPH has SPX Customer capacity volume during the month", []),
        ("FC17", "Fees are assessed only on items that are (1) lost or (2) damaged", []),
        ("FC18", "payable in 2026 (99) and thereafter", []),
    ],
)
def test_FC1_to_FC18_the_prototype_call_cases(case: str, text: str, calls: list[str]) -> None:
    assert accepted(text) == calls, case


@pytest.mark.parametrize(
    ("text", "reasons"),
    [
        (
            "involves a complex order with at least five (5) different series",
            [("5", "spelled-number-gloss")],
        ),
        ("for a period of two (2) years", [("2", "spelled-number-gloss")]),
        ("defined in Section 202(a)(11) of the Act", [("11", "statutory-citation")]),
        ("in all products except (1) Underlying Symbol List A (34), DJX", [("1", "function-word")]),
        (
            "(2) volume executed in open outcry, (3) volume executed via AIM",
            [("2", "clause-initial"), ("3", "sub-clause-enumerator")],
        ),
        ("organization; (2) if the trading floor reopens", [("2", "sub-clause-enumerator")]),
        ("calendar month; and (9) the AIM Contra Surcharge", [("9", "function-word")]),
        (
            "items that are (1) lost or (2) damaged",
            [("1", "function-word"), ("2", "function-word")],
        ),
        ("the year 2026(5) applies", [("5", "attached-to-number")]),
        ("a rule \u2014 (4) applies", [("4", "no-anchor")]),
    ],
)
def test_FC_rejections_name_their_convention(text: str, reasons: list[tuple[str, str]]) -> None:
    assert rejected(text) == reasons


def test_FC18_a_number_no_note_carries_is_no_candidate() -> None:
    assert parenthetical_calls("payable in 2026 (99) and thereafter", REGISTER) == []


def test_FC19_a_named_reference_is_a_call() -> None:
    text = "Please see Customer Large Trade Discounts table and footnote 27 for details"
    assert named_calls(text) == [Candidate("27", "named")]
    assert parenthetical_calls(text, REGISTER) == []


def test_FC20_an_inverse_declaration_is_no_call() -> None:
    text = "Add/Remove Volume Tiers. Applicable to the following fee codes: B, V and Y."
    ws = place([P(t, 72 + 40 * i, 100) for i, t in enumerate(text.split())])
    assert calls_in("footnote", ws, text, REGISTER, own_label="3") == []
