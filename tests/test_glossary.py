from collections.abc import Sequence

from inkgrid.core.glossary import as_definition, dissolve, glossary, is_definitions_title
from inkgrid.core.layout import Region
from inkgrid.core.lines import group_lines
from inkgrid.core.prose import ProtoBlock, line_gaps, page_blocks
from inkgrid.core.tables.lattice import lattice_tables
from inkgrid.core.tables.proto import ProtoTable
from inkgrid.core.text import block_text
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.geometry import Rect
from layout_builder import P, place, text_line
from model_builders import mk_page

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


# --- Scopes (spec 08 section 1) ------------------------------------------------------------


def page(*parts: list[P], number: int = 1, first_id: int = 0) -> tuple[ProtoBlock, ...]:
    ps = [p for part in parts for p in part]
    region = Region("prose", group_lines(place(ps, page=number, first_id=first_id), PROFILE))
    return page_blocks((region,), LEXICON, PROFILE, BODY, line_gaps((region,)))


def heading(text: str, *, y: float, size: float = 12) -> list[P]:
    return text_line(text.split(), x=72, y=y, size=size, bold=True)


def kinds(pages: Sequence[Sequence[ProtoBlock]]) -> list[str]:
    out, _ = glossary(pages, [() for _ in pages], marks=frozenset(), profile=PROFILE)
    return [b.kind for blocks in out for b in blocks]


APPLIES = f"{OPEN}Fee{CLOSE} applies to all trades on the order book"


def test_SC1_a_scope_ends_at_the_next_heading_of_its_level() -> None:
    blocks = page(
        heading("Definitions", y=80),
        said(f"{OPEN}Fee{CLOSE} means a charge on a trade", y=100),
        heading("Fees", y=130),
        said(APPLIES, y=150),
    )
    assert kinds([blocks]) == ["heading", "definition", "heading", "paragraph"]


def test_SC2_a_sub_heading_keeps_the_scope() -> None:
    blocks = page(
        heading("Fee Schedule", y=60, size=16),
        heading("2 Definitions", y=90, size=14),
        heading("Trading terms", y=120),
        said(APPLIES, y=140),
        heading("3 Fees", y=170, size=14),
        said(APPLIES, y=200),
    )
    assert kinds([blocks]) == ["heading"] * 3 + ["definition", "heading", "paragraph"]


def test_SC3_a_contents_line_opens_no_scope() -> None:
    blocks = page(heading("Definitions .......... 4", y=80), said(APPLIES, y=100))
    assert kinds([blocks]) == ["heading", "paragraph"]


def test_SC4_a_long_heading_mentioning_definitions_opens_no_scope() -> None:
    title = "Definitions of the fees for members trading on markets"  # nine words
    blocks = page(heading(title, y=80), said(APPLIES, y=100))
    assert kinds([blocks]) == ["heading", "paragraph"]


def test_SC5_a_scope_runs_across_a_page_break() -> None:
    first = page(heading("Definitions", y=80), said(APPLIES, y=100))
    second = page(said(APPLIES, y=100), number=2, first_id=100)
    assert kinds([first, second]) == ["heading", "definition", "definition"]


def test_SC6_numbered_and_bracketed_titles_open_scopes() -> None:
    assert is_definitions_title("4.2.1.1 DEFINITIONS")
    assert is_definitions_title("I. Definitions (applicable for purposes of fees):")
    assert is_definitions_title("Legend")
    assert is_definitions_title("Defined terms")
    assert not is_definitions_title("Fees and charges")


# --- Grids (spec 08 section 3) -------------------------------------------------------------


