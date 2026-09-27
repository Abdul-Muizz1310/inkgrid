from collections.abc import Sequence
from typing import Any

import pytest

from inkgrid.core.assemble import assemble
from inkgrid.core.calls import (
    CallSite,
    Candidate,
    Note,
    calls_in,
    named_calls,
    parenthetical_calls,
    resolve,
)
from inkgrid.core.furniture import FoundFurniture
from inkgrid.core.lines import group_lines
from inkgrid.core.prose import ProtoBlock
from inkgrid.core.tables.lattice import lattice_tables
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.document import Document
from inkgrid.model.findings import FindingCode
from inkgrid.model.geometry import Rect
from inkgrid.model.page import PageModel, Reading, Word
from layout_builder import P, place, text_line
from model_builders import mk_page, mk_reading

PROFILE = Profile()
LEXICON = Lexicon()
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


def test_FC21_an_enumerator_after_has_is_no_call() -> None:
    # MEMX (4c73123c9319 p8): a sentence enumerating its conditions after a verb
    assert rejected("a Member has (1) a Tape B ADAV of at least 0.10%") == [("1", "function-word")]


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


# --- Resolution (spec 09 section 3) --------------------------------------------------------------


def site(order: int, page: int, label: str, *, method: str = "superscript") -> CallSite:
    return CallSite(order, page, None, Candidate(label, method))  # type: ignore[arg-type]


def test_FR1_a_label_printed_once_resolves_at_any_distance() -> None:
    assert resolve([site(0, 1, "3")], [Note(5, 4, "3")]) == [5]


def test_FR2_repeated_labels_resolve_to_the_notes_on_their_own_pages() -> None:
    notes = [Note(1, 1, "1"), Note(4, 3, "1")]
    assert resolve([site(0, 1, "1"), site(3, 3, "1")], notes) == [1, 4]


def test_FR3_a_repeated_label_with_no_note_nearby_is_unresolved() -> None:
    assert resolve([site(0, 1, "1")], [Note(2, 3, "1"), Note(4, 5, "1")]) == [None]


def test_FR4_a_call_never_resolves_backward() -> None:
    assert resolve([site(1, 2, "2")], [Note(0, 1, "2")]) == [None]


def test_FR5_a_continuing_tables_calls_count_from_its_last_page() -> None:
    # the calling table starts on page 4; its chain ends on page 5, which is the site's page
    assert resolve([site(0, 5, "1")], [Note(1, 5, "1"), Note(3, 9, "1")]) == [1]


def test_FR_a_rejected_candidate_never_resolves() -> None:
    rejected_site = CallSite(0, 1, None, Candidate("1", "parenthetical", "function-word"))
    assert resolve([rejected_site], [Note(1, 1, "1")]) == [None]


# --- Links through assembly (spec 09 sections 2-3) -----------------------------------------------


def reading_of(specs: Sequence[Sequence[P]]) -> Reading:
    pages: list[PageModel] = []
    next_id = 0
    for number, ps in enumerate(specs, 1):
        ws = place(ps, page=number, first_id=next_id)
        next_id += len(ws)
        pages.append(mk_page(number=number, words=ws, text_layer="full" if ws else "none"))
    return mk_reading(tuple(pages))


def document(pages: Sequence[Sequence[tuple[str, str | None, list[P]]]], **kw: Any) -> Document:
    """Assemble pages of `(kind, label, placements)` blocks, one line each, ids in page order."""
    specs = [[p for _, _, ps in page for p in ps] for page in pages]
    reading = reading_of(specs)
    placed = iter(w for page in reading.pages for w in page.words)
    out: list[tuple[ProtoBlock, ...]] = []
    for page in pages:
        blocks = []
        for kind, label, ps in page:
            ws = tuple(next(placed) for _ in ps)
            lines = group_lines(ws, PROFILE)
            blocks.append(ProtoBlock(kind, lines, lines[0].size, label=label))  # type: ignore[arg-type]
        out.append(tuple(blocks))
    empty = FoundFurniture((), frozenset())
    return assemble(reading, out, empty, lexicon=LEXICON, profile=PROFILE, lattice="combined", **kw)


def said(text: str, y: float, *, size: float = 10) -> list[P]:
    return text_line(text.split(), x=72, y=y, size=size)


def summary(doc: Document) -> list[tuple[str, str | None, str | None, str, str | None]]:
    return [(k.from_.block, k.to, k.label, k.status, k.reason) for k in doc.links]


def test_FR6_a_paragraph_links_its_call_and_records_the_rejection() -> None:
    text = "transaction fees in all products except (1) Underlying Symbol List A (34), DJX"
    doc = document(
        [
            [
                ("paragraph", None, said(text, 100)),
                ("footnote", "1", said("1 Applies to members trading", 700, size=7)),
                ("footnote", "34", said("34 Applies to the list only", 712, size=7)),
            ]
        ]
    )
    assert summary(doc) == [
        ("b1", None, "1", "rejected", "function-word"),
        ("b1", "b3", "34", "resolved", None),
    ]


def test_FR7_a_call_in_a_table_cell_links_from_the_cell() -> None:
    ps = [P("Fee", 76, 106), P("Cap", 176, 106), P("Band", 76, 126), P("$1.00", 176, 126)]
    ps.append(P("2", 202, 123.5, size=6, superscript=True))
    note = said("2 Applies to every member trading", 200, size=7)
    reading = reading_of([ps + note])
    words = reading.pages[0].words
    rects = [Rect(72, 100, 172, 120), Rect(172, 100, 272, 120)]
    rects += [Rect(72, 120, 172, 140), Rect(172, 120, 272, 140)]
    stage = lattice_tables(reading.pages[0], [rects], words, PROFILE, frame=0, read=True)
    (table,) = stage.tables
    lines = group_lines(words[len(ps) :], PROFILE)
    blocks = ((ProtoBlock("footnote", lines, lines[0].size, label="2"),),)
    empty = FoundFurniture((), frozenset())
    doc = assemble(
        reading, blocks, empty, lexicon=LEXICON, profile=PROFILE, lattice="combined",
        tables=[(table,)],
    )  # fmt: skip
    (link,) = doc.links
    assert (link.from_.block, link.from_.cell, link.to, link.status) == (
        "b1",
        (1, 1),
        "b2",
        "resolved",
    )


def test_FR8_a_note_never_calls_itself() -> None:
    doc = document(
        [[("footnote", "27", said("27 Please see footnote 27 for details", 700, size=7))]]
    )
    assert doc.links == ()


def test_FR_unresolved_calls_raise_one_finding_per_page() -> None:
    ps = [P("Fee", 72, 100), P("4", 90, 96.5, size=6, superscript=True)]
    ps += [P("Cap", 100, 100), P("9", 118, 96.5, size=6, superscript=True)]
    doc = document([[("paragraph", None, ps)]])
    assert [k.status for k in doc.links] == ["unresolved", "unresolved"]
    (finding,) = [f for f in doc.findings if f.code is FindingCode.CALL_UNRESOLVED]
    assert (finding.page, finding.detail) == (1, "2 footnote calls resolve to no note: 4, 9")


def test_FR9_one_label_called_twice_by_one_method_gives_one_link() -> None:
    ps = [P("Fee", 72, 100), P("2", 90, 96.5, size=6, superscript=True)]
    ps += [P("Cap", 100, 100), P("2", 118, 96.5, size=6, superscript=True)]
    doc = document(
        [
            [("paragraph", None, ps)],
            [("footnote", "2", said("2 Applies to all members", 700, size=7))],
        ]
    )
    assert [(k.label, k.status) for k in doc.links] == [("2", "resolved")]
