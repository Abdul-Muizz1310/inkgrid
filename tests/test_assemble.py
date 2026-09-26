from collections.abc import Sequence

import pytest

from inkgrid.core.assemble import assemble
from inkgrid.core.furniture import FoundFurniture
from inkgrid.core.lines import Line, group_lines
from inkgrid.core.pipeline import build_document
from inkgrid.core.prose import ProtoBlock
from inkgrid.core.text import block_text
from inkgrid.errors import InvariantError
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.document import Definition, Document
from inkgrid.model.findings import FindingCode
from inkgrid.model.page import PageModel, Reading
from layout_builder import P, place, text_line
from model_builders import mk_page, mk_reading

PROFILE = Profile()
LEXICON = Lexicon()


def reading_of(specs: Sequence[Sequence[P]]) -> Reading:
    pages: list[PageModel] = []
    next_id = 0
    for number, ps in enumerate(specs, 1):
        words = place(ps, page=number, first_id=next_id)
        next_id += len(words)
        pages.append(mk_page(number=number, words=words, text_layer="full" if words else "none"))
    return mk_reading(tuple(pages))


def document(specs: Sequence[Sequence[P]]) -> Document:
    return build_document(reading_of(specs), lexicon=LEXICON, profile=PROFILE, lattice="combined")


def text_of(texts: Sequence[str]) -> tuple[str, tuple[tuple[int, int], ...]]:
    ps: list[P] = []
    for i, text in enumerate(texts):
        ps += text_line(text.split(), x=72, y=100 + 12 * i)
    return block_text(group_lines(place(ps), PROFILE))


def test_AS1_a_line_final_hyphen_joins_a_lower_case_continuation() -> None:
    assert text_of(["execu-", "tions are billed"]) == ("executions are billed", ((0, 1),))


def test_AS2_an_upper_case_continuation_keeps_the_hyphen() -> None:
    assert text_of(["pre-", "Market"]) == ("pre- Market", ())


def test_AS3_a_lone_dash_is_not_a_hyphen() -> None:
    assert text_of(["rate -", "applies"]) == ("rate - applies", ())


def test_AS4_superscript_words_are_markers() -> None:
    doc = document([[P("$0.40", 72, 100), P("2", 97, 96.5, superscript=True)]])
    assert doc.blocks[0].markers == ("2",)


def framed(n: int, pages: int) -> list[P]:
    body = text_line(["The", "tier", "x" * n, "charges", "members", "daily."], x=72, y=300)
    return [
        *text_line(["Acme", "Fee", "Guide"], x=72, y=40),
        *body,
        *text_line(["Page", str(n), "of", str(pages)], x=72, y=750),
    ]


def test_AS5_furniture_frames_the_page_content() -> None:
    doc = document([framed(n, 2) for n in (1, 2)])
    kinds = [(b.kind, b.regions[0].page) for b in doc.blocks]
    assert kinds == [
        ("furniture", 1),
        ("paragraph", 1),
        ("furniture", 1),
        ("furniture", 2),
        ("paragraph", 2),
        ("furniture", 2),
    ]
    roles = [b.role for b in doc.blocks if b.kind == "furniture"]
    assert roles == ["header", "footer", "header", "footer"]


@pytest.mark.parametrize(("pages", "expected"), [(9, True), (8, False)])
def test_AS6_a_long_document_without_furniture_is_flagged(pages: int, expected: bool) -> None:
    doc = document([text_line(["tier", "x" * n], x=72, y=300) for n in range(1, pages + 1)])
    codes = [f.code for f in doc.findings]
    assert (FindingCode.NO_FURNITURE_LONG_DOCUMENT in codes) is expected


def test_AS7_a_word_in_two_blocks_is_an_invariant_error() -> None:
    reading = reading_of([text_line(["one", "two"], x=72, y=100)])
    a, b = reading.pages[0].words
    blocks = (
        ProtoBlock("paragraph", (Line((a,)),), 10.0),
        ProtoBlock("paragraph", (Line((a, b)),), 10.0),
    )
    empty = FoundFurniture((), frozenset())
    with pytest.raises(InvariantError, match="word 0 is in blocks"):
        assemble(reading, (blocks,), empty, lexicon=LEXICON, profile=PROFILE, lattice="combined")


