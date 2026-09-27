import inkgrid
import pdf_factory
from inkgrid.model.document import Footnote
from inkgrid.model.findings import FindingCode
from lattice_builder import read_with_tables


def test_TC11_a_continued_table_carries_its_header_through_the_pipeline() -> None:
    doc = read_with_tables(pdf_factory.continued_table())
    parent, child = doc.tables()
    assert [c.text for c in child.grid.cells if c.carried] == ["Fee", "Rate"]
    assert child.grid.header_rows == 1
    (link,) = [k for k in doc.links if k.kind == "continuation"]
    assert (link.from_.block, link.to) == (child.id, parent.id)
    pages = [f.page for f in doc.findings if f.code is FindingCode.HEADER_NOT_FOUND]
    assert 2 not in pages


def test_TC11_a_headerless_table_that_continues_nothing_still_raises_header_not_found() -> None:
    doc = read_with_tables(pdf_factory.headerless_table())
    assert [f.code for f in doc.findings] == [FindingCode.HEADER_NOT_FOUND]


def test_PJ1_a_paragraph_broken_by_the_page_reads_as_one_block() -> None:
    doc = inkgrid.read(pdf_factory.continued_paragraph())
    joined = [b for b in doc.blocks if b.kind == "paragraph" and len(b.regions) == 2]
    (block,) = joined
    assert block.text.endswith("the fee is charged per executed order.")
    assert [r.page for r in block.regions] == [1, 2]


def test_LK1_a_fee_cells_raised_call_resolves_to_its_note() -> None:
    doc = read_with_tables(pdf_factory.footnoted_table())
    (table,) = doc.tables()
    (note,) = [b for b in doc.blocks if isinstance(b, Footnote)]
    (link,) = [k for k in doc.links if k.kind == "footnote_call"]
    assert (link.from_.block, link.from_.cell, link.to, link.label) == (
        table.id,
        (1, 1),
        note.id,
        "1",
    )
    assert link.status == "resolved"


def test_LK2_a_glued_note_number_opens_a_note_that_resolves() -> None:
    doc = inkgrid.read(pdf_factory.glued_notes())
    (note,) = [b for b in doc.blocks if isinstance(b, Footnote)]
    assert note.label == "1"
    assert note.text.startswith("1 A surcharge")
    (link,) = doc.links
    assert (link.label, link.status, link.to) == ("1", "resolved", note.id)
