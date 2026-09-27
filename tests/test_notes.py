from collections.abc import Sequence

from inkgrid.core.layout import Region
from inkgrid.core.lines import group_lines
from inkgrid.core.notes import as_note, note_grid
from inkgrid.core.prose import ProtoBlock, line_gaps, page_blocks
from inkgrid.core.tables.lattice import lattice_tables
from inkgrid.core.tables.proto import ProtoTable
from inkgrid.core.text import block_text
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.geometry import Rect
from inkgrid.model.page import Word
from layout_builder import P, place, text_line
from model_builders import mk_page

PROFILE = Profile()
LEXICON = Lexicon(bullets=("*",), id="test/1")
BODY = 10.0
PROSE = ["applies", "to", "every", "trade", "on", "the", "book"]


def only(ps: Sequence[P]) -> ProtoBlock:
    region = Region("prose", group_lines(place(ps), PROFILE))
    (block,) = page_blocks((region,), LEXICON, PROFILE, BODY, line_gaps((region,)))
    return block


def opener(
    label: str,
    *,
    size: float,
    text_size: float = 10.0,
    words: Sequence[str] = PROSE,
    bold: bool = False,
    superscript: bool = False,
) -> list[P]:
    """A line opening with `label` at `size`, then `words` at `text_size`, on one line."""
    lift = (text_size - size) / 2  # the label's box sits inside the text's: one line
    width = 0.55 * size * len(label)
    ps = [P(label, 72, 100 + lift, size=size, bold=bold, superscript=superscript)]
    ps += text_line(list(words), x=72 + width + 2, y=100, size=text_size, bold=bold)
    return ps


def kind_and_label(block: ProtoBlock, called: frozenset[str]) -> tuple[str, str | None]:
    got = as_note(block, called=called, body=BODY)
    return got.kind, got.label


def test_OP1_a_smaller_called_number_opens_a_note() -> None:
    block = only(opener("14", size=7))
    assert kind_and_label(block, frozenset({"14"})) == ("footnote", "14")


def test_OP2_an_uncalled_opener_is_no_note() -> None:
    block = only(opener("14", size=7))
    assert kind_and_label(block, frozenset({"3"})) == (block.kind, block.label)


def test_OP3_a_bare_number_at_text_size_opens_a_called_note() -> None:
    assert kind_and_label(only(opener("2", size=10)), frozenset({"2"})) == ("footnote", "2")


def test_OP4_marks_at_text_size_open_called_notes() -> None:
    assert kind_and_label(only(opener("^", size=10)), frozenset({"^"})) == ("footnote", "^")
    bulleted = only(opener("*", size=10))
    assert bulleted.kind == "list_item"  # `*` is also a bullet
    assert kind_and_label(bulleted, frozenset({"*"})) == ("footnote", "*")


def test_OP4_geometric_marks_open_called_notes() -> None:
    # MIAX calls with a black medium square and a black lozenge, both Unicode category Sm
    for mark in ("\u25fc", "\u29eb", "\u25ca"):
        assert kind_and_label(only(opener(mark, size=10)), frozenset({mark})) == ("footnote", mark)


def test_OP5_an_enumerator_at_text_size_stays_a_list_item() -> None:
    block = only(opener("1)", size=10))
    assert block.kind == "list_item"
    assert kind_and_label(block, frozenset({"1"})) == ("list_item", "1)")


def test_OP6_a_smaller_enumerator_opens_a_note() -> None:
    assert kind_and_label(only(opener("1)", size=7)), frozenset({"1"})) == ("footnote", "1")


def test_OP7_a_flagged_superscript_opener_is_a_call_not_a_note() -> None:
    block = only(opener("3", size=7, superscript=True))
    assert kind_and_label(block, frozenset({"3"}))[0] != "footnote"


def test_OP8_a_heading_number_is_no_note() -> None:
    words = ["Transaction", "Fees", "Apply"]
    block = only(opener("1", size=12, text_size=14, words=words, bold=True))
    assert kind_and_label(block, frozenset({"1"}))[0] != "footnote"


def test_OP9_an_opener_needs_three_words_after_it() -> None:
    block = only(opener("7", size=7, words=["Reserved", "item"]))
    assert kind_and_label(block, frozenset({"7"}))[0] != "footnote"


def test_OP10_a_letter_opens_a_note_only_when_smaller() -> None:
    assert kind_and_label(only(opener("a", size=7)), frozenset({"a"})) == ("footnote", "a")
    same = only(opener("a", size=10))
    assert kind_and_label(same, frozenset({"a"}))[0] != "footnote"


# --- Titled note grids (spec 09 section 1.2) ----------------------------------------------------


def grid(rows: Sequence[Sequence[str]], *, cols: int = 3) -> ProtoTable:
    """A ruled grid, 20 pt rows; the first column 60 pt wide, the rest 200 pt each.

    Each row lists its cells left to right; a cell given as `text>` spans to the last column.
    """
    xs = [72.0, 132.0] + [132.0 + 200.0 * (i + 1) for i in range(cols - 1)]
    rects: list[Rect] = []
    ps: list[P] = []
    for r, row in enumerate(rows):
        y = 200.0 + 20 * r
        c = 0
        for text in row:
            wide = text.endswith(">")
            end = cols if wide else c + 1
            rects.append(Rect(xs[c], y, xs[end], y + 20))
            ps += text_line(text.rstrip(">").split(), x=xs[c] + 4, y=y + 6, size=9)
            c = end
        while c < cols:  # empty cells to the right
            rects.append(Rect(xs[c], y, xs[c + 1], y + 20))
            c += 1
    words: tuple[Word, ...] = place(ps)
    stage = lattice_tables(mk_page(words=words), [rects], words, PROFILE, frame=0, read=True)
    (table,) = stage.tables
    return table


def shown(blocks: Sequence[ProtoBlock]) -> list[tuple[str, str]]:
    return [(b.kind, b.label or block_text(b.lines)[0]) for b in blocks]


NOTES = [
    ["Footnotes:"],
    ["Footnote Number", "Description>"],
    ["1", "Per contract side, including FLEX.>"],
    ["2", "Reserved.>"],
]


def test_NG1_a_titled_note_grid_dissolves_into_headings_and_notes() -> None:
    blocks = note_grid(grid(NOTES))
    assert blocks is not None
    assert shown(blocks) == [
        ("heading", "Footnotes:"),
        ("heading", "Footnote Number Description"),
        ("footnote", "1"),
        ("footnote", "2"),
    ]


def test_NG2_a_grid_without_a_notes_word_stays_a_table() -> None:
    rows = [["Fees:"], ["Code", "Description>"], *NOTES[2:]]
    assert note_grid(grid(rows)) is None


def test_NG3_values_beside_labels_keep_the_table() -> None:
    rows = [*NOTES[:2], ["1", "1.20%>"], ["2", "0.95%>"]]
    assert note_grid(grid(rows)) is None


def test_NG4_three_filled_cells_keep_the_table() -> None:
    rows = [*NOTES[:2], ["1", "Per contract side", "extra words"], ["2", "Reserved.", "more"]]
    assert note_grid(grid(rows)) is None
