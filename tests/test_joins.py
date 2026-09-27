from collections.abc import Sequence
from dataclasses import replace

import pytest

from inkgrid.core.assemble import assemble
from inkgrid.core.furniture import FoundFurniture
from inkgrid.core.joins import join_tables
from inkgrid.core.lines import group_lines
from inkgrid.core.prose import ProtoBlock
from inkgrid.core.tables.lattice import lattice_tables
from inkgrid.core.tables.proto import ProtoCell, ProtoTable
from inkgrid.core.text import block_text
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.document import Document
from inkgrid.model.geometry import Rect
from layout_builder import P, place, text_line
from model_builders import mk_page, mk_reading

PROFILE = Profile()
XS = (72.0, 172.0, 272.0)


def table(
    rows: Sequence[Sequence[str]],
    *,
    page: int,
    y0: float,
    xs: Sequence[float] = XS,
    first_id: int | None = None,
) -> ProtoTable:
    """A ruled grid of 20 pt rows at `y0` on `page`; an empty string is an empty cell."""
    rects: list[Rect] = []
    ps: list[P] = []
    for r, row in enumerate(rows):
        y = y0 + 20 * r
        for c, text in enumerate(row):
            rects.append(Rect(xs[c], y, xs[c + 1], y + 20))
            if text:
                ps += text_line(text.split(), x=xs[c] + 4, y=y + 5, size=9)
    start = 1000 * page if first_id is None else first_id
    words = place(ps, page=page, first_id=start)
    stage = lattice_tables(
        mk_page(number=page, words=words), [rects], words, PROFILE, frame=0, read=True
    )
    (proto,) = stage.tables
    return proto


def block(kind: str, text: str, *, page: int, y: float, first_id: int | None = None) -> ProtoBlock:
    start = 1000 * page + 500 if first_id is None else first_id
    words = place(text_line(text.split(), x=72, y=y, size=9), page=page, first_id=start)
    lines = group_lines(words, PROFILE)
    return ProtoBlock(kind, lines, lines[0].size, label="1" if kind == "footnote" else None)  # type: ignore[arg-type]


HEAD = ["Fee", "Rate"]
PARENT = [HEAD, ["Band1", "$0.50"], ["Band2", "$0.60"]]
CHILD = [["Band3", "$0.70"], ["Band4", "$0.80"]]


def joined(
    pages: Sequence[Sequence[ProtoBlock]], tables: Sequence[Sequence[ProtoTable]]
) -> list[tuple[ProtoTable, ...]]:
    return join_tables(pages, tables)


def two_pages(
    *,
    before: Sequence[ProtoBlock] = (),
    after: Sequence[ProtoBlock] = (),
    child: ProtoTable | None = None,
) -> list[tuple[ProtoTable, ...]]:
    parent = table(PARENT, page=1, y0=600)
    second = child if child is not None else table(CHILD, page=2, y0=80)
    return joined([tuple(before), tuple(after)], [(parent,), (second,)])


def carried(t: ProtoTable) -> list[tuple[int, int, str, tuple[tuple[int, int], ...]]]:
    return [(c.cell.row, c.cell.col, c.carried, c.source) for c in t.cells if c.source]


def test_TC1_a_headerless_table_carries_its_parents_header() -> None:
    parent, child = (t for page in two_pages() for t in page)
    assert child.continues is parent
    assert child.header_rows == 1
    assert carried(child) == [(0, 0, "Fee", ((0, 0),)), (0, 1, "Rate", ((0, 1),))]
    body = [(c.cell.row, block_text(c.lines)[0]) for c in child.cells if not c.source]
    assert body == [(1, "Band3"), (1, "$0.70"), (2, "Band4"), (2, "$0.80")]
    edges = child.shape.row_edges
    assert edges[1] == 80.0  # the carried band sits directly above the first body row
    assert 0 < edges[0] < 80.0


def test_TC2_a_paragraph_after_the_parent_breaks_the_flow() -> None:
    tables = two_pages(before=[block("paragraph", "More text follows here", page=1, y=700)])
    assert tables[1][0].continues is None


def test_TC3_a_footnote_under_the_parent_does_not() -> None:
    tables = two_pages(before=[block("footnote", "1 Applies to all bands", page=1, y=700)])
    assert tables[1][0].continues is tables[0][0]


def test_TC4_a_heading_above_the_child_breaks_the_flow() -> None:
    tables = two_pages(after=[block("heading", "Other fees", page=2, y=50)])
    assert tables[1][0].continues is None


def test_TC5_a_different_column_count_is_no_continuation() -> None:
    wide = table([["Band3", "$0.70", "x"], ["Band4", "$0.80", "y"]], page=2, y0=80, xs=(*XS, 372.0))
    assert two_pages(child=wide)[1][0].continues is None


def test_TC6_columns_that_do_not_align_are_no_continuation() -> None:
    shifted = table(CHILD, page=2, y0=80, xs=tuple(x + 20 for x in XS))
    assert two_pages(child=shifted)[1][0].continues is None


def test_TC7_a_reprinted_header_continues_without_carrying() -> None:
    reprint = table([HEAD, *CHILD], page=2, y0=80)
    parent, child = (t for page in two_pages(child=reprint) for t in page)
    assert child.continues is parent
    assert carried(child) == []


