from collections.abc import Mapping, Sequence
from itertools import pairwise

from hypothesis import given
from hypothesis import strategies as st

from doc_builder import B, C, W, build
from ink_builder import edited, ink_of, stray
from inkgrid.model.document import Document, Link, LinkEnd, Table
from inkgrid.model.geometry import Rect, unturn_rect
from inkgrid.model.verification import DefectCode
from inkgrid.verify.checks import (
    CellIndex,
    Home,
    TableResult,
    Words,
    homes_of,
    reading_sequence,
    table_checks,
    value_checks,
)
from inkgrid.verify.ink import InkChar, InkPage, InkRule
from inkgrid.verify.ownership import own_page

X0, Y0, COL, ROW = 100.0, 200.0, 60.0, 20.0


def bands(n: int, start: float, size: float) -> list[tuple[float, float]]:
    return [(start + size * i, start + size * (i + 1)) for i in range(n)]


def grid_table(
    rows: Sequence[Sequence[str]],
    *,
    at: Mapping[tuple[int, int], tuple[float, float]] | None = None,
    row_bands: list[tuple[float, float]] | None = None,
) -> B:
    """A table of one word per non-empty cell, each word 5 pt into its cell unless `at` moves it."""
    words: list[W] = []
    cells: list[C] = []
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            ids = []
            for part in text.split():
                x, y = (at or {}).get((r, c), (X0 + COL * c + 5, Y0 + ROW * r + 5))
                x += 5 * sum(len(p) + 1 for p in text.split()[: len(ids)])
                ids.append(len(words))
                words.append(W(part, x, y))
            cells.append(C(r, c, ids))
    return B(
        "table",
        words,
        row_bands=row_bands or bands(len(rows), Y0, ROW),
        col_bands=bands(len(rows[0]), X0, COL),
        cells=cells,
    )


def check(doc: Document, ink: InkPage | None = None, *, table: str = "b1") -> TableResult:
    (block,) = [t for t in doc.tables() if t.id == table]
    number = block.regions[0].page
    ink = ink or ink_of(doc, number)
    words = [w for w in doc.words if w.page == number]
    owner = own_page(ink, words, clipped_chars=0, invisible_chars=0).owner
    return table_checks(block, ink, owner, Words.of(doc))


def respaced(ink: InkPage, first: int, edges: Sequence[float]) -> InkPage:
    """The ink with characters `first`, `first + 1`, ... redrawn between consecutive `edges` (x)."""

    def change(chars: list[InkChar]) -> list[InkChar]:
        out = list(chars)
        for k, (x0, x1) in enumerate(pairwise(edges)):
            old = out[first + k]
            out[first + k] = InkChar(0, old.char, Rect(x0, old.box.y0, x1, old.box.y1), old.kind)
        return out

    return edited(ink, change)


def codes(result: TableResult) -> list[tuple[str, tuple[int, int] | None]]:
    return [(d.code.value, d.cell) for d in (*result.defects, *result.advisories)]


RATES = [["Fee", "Rate"], ["Equity", "0.30"]]


@given(
    st.lists(
        st.lists(
            st.text(alphabet="abcXYZ019.,$%", min_size=1, max_size=10), min_size=2, max_size=4
        ),
        min_size=1,
        max_size=4,
    ).filter(lambda rows: len({len(r) for r in rows}) == 1)
)
def test_TB1_ink_made_from_a_tables_words_passes_every_check(rows: list[list[str]]) -> None:
    result = check(build([grid_table(rows)]))
    assert codes(result) == []
    assert result.overflow == 0


def test_TB2_ink_in_a_gap_between_bands_is_an_orphan() -> None:
    doc = build([grid_table(RATES, row_bands=[(200, 220), (225, 245)])])
    ink = edited(ink_of(doc), lambda cs: [*cs, *stray("x", 110, 217.5)])  # centre y 222.5
    result = check(doc, ink)
    assert codes(result) == [("orphan", None)]
    assert result.defects[0].text == "x"


def test_TB3_a_point_in_two_overlapping_rectangles_has_two_homes() -> None:
    index = CellIndex([Rect(0, 0, 20, 20), Rect(10, 0, 30, 20), Rect(40, 0, 60, 20)])
    assert index.homes(15, 10) == [0, 1]
    assert index.homes(5, 10) == [0]
    assert index.homes(35, 10) == []
    assert index.homes(20, 10) == [1]  # half-open: x1 of the first is outside it


