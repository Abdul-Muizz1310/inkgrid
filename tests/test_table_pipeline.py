import json
from typing import Any

import camelot
import pytest
from pydantic import ValidationError

import inkgrid
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


def test_TP7_a_ruled_two_column_page_reads_as_prose_columns() -> None:
    doc = build(pdf_factory.ruled_columns())
    assert tables(doc) == []
    texts = [b.text for b in doc.blocks]
    assert texts.index(" ".join(pdf_factory.RULED_COLUMNS_LEFT)) < texts.index(
        " ".join(pdf_factory.RULED_COLUMNS_RIGHT)
    )


def test_TP8_a_table_reads_within_its_column() -> None:
    doc = build(pdf_factory.table_in_right_column())
    left = [" ".join(p) for p in pdf_factory.RIGHT_COLUMN_LEFT]
    right = [" ".join(p) for p in pdf_factory.RIGHT_COLUMN_RIGHT]
    order = [b.text if b.kind != "table" else "TABLE" for b in doc.blocks]
    assert order == [*left, right[0], "TABLE", right[1]]


def test_TP9_a_failed_page_is_not_also_a_disagreement(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: Any, **kwargs: Any) -> Any:
        msg = "rendering failed"
        raise RuntimeError(msg)

    monkeypatch.setattr(camelot, "read_pdf", broken)
    doc = build(pdf_factory.ruled_grid())
    assert [(f.code.value, f.page) for f in doc.findings] == [("lattice_failed", 1)]


# --- spec 14: grids kept to their tables ------------------------------------------------


def verified(data: bytes, doc: Document) -> None:
    report = inkgrid.verify(doc, data)
    assert report.ok, [(d.code.value, d.text, d.detail) for d in report.defects]


def test_GO1_a_frame_grid_over_a_table_is_not_a_second_table() -> None:
    data = pdf_factory.open_frame_table()
    doc = build(data, engine="combined")
    (table,) = tables(doc)
    assert (table.grid.n_rows, table.grid.n_cols) == (4, 3)
    assert [b.kind for b in doc.blocks if b.kind != "table"] == ["heading", "paragraph"]
    verified(data, doc)


def test_FR1_a_frame_around_a_table_reads_as_its_core() -> None:
    data = pdf_factory.framed_table()
    doc = build(data, engine="combined")
    (table,) = tables(doc)
    assert (table.grid.n_rows, table.grid.n_cols) == (4, 3)
    assert doc.blocks[0].text == pdf_factory.FRAMED_HEADING
    verified(data, doc)


def test_LS1_a_grey_fill_between_two_columns_keeps_them_apart() -> None:
    data = pdf_factory.grey_column_rule()
    doc = build(data)
    (table,) = tables(doc)
    assert table.grid.n_cols == 3
    assert table.text.split("\n")[0] == "Band Rate Cap"
    verified(data, doc)


def test_LS2_a_rule_camelot_drops_still_divides_its_columns() -> None:
    data = pdf_factory.stub_column_rule()
    doc = build(data)
    (table,) = tables(doc)
    assert table.grid.n_cols == 3
    spans = {c.text: c.col_span for c in table.grid.cells if c.text}
    assert spans["Fees"] == 2
    verified(data, doc)


def test_DG1_a_diagonal_watermark_is_no_cells() -> None:
    data = pdf_factory.watermarked_table()
    doc = build(data)
    (table,) = tables(doc)
    watermark = {w.id for w in doc.words if w.text in {"DRAFT", "COPY"}}
    assert watermark
    assert not watermark & set(table.word_ids)
    verified(data, doc)


@pytest.mark.parametrize("name", ["bar_chart", "bar_chart_landscape"])
def test_CH1_CH4_CH5_a_bar_chart_is_no_table_in_either_gridder(name: str) -> None:
    data = pdf_factory.OPENABLE[name]()
    for engine in ("combined", "vector"):
        doc = build(data, engine=engine)
        assert tables(doc) == []
        charts = [f for f in doc.findings if f.code.value == "chart_left_as_text"]
        assert len(charts) == 1, engine
        verified(data, doc)


def test_FT1_a_spanning_header_in_the_top_band_stays_in_its_ruled_table() -> None:
    data = pdf_factory.spanning_header_pages()
    doc = build(data)
    assert [b.text for b in doc.blocks if b.kind == "furniture"] == ["Acme Fee Guide"] * 3
    found = tables(doc)
    assert len(found) == 3
    assert all(t.text.startswith("Threshold for releases") for t in found)
    verified(data, doc)


def furniture(doc: Document) -> list[tuple[int, str]]:
    return [(b.regions[0].page, b.text) for b in doc.blocks if b.kind == "furniture"]


def charts(doc: Document) -> list[str]:
    return [f.detail for f in doc.findings if f.code.value == "chart_left_as_text"]


def test_DG3_a_diagonal_watermark_over_an_unruled_table_splits_nothing() -> None:
    data = pdf_factory.unruled_watermarked_table()
    doc = build(data, engine="combined")
    (table,) = tables(doc)
    assert (table.grid.n_rows, table.grid.n_cols) == (9, 3)
    verified(data, doc)


def test_CH6_a_ruled_table_with_data_bars_is_a_table() -> None:
    data = pdf_factory.data_bar_table()
    doc = build(data, engine="combined")
    (table,) = tables(doc)
    assert (table.grid.n_rows, table.grid.n_cols) == (7, 3)
    assert charts(doc) == []
    verified(data, doc)


def test_CH7_tier_numbers_level_with_sub_row_rules_are_no_axis() -> None:
    data = pdf_factory.tier_sub_rules()
    doc = build(data, engine="combined")
    assert len(tables(doc)) == 1
    assert charts(doc) == []
    verified(data, doc)


def test_FR4_side_cells_with_top_aligned_text_keep_the_whole_grid() -> None:
    data = pdf_factory.top_aligned_side_cells()
    doc = build(data, engine="combined")
    (table,) = tables(doc)
    assert (table.grid.n_rows, table.grid.n_cols) == (6, 4)
    verified(data, doc)


@pytest.mark.parametrize(
    ("name", "header"),
    [
        ("framed_pages", "Acme Exchange Fee Guide 2026"),
        ("bordered_newsletter", "Acme Exchange Member Newsletter"),
    ],
)
def test_FT5_furniture_inside_a_page_border_stays_furniture(name: str, header: str) -> None:
    data = pdf_factory.OPENABLE[name]()
    doc = build(data, engine="combined")
    assert furniture(doc) == [(n, text) for n in (1, 2, 3) for text in (header, str(n))]
    verified(data, doc)


def test_FT6_a_running_header_box_is_furniture_not_a_table() -> None:
    data = pdf_factory.running_box_pages()
    doc = build(data, engine="combined")
    assert tables(doc) == []
    marked = furniture(doc)
    for n in (1, 2, 3):
        assert (n, "Schedule of Fees and Charges Revision 3") in marked
        assert (n, str(n)) in marked
    verified(data, doc)


def test_FT7_a_three_part_footer_leaves_the_line_above_it_furniture() -> None:
    data = pdf_factory.three_part_footer_pages()
    doc = build(data, engine="combined")
    copyright_line = "Copyright 2026 Acme Exchange. All rights reserved."
    assert [(n, copyright_line) for n in (1, 2, 3)] == [
        f for f in furniture(doc) if "Copyright" in f[1]
    ]
    verified(data, doc)