def grid(
    rows: Sequence[Sequence[str]], *, banner: str | None = None, y0: float = 200, cols: int = 2
) -> ProtoTable:
    """A ruled grid of `rows`, 24 pt high, its first column 120 pt wide, the rest 240 pt."""
    xs = [72.0, 192.0] + [192.0 + 240.0 * (i + 1) for i in range(cols - 1)]
    rects: list[Rect] = []
    ps: list[P] = []
    y = y0
    if banner is not None:
        rects.append(Rect(xs[0], y, xs[-1], y + 24))
        ps += text_line(banner.split(), x=xs[0] + 4, y=y + 8, size=9, bold=True)
        y += 24
    for row in rows:
        for c, text in enumerate(row):
            rects.append(Rect(xs[c], y, xs[c + 1], y + 24))
            ps += text_line(text.split(), x=xs[c] + 4, y=y + 8, size=9)
        y += 24
    words = place(ps)
    stage = lattice_tables(mk_page(words=words), [rects], words, PROFILE, frame=0, read=True)
    (table,) = stage.tables
    return table


def shown(blocks: Sequence[ProtoBlock]) -> list[tuple[str, str]]:
    out = []
    for b in blocks:
        if b.kind == "definition":
            out.append((b.kind, block_text(b.term)[0]))
        elif b.kind == "footnote":
            out.append((b.kind, b.label or ""))
        else:
            out.append((b.kind, block_text(b.lines)[0]))
    return out


RATES = ["Tier A", "Metro areas of Amsterdam, Frankfurt and London"]
REBATE = ["X2", "Connection rebate: the monthly fees are reduced"]


def test_NL1_a_legend_grid_dissolves_into_its_heading_terms_and_notes() -> None:
    table = grid([RATES, REBATE], banner="Legend")
    blocks = dissolve(table, in_scope=False, marks=frozenset({"X2"}), profile=PROFILE)
    assert blocks is not None
    assert shown(blocks) == [("heading", "Legend"), ("definition", "Tier A"), ("footnote", "X2")]


GLOSSARY = [
    ["Access", "Connection of physical data line to the Exchange network"],
    ["bp", "Basis points (1/100th of a percentage point)."],
]


def test_NL2_a_grid_under_a_definitions_heading_is_a_glossary() -> None:
    blocks = page(heading("Definitions", y=150))
    out, tables = glossary([blocks], [(grid(GLOSSARY),)], marks=frozenset(), profile=PROFILE)
    assert tables == [()]
    assert shown(out[0]) == [
        ("heading", "Definitions"),
        ("definition", "Access"),
        ("definition", "bp"),
    ]


def test_NL3_the_same_grid_outside_a_scope_stays_a_table() -> None:
    table = grid(GLOSSARY)
    out, tables = glossary([()], [(table,)], marks=frozenset(), profile=PROFILE)
    assert (out, tables) == ([()], [(table,)])


def test_NL4_a_numbered_note_grid_becomes_footnotes_anywhere() -> None:
    notes = [
        ["1", "Applies to members trading on the market"],
        ["2", "Excludes orders routed to other venues"],
    ]
    blocks = dissolve(grid(notes), in_scope=False, marks=frozenset(), profile=PROFILE)
    assert blocks is not None
    assert shown(blocks) == [("footnote", "1"), ("footnote", "2")]


def test_NL5_a_value_row_keeps_the_grid_a_table() -> None:
    table = grid([*GLOSSARY, ["Monthly fee", "CHF 250"]])
    assert dissolve(table, in_scope=True, marks=frozenset(), profile=PROFILE) is None


def test_NL6_a_three_column_grid_stays_a_table() -> None:
    table = grid([[*row, "extra words in a third column"] for row in GLOSSARY], cols=3)
    assert dissolve(table, in_scope=True, marks=frozenset(), profile=PROFILE) is None


def test_NL7_a_label_no_superscript_spells_is_no_note() -> None:
    table = grid([REBATE, ["X3", "Connection rebate for transaction connections"]])
    assert dissolve(table, in_scope=False, marks=frozenset(), profile=PROFILE) is None


def test_NL8_a_note_row_whose_text_is_a_fee_keeps_the_table() -> None:
    table = grid([["1", "$0.25 per contract"], REBATE])
    assert dissolve(table, in_scope=False, marks=frozenset({"X2"}), profile=PROFILE) is None