def test_TB4_a_word_whose_ink_lies_mostly_in_the_next_cell_is_misplaced() -> None:
    # `Rate`'s box (150-170) centres on 160, inside its cell (160-220), but three of its
    # glyphs are drawn left of 160: the page puts most of the word in the cell before.
    doc = build([grid_table(RATES, at={(0, 1): (150.0, Y0 + 5)})])
    ink = respaced(ink_of(doc), 4, [150, 155, 158, 159.5, 170])
    result = check(doc, ink)
    assert codes(result) == [("text", (0, 1))]
    assert "'Rate' has 1 of its 4 characters in the cell" in result.defects[0].detail


def test_TB5_a_word_overflowing_its_cell_with_most_of_it_inside_stands() -> None:
    doc = build([grid_table([["Charge", ""]], at={(0, 0): (140.0, Y0 + 5)})])
    result = check(doc)
    assert codes(result) == []
    assert result.overflow == 2


def test_TB6_a_word_split_exactly_in_half_is_misplaced() -> None:
    doc = build([grid_table([["", "Charge"]], at={(0, 1): (145.0, Y0 + 5)})])  # centre 160
    assert codes(check(doc)) == [("text", (0, 1))]


def test_TB7_another_blocks_ink_in_a_cell_is_foreign() -> None:
    doc = build([grid_table(RATES), B("paragraph", [W("note", 190, 225)])])
    result = check(doc)
    assert codes(result) == [("text", (1, 1))]
    assert "note" in result.defects[0].detail


def continued(extra: list[B]) -> Document:
    """A two-page table whose second part carries its header row, then `extra` blocks on page 2."""
    parent = grid_table(RATES)
    parent.header_rows = 1
    child = B(
        "table",
        [W("Equity", 105, 225, page=2), W("0.30", 165, 225, page=2)],
        row_bands=bands(2, Y0, ROW),
        col_bands=bands(2, X0, COL),
        cells=[
            C(0, 0, carried_text="Fee", source=((0, 0),)),
            C(0, 1, carried_text="Rate", source=((0, 1),)),
            C(1, 0, [0]),
            C(1, 1, [1]),
        ],
        header_rows=1,
    )
    link = Link.model_validate(
        {"kind": "continuation", "from": LinkEnd(block="b2"), "to": "b1", "status": "resolved"}
    )
    return build([parent, child, *extra], pages=2, links=[link])


def test_TB7_foreign_ink_in_a_carried_cells_rectangle_is_a_defect() -> None:
    assert (
        codes(check(continued([B("paragraph", [W("elsewhere", 300, 400, page=2)])]), table="b2"))
        == []
    )
    doc = continued([B("paragraph", [W("Continued", 105, 205, page=2)])])
    assert codes(check(doc, table="b2")) == [("text", (0, 0))]


def test_TB8_a_cell_whose_ink_reads_in_another_order_is_advisory() -> None:
    table = B(
        "table",
        [W("Maker", 105, 215), W("BBO", 105, 203)],
        row_bands=[(200, 230)],
        col_bands=[(100, 160)],
        cells=[C(0, 0, [0, 1])],
    )
    result = check(build([table]))
    assert codes(result) == [("order", (0, 0))]
    assert result.defects == ()


def two_words() -> Document:
    table = B(
        "table",
        [W("ab", 105, 205), W("cd", 140, 205), W("ef", 105, 225)],
        row_bands=[(200, 240)],
        col_bands=[(100, 160)],
        cells=[C(0, 0, [0, 1, 2])],
    )
    return build([table])


def with_rules(doc: Document, *rules: InkRule) -> InkPage:
    ink = ink_of(doc)
    return InkPage(ink.number, ink.width, ink.height, chars=ink.chars, rules=rules)


def test_TB9_a_vertical_rule_through_a_cell_between_its_ink_is_vrule() -> None:
    doc = two_words()
    assert codes(check(doc, with_rules(doc, InkRule("v", 130, 199, 241)))) == [("vrule", (0, 0))]


def test_TB10_a_rule_that_does_not_span_the_cell_or_hugs_its_edge_cuts_nothing() -> None:
    doc = two_words()
    assert codes(check(doc, with_rules(doc, InkRule("v", 130, 200, 220)))) == []
    assert codes(check(doc, with_rules(doc, InkRule("v", 100.8, 199, 241)))) == []


def test_TB11_a_horizontal_rule_across_a_cell_between_lines_is_hrule() -> None:
    doc = two_words()
    assert codes(check(doc, with_rules(doc, InkRule("h", 220, 99, 161)))) == [("hrule", (0, 0))]
    underline = InkRule("h", 216, 105, 115)
    assert codes(check(doc, with_rules(doc, underline))) == []