def test_TC8_a_different_header_is_another_table() -> None:
    other = table([["Band", "Charge"], *CHILD], page=2, y0=80)
    assert two_pages(child=other)[1][0].continues is None


def test_TC9_a_chain_carries_the_first_parts_header() -> None:
    first = table(PARENT, page=1, y0=600)
    second = table(CHILD, page=2, y0=80)
    third = table([["Band5", "$0.90"], ["Band6", "$1.00"]], page=3, y0=80)
    out = joined([(), (), ()], [(first,), (second,), (third,)])
    (a,), (b,), (c,) = out
    assert b.continues is a
    assert c.continues is b
    assert carried(c) == [(0, 0, "Fee", ((0, 0),)), (0, 1, "Rate", ((0, 1),))]


def test_TC10_an_empty_header_cell_is_carried_as_an_empty_cell() -> None:
    parent = table([["Charges", ""], HEAD, ["Band1", "$0.50"], ["Band2", "$0.60"]], page=1, y0=580)
    assert parent.header_rows == 2
    (_,), (child,) = joined([(), ()], [(parent,), (table(CHILD, page=2, y0=80),)])
    assert child.header_rows == 2
    assert carried(child) == [
        (0, 0, "Charges", ((0, 0),)),
        (1, 0, "Fee", ((1, 0),)),
        (1, 1, "Rate", ((1, 1),)),
    ]
    empty = [c for c in child.cells if c.cell.row == 0 and c.cell.col == 1]
    assert empty == [ProtoCell(empty[0].cell, ())]


# --- Through assembly --------------------------------------------------------------------------


def assembled(
    tables: Sequence[Sequence[ProtoTable]], blocks: Sequence[Sequence[ProtoBlock]] | None = None
) -> Document:
    """Assemble pages of tables and blocks whose words carry dense ids in page order."""
    prose = [tuple(p) for p in blocks] if blocks is not None else [() for _ in tables]
    pages = []
    for number, (page_tables, page_blocks) in enumerate(zip(tables, prose, strict=True), 1):
        own = [w for t in page_tables for w in t.words]
        own += [w for b in page_blocks for line in b.lines for w in line.words]
        own.sort(key=lambda w: w.id)
        layer = "full" if own else "none"
        pages.append(mk_page(number=number, words=tuple(own), text_layer=layer))
    reading = mk_reading(tuple(pages))
    empty = FoundFurniture((), frozenset())
    return assemble(
        reading, prose, empty, lexicon=Lexicon(), profile=PROFILE, lattice="combined",
        tables=[tuple(p) for p in tables],
    )  # fmt: skip


def test_TC1_a_joined_pair_assembles_into_a_linked_valid_document() -> None:
    parent = table(PARENT, page=1, y0=600, first_id=0)
    child = table(CHILD, page=2, y0=80, first_id=len(parent.words))
    doc = assembled(join_tables([(), ()], [(parent,), (child,)]))
    (link,) = doc.links
    assert (link.kind, link.from_.block, link.to, link.status) == (
        "continuation",
        "b2",
        "b1",
        "resolved",
    )
    joined = doc.tables()[1]
    assert [c.text for c in joined.grid.cells if c.carried] == ["Fee", "Rate"]
    assert joined.grid.header_rows == 1
    assert joined.text == "Band3 $0.70\nBand4 $0.80"


def test_FR5_calls_in_a_continued_table_resolve_from_its_last_page() -> None:
    first = table([HEAD, ["Band1", "$0.50"], ["Band2", "$0.60"]], page=1, y0=600, first_id=0)
    # the fee in row 1 carries a raised `1`
    raised = place([P("1", 214, 622.5, size=5, superscript=True)], page=1, first_id=6)
    cells = tuple(
        ProtoCell(c.cell, group_lines((*c.words, *raised), PROFILE))
        if (c.cell.row, c.cell.col) == (1, 1)
        else c
        for c in first.cells
    )
    first = replace(first, cells=cells)
    second = table(CHILD, page=2, y0=80, first_id=7)
    third = table([["Band5", "$0.90"], ["Band6", "$1.00"]], page=3, y0=80, first_id=11)
    note3 = block("footnote", "1 Applies to every band listed", page=3, y=200, first_id=15)
    note7 = block("footnote", "1 Applies to another table", page=7, y=200, first_id=21)
    prose: list[tuple[ProtoBlock, ...]] = [(), (), (note3,), (), (), (), (note7,)]
    tables = join_tables(prose, [(first,), (second,), (third,), (), (), (), ()])
    doc = assembled(tables, prose)
    calls = [k for k in doc.links if k.kind == "footnote_call"]
    # without the chain, page 1's call looks at pages 1-2 only, and page 3's note is too far
    assert [(k.label, k.status, k.to) for k in calls] == [("1", "resolved", "b4")]


def test_TC_a_carried_cell_holds_a_text_and_a_source_and_no_words() -> None:
    parent = table(PARENT, page=1, y0=600)
    head = parent.cells[0]
    with pytest.raises(ValueError, match="both a text and a source"):
        ProtoCell(head.cell, (), carried="Fee")
    with pytest.raises(ValueError, match="both a text and a source"):
        ProtoCell(head.cell, (), source=((0, 0),))
    with pytest.raises(ValueError, match="owns no words"):
        ProtoCell(head.cell, head.lines, carried="Fee", source=((0, 0),))
