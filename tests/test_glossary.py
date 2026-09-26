from collections.abc import Sequence

from inkgrid.core.glossary import as_definition
from inkgrid.core.layout import Region
from inkgrid.core.lines import group_lines
from inkgrid.core.prose import ProtoBlock, line_gaps, page_blocks
from inkgrid.core.text import block_text
from inkgrid.model.config import Lexicon, Profile
from layout_builder import P, place, text_line

PROFILE = Profile()
LEXICON = Lexicon()
BODY = 10.0
OPEN, CLOSE = "\u201c", "\u201d"


def blocks_of(ps: Sequence[P]) -> tuple[ProtoBlock, ...]:
    region = Region("prose", group_lines(place(ps), PROFILE))
    return page_blocks((region,), LEXICON, PROFILE, BODY, line_gaps((region,)))


def only(ps: Sequence[P]) -> ProtoBlock:
    (block,) = blocks_of(ps)
    return block


def said(text: str, *, y: float = 100, x: float = 72) -> list[P]:
    return text_line(text.split(), x=x, y=y)


def term_and_body(block: ProtoBlock, *, in_scope: bool = True) -> tuple[str, str] | str:
    """The definition's term and body, or the kind the block kept."""
    got = as_definition(block, in_scope=in_scope, profile=PROFILE)
    if got.kind != "definition":
        return got.kind
    return block_text(got.term)[0], block_text(got.lines[len(got.term) :])[0]


def test_DF1_a_quoted_term_opens_a_definition() -> None:
    block = only(said(f"{OPEN}ABBO{CLOSE} means the best bid(s) or offer(s) disseminated"))
    assert term_and_body(block) == (
        f"{OPEN}ABBO{CLOSE}",
        "means the best bid(s) or offer(s) disseminated",
    )


def test_DF2_alternate_quoted_terms_chain() -> None:
    text = f"{OPEN}Electronic Exchange Member{CLOSE} or {OPEN}EEM{CLOSE} means the holder of"
    term, body = term_and_body(only(said(text)))
    assert term == f"{OPEN}Electronic Exchange Member{CLOSE} or {OPEN}EEM{CLOSE}"
    assert body == "means the holder of"


def test_DF3_a_parenthetical_after_the_term_belongs_to_it() -> None:
    text = f"{OPEN}Dedicated{CLOSE} (cross-connect) means cross-connect that provides"
    term, _ = term_and_body(only(said(text)))
    assert term == f"{OPEN}Dedicated{CLOSE} (cross-connect)"


def test_DF4_outside_a_scope_only_a_defining_verb_makes_a_definition() -> None:
    defined = only(said(f"{OPEN}SMQ Payout{CLOSE} shall mean the lump sum payment"))
    assert term_and_body(defined, in_scope=False) == (
        f"{OPEN}SMQ Payout{CLOSE}",
        "shall mean the lump sum payment",
    )
    described = only(said(f"{OPEN}Purge Ports{CLOSE} provide Market Makers with the ability"))
    assert term_and_body(described, in_scope=False) == "paragraph"


def test_DF5_a_bold_lead_is_a_term_inside_a_scope() -> None:
    ps = text_line(["Available", "for", "Distribution:"], x=72, y=100, bold=True)
    ps += text_line(
        ["Instruments", "that", "can", "be", "offered", "for", "distribution", "to", "investors"],
        x=195,
        y=100,
    )
    assert term_and_body(only(ps)) == (
        "Available for Distribution:",
        "Instruments that can be offered for distribution to investors",
    )
    assert term_and_body(only(ps), in_scope=False) == "paragraph"


def test_DF6_a_paragraph_bold_throughout_has_no_term() -> None:
    ps: list[P] = []
    for i in range(3):
        words = [
            "These",
            "fees",
            "apply",
            "to",
            "every",
            "member",
            "of",
            "the",
            "Exchange",
            "in",
            "full.",
        ]
        ps += text_line(words, x=72, y=100 + 12 * i, bold=True)
    assert term_and_body(only(ps)) == "paragraph"


def hanging(first_x: float, *, term: str = "Access") -> list[P]:
    ps = [P(term, 57, 100)]
    ps += text_line(["Connection", "of", "physical", "data", "line", "to", "the"], x=190, y=100)
    ps += text_line(["Exchange", "network."], x=first_x, y=112)
    return ps


def test_DF7_a_hanging_term_sits_in_a_column_of_its_own() -> None:
    assert term_and_body(only(hanging(190))) == (
        "Access",
        "Connection of physical data line to the Exchange network.",
    )


def test_DF8_a_line_back_at_the_margin_is_no_hanging_indent() -> None:
    assert term_and_body(only(hanging(57))) == "paragraph"


def test_DF9_a_hanging_note_number_is_not_a_term() -> None:
    ps = [P("1", 57, 100)]
    ps += text_line(["Trade", "activity", "on", "days", "when", "the", "market"], x=100, y=100)
    ps += text_line(["closes", "early", "is", "excluded."], x=100, y=112)
    assert term_and_body(only(ps)) == "paragraph"


def test_DF10_a_numbered_definition_stays_a_list_item() -> None:
    block = only(said(f"1. {OPEN}CADV{CLOSE} means the consolidated average daily volume"))
    assert block.kind == "list_item"
    assert term_and_body(block) == "list_item"


def test_DF11_a_colon_without_bold_is_not_a_term() -> None:
    block = only(said("2 These transaction fees do not apply to: Directed Orders"))
    assert term_and_body(block) == "paragraph"


def test_DF12_a_quote_that_does_not_close_is_not_a_term() -> None:
    words = " ".join(["word"] * 13)
    block = only(said(f"{OPEN}Fee is charged per trade {words} and more"))
    assert term_and_body(block) == "paragraph"


def test_DF13_a_term_needs_a_body() -> None:
    assert term_and_body(only(said(f"{OPEN}ABBO{CLOSE}"))) == "paragraph"
