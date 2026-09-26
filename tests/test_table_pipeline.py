import json

import pytest
from pydantic import ValidationError

import pdf_factory
from inkgrid.model.document import Document, Table
from lattice_builder import read_with_tables

build = read_with_tables


def tables(doc: Document) -> list[Table]:
    return [b for b in doc.blocks if isinstance(b, Table)]


def test_TP1_a_ruled_grid_reads_as_a_table() -> None:
    doc = build(pdf_factory.ruled_grid())
    (table,) = tables(doc)
    assert set(table.word_ids) == {w.id for w in doc.words}
    assert (table.grid.n_rows, table.grid.n_cols, table.grid.header_rows) == (4, 3, 1)
    spans = {c.text: (c.row_span, c.col_span) for c in table.grid.cells if c.text}
    assert spans["Rate"] == (1, 2)
    assert spans["Equity"] == (2, 1)
    assert table.text.split("\n")[0] == "Fee Rate"
    assert doc.producer.camelot is not None


def test_TP2_a_table_takes_its_place_between_paragraphs() -> None:
    doc = build(pdf_factory.table_between_paragraphs())
    assert [b.kind for b in doc.blocks] == ["paragraph", "table", "paragraph"]
    assert doc.blocks[0].text == " ".join(pdf_factory.TABLE_BEFORE)
    assert doc.blocks[2].text == " ".join(pdf_factory.TABLE_AFTER)


def test_TP3_a_box_around_a_paragraph_is_not_a_table() -> None:
    doc = build(pdf_factory.boxed_paragraph())
    assert [(b.kind, b.text) for b in doc.blocks] == [
        ("paragraph", " ".join(pdf_factory.BOXED_PARAGRAPH))
    ]


def test_TP4_a_landscape_table_reads_in_screen_order() -> None:
    doc = build(pdf_factory.ruled_landscape())
    (table,) = tables(doc)
    assert table.grid.frame == 90
    assert table.text.split("\n") == ["Fee Rate Cap", "Equity 0.10 0.20"]


def test_TP5_a_turned_table_read_in_the_wrong_frame_is_rejected() -> None:
    doc = build(pdf_factory.ruled_landscape())
    data = json.loads(doc.model_dump_json())
    (index,) = [i for i, b in enumerate(data["blocks"]) if b["kind"] == "table"]
    data["blocks"][index]["grid"]["frame"] = 0
    with pytest.raises(ValidationError, match="outside cell"):
        Document.model_validate_json(json.dumps(data))


def test_TP6_a_boxed_furniture_label_is_not_a_table() -> None:
    doc = build(pdf_factory.labelled_page())
    assert tables(doc) == []
    assert [b.text for b in doc.blocks if b.kind == "furniture"] == [pdf_factory.LABEL] * 3