def turned(frame_x0: float, edges: Sequence[float] | None = None) -> tuple[Document, InkPage]:
    """A frame-90 table of two cells side by side in the frame, `Charge` bound to the cell holding
    its box's centre, and its ink: even, or with its glyphs between frame `edges` (x)."""
    frame_box = Rect(frame_x0, Y0 + 5, frame_x0 + 30, Y0 + 15)
    page_box = unturn_rect(frame_box, 90, 612.0, 792.0)
    cell = 0 if frame_box.center[0] < X0 + COL else 1
    table = B(
        "table",
        [W("Charge", page_box.x0, page_box.y0, rect=page_box)],
        row_bands=[(Y0, Y0 + ROW)],
        col_bands=bands(2, X0, COL),
        cells=[C(0, 0, [0] if cell == 0 else []), C(0, 1, [0] if cell == 1 else [])],
        frame=90,
    )
    doc = build([table])
    if edges is None:
        return doc, ink_of(doc)
    glyphs = [
        InkChar(0, ch, unturn_rect(Rect(x0, Y0 + 5, x1, Y0 + 15), 90, 612.0, 792.0), "ink")
        for ch, (x0, x1) in zip("Charge", pairwise(edges), strict=True)
    ]
    return doc, edited(ink_of(doc), lambda cs: [*glyphs, *cs[6:]])


def test_TB12_checks_run_in_the_tables_frame() -> None:
    doc, ink = turned(165.0)
    assert codes(check(doc, ink)) == []
    doc, ink = turned(140.0, [140, 158, 161, 164, 167, 169, 170])  # centre 155, 1 glyph in cell 0
    assert codes(check(doc, ink)) == [("text", (0, 0))]


def test_TB12_a_cell_defect_is_boxed_in_the_unrotated_frame() -> None:
    doc, ink = turned(140.0, [140, 158, 161, 164, 167, 169, 170])
    (defect,) = check(doc, ink).defects
    (table,) = doc.tables()
    rect = table.grid.cell_rect(table.grid.cells[0])
    assert defect.bbox == unturn_rect(rect, 90, 612.0, 792.0)


def test_reading_sequence_clusters_lines_by_vertical_overlap() -> None:
    chars = [
        InkChar(0, "b", Rect(10, 0, 15, 10), "ink"),
        InkChar(1, ",", Rect(15, 4, 17, 12), "ink"),  # overlaps the line by 6 of its 8
        InkChar(2, "a", Rect(0, 1, 5, 11), "ink"),
        InkChar(3, "c", Rect(0, 20, 5, 30), "ink"),
    ]
    assert "".join(c.char for c in reading_sequence(chars, 0, 612, 792)) == "ab,c"


def values(doc: Document, ink: InkPage | None = None) -> list[str]:
    ink = ink or ink_of(doc)
    owner = own_page(ink, doc.words, clipped_chars=0, invisible_chars=0).owner
    return [d.text for d in value_checks(ink, owner, Words.of(doc)) if d.code is DefectCode.VALUE]


def glued(doc: Document, first: int) -> InkPage:
    """The ink with the generated space after word `first` removed: two words, one token."""
    ink = ink_of(doc)
    spaces = [ch.index for ch in ink.chars if ch.kind == "generated"]
    return edited(ink, lambda cs: [c for c in cs if c.index != spaces[first]])


def test_VF1_a_value_token_bound_to_two_cells() -> None:
    doc = build([grid_table([["1.20", "%"]])])
    assert values(doc) == []
    assert values(doc, glued(doc, 0)) == ["1.20%"]


def test_VF2_a_value_token_bound_to_two_blocks() -> None:
    doc = build([B("paragraph", [W("2", 100, 100)]), B("paragraph", [W("7", 105, 100)])])
    assert values(doc, glued(doc, 0)) == ["27"]


def test_VF3_a_token_without_a_digit_or_with_unowned_ink_is_not_checked() -> None:
    doc = build([B("paragraph", [W("Fees", 100, 100)]), B("paragraph", [W("Apply", 125, 100)])])
    assert values(doc, glued(doc, 0)) == []
    doc = build([B("paragraph", [W("1", 100, 100)])])
    ink = edited(ink_of(doc), lambda cs: [cs[0], *stray("2", 105, 100), *cs[1:]])
    assert values(doc, ink) == []


def test_VF4_tokens_end_at_a_generated_space() -> None:
    doc = build([grid_table([["12", "34"]])])
    assert values(doc) == []


def test_homes_name_each_words_block_and_cell() -> None:
    doc = build([grid_table(RATES), B("paragraph", [W("note", 300, 400)])])
    homes: Mapping[int, Home] = homes_of(doc)
    assert homes[0] == ("b1", (0, 0))
    assert homes[4] == ("b2", None)
    assert isinstance(doc.blocks[0], Table)
