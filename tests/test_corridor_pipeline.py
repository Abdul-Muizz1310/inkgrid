import json

import pytest

import pdf_factory
from inkgrid.model.document import Document, Table
from lattice_builder import read_with_tables

build = read_with_tables


def tables(doc: Document) -> list[Table]:
    return [b for b in doc.blocks if isinstance(b, Table)]


def grid_text(table: Table) -> list[list[str]]:
    rows: list[list[str]] = [[""] * table.grid.n_cols for _ in range(table.grid.n_rows)]
    for cell in table.grid.cells:
        rows[cell.row][cell.col] = cell.text
    return rows


def test_CP1_an_unruled_table_takes_its_place_among_headings() -> None:
    doc = build(pdf_factory.unruled_table())
    assert [b.kind for b in doc.blocks] == ["heading", "paragraph", "table", "heading"]
    (table,) = tables(doc)
    assert (table.grid.n_rows, table.grid.n_cols, table.grid.source) == (5, 4, "corridor")
    assert grid_text(table)[0] == pdf_factory.UNRULED_HEADER
    assert grid_text(table)[2] == pdf_factory.UNRULED_ROWS[1]
    assert table.grid.header_rows == 1


def test_CG5_a_corridor_document_round_trips_through_every_invariant() -> None:
    doc = build(pdf_factory.unruled_table())
    assert Document.model_validate_json(json.dumps(json.loads(doc.model_dump_json()))) == doc


def test_CP2_centred_values_stay_in_the_row_of_their_label() -> None:
    doc = build(pdf_factory.centred_values())
    (table,) = tables(doc)
    rows = grid_text(table)
    labels = [" ".join(label) for label, _ in pdf_factory.CENTRED_ROWS]
    values = [value for _, value in pdf_factory.CENTRED_ROWS]
    assert [r for r in rows if r[1]] == [
        [label, value] for label, value in zip(labels, values, strict=True)
    ]
    assert [pdf_factory.CENTRED_BANNER, ""] in rows


def test_CP3_ruled_and_unruled_tables_on_one_page() -> None:
    doc = build(pdf_factory.ruled_and_unruled())
    assert [t.grid.source for t in tables(doc)] == ["lattice", "corridor"]


def test_CP4_an_unruled_landscape_table_reads_in_screen_order() -> None:
    doc = build(pdf_factory.unruled_landscape())
    (table,) = tables(doc)
    assert table.grid.frame == 90
    assert grid_text(table)[0] == pdf_factory.UNRULED_HEADER


@pytest.mark.parametrize("name", pdf_factory.OPENABLE)
def test_CP5_every_fixture_builds_a_valid_document(name: str) -> None:
    assert isinstance(build(pdf_factory.OPENABLE[name]()), Document)