def test_DF14_a_definition_renders_as_term_and_body() -> None:
    reading = reading_of(
        [text_line(["\u201cABBO\u201d", "means", "the", "best", "bid"], x=72, y=100)]
    )
    term, *body = reading.pages[0].words
    block = ProtoBlock(
        "definition", (Line((term,)), Line(tuple(body))), 10.0, term=(Line((term,)),)
    )
    empty = FoundFurniture((), frozenset())
    doc = assemble(
        reading, ((block,),), empty, lexicon=LEXICON, profile=PROFILE, lattice="combined"
    )
    (d,) = doc.blocks
    assert isinstance(d, Definition)
    assert (d.term, d.body, d.text) == (
        "\u201cABBO\u201d",
        "means the best bid",
        "\u201cABBO\u201d means the best bid",
    )
    assert doc.to_markdown() == "**\u201cABBO\u201d** means the best bid\n"


def test_DF14_a_definition_block_holds_its_term_first_and_a_body() -> None:
    a, b = (Line((w,)) for w in place(text_line(["Term", "body"], x=72, y=100)))
    with pytest.raises(ValueError, match="opening lines"):
        ProtoBlock("definition", (b, a), 10.0, term=(a,))
    with pytest.raises(ValueError, match="body"):
        ProtoBlock("definition", (a,), 10.0, term=(a,))
    with pytest.raises(ValueError, match="has no term"):
        ProtoBlock("paragraph", (a, b), 10.0, term=(a,))


def test_AS8_the_ledger_counts_furniture_characters() -> None:
    doc = document([framed(n, 5) for n in range(1, 6)])
    furniture = sum(len(w.text) for w in doc.words if w.bbox.y0 in {40.0, 750.0})
    assert doc.ledger.furniture_chars == furniture
    assert doc.ledger.content_chars == sum(len(w.text) for w in doc.words) - furniture


def test_AS9_heading_levels_rank_distinct_sizes() -> None:
    ps: list[P] = []
    y = 60.0
    for size, bold, title in [
        (18, False, "Alpha"),
        (14, False, "Beta"),
        (14, False, "Gamma"),
        (10, True, "Delta"),
    ]:
        ps += text_line([title, "part"], x=72, y=y, size=size, bold=bold)
        ps += text_line(["body", "text", "under", "the", "heading", "runs", "long"], x=72, y=y + 30)
        y += 60
    doc = document([ps])
    levels = [b.level for b in doc.blocks if b.kind == "heading"]
    assert levels == [1, 2, 2, 3]


def test_AS10_repeated_headings_get_twin_keys() -> None:
    ps = [
        *text_line(["Fees"], x=72, y=60, size=14, bold=True),
        *text_line(["body", "one", "is", "here"], x=72, y=90),
        *text_line(["Fees"], x=72, y=130, size=14, bold=True),
        *text_line(["body", "two", "is", "here"], x=72, y=160),
    ]
    doc = document([ps])
    first, second = (b.key for b in doc.blocks if b.kind == "heading")
    assert second == f"{first}:2"


def test_AS11_list_items_and_footnotes_carry_their_labels() -> None:
    ps = [
        *text_line(["\u2022", "first", "item", "here"], x=72, y=100),
        *text_line(["a)", "second", "item", "here"], x=72, y=112),
        *text_line(["Closing", "body", "text", "for", "the", "page"], x=72, y=140),
        *text_line(["runs", "over", "a", "second", "line"], x=72, y=152),
        *text_line(["and", "a", "third", "one"], x=72, y=164),
        *text_line(["(4)", "Applies", "to", "members"], x=72, y=190, size=7),
    ]
    doc = document([ps])
    labels = [(b.kind, getattr(b, "label", None)) for b in doc.blocks]
    assert labels == [
        ("list_item", "\u2022"),
        ("list_item", "a)"),
        ("paragraph", None),
        ("footnote", "4"),
    ]


def test_PB16_one_line_clauses_break_at_the_documents_line_gap() -> None:
    prose = [
        *text_line(["The", "tier", "one", "fee"], x=72, y=100),
        *text_line(["applies", "to", "members"], x=72, y=112),
        *text_line(["and", "is", "billed", "monthly."], x=72, y=124),
        *text_line(["A", "second", "paragraph", "starts"], x=72, y=150),
        *text_line(["on", "this", "line", "here."], x=72, y=162),
    ]
    clauses = [
        text_line(["1", "The", "fee", f"clause{'x' * n}", "applies."], x=72, y=100 + 18 * n)
        for n in range(4)
    ]
    doc = document([prose, [p for clause in clauses for p in clause]])
    on_page_2 = [b.text for b in doc.blocks if b.regions[0].page == 2]
    assert len(on_page_2) == 4
