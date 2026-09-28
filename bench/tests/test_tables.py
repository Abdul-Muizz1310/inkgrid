import pytest

from inkgrid_bench.tables import NCell, NDocument, NPage, NTable, cells_from_boxes


def spanning() -> NTable:
    cells = (
        NCell(0, 0, cols=2, text="Fee", header=True),
        NCell(1, 0, text="Equity"),
        NCell(1, 1, text="0.30"),
    )
    return NTable(page=1, bbox=(72.0, 100.0, 272.0, 140.0), cells=cells)


def test_NT1_a_table_round_trips_through_json() -> None:
    pages = (NPage(box=(0.0, 0.0, 612.0, 792.0), rotation=90),)
    doc = NDocument(
        tool="t", version="1", pdf_sha256="0" * 64, pages=pages, tables=(spanning(),), seconds=0.5
    )
    assert NDocument.from_json(doc.to_json()) == doc
    assert (spanning().n_rows, spanning().n_cols) == (2, 2)


def test_NT1_cells_must_tile_the_grid() -> None:
    with pytest.raises(ValueError, match="covered twice"):
        NTable(page=1, bbox=(0, 0, 1, 1), cells=(NCell(0, 0, cols=2), NCell(0, 1)))
    filled = NTable.filled(page=1, bbox=(0, 0, 1, 1), cells=(NCell(0, 0), NCell(1, 1)))
    assert sorted((c.row, c.col) for c in filled.cells) == [(0, 0), (0, 1), (1, 0), (1, 1)]


def test_NT2_spans_come_from_the_edges_the_boxes_cover() -> None:
    # 3 x-edges (0, 50, 100) and 3 y-edges (0, 10, 20); `A` spans both columns, `B` both rows
    boxes = [
        [(0.0, 0.0, 100.0, 10.0), None],
        [(0.0, 10.0, 50.0, 20.0), (50.0, 10.0, 100.0, 20.0)],
    ]
    texts = [["A", None], ["B", "C"]]
    cells = cells_from_boxes(boxes, texts)
    assert cells == [NCell(0, 0, cols=2, text="A"), NCell(1, 0, text="B"), NCell(1, 1, text="C")]


def test_NT2_edges_within_a_point_are_one_edge() -> None:
    boxes = [[(0.0, 0.0, 50.0, 10.0), (50.4, 0.0, 100.0, 10.2)]]
    assert [(c.row, c.col, c.rows, c.cols) for c in cells_from_boxes(boxes, [["a", "b"]])] == [
        (0, 0, 1, 1),
        (0, 1, 1, 1),
    ]


def test_NT1_a_page_knows_its_frame() -> None:
    page = NPage(box=(-100.0, -100.0, 512.0, 692.0), rotation=0)
    assert (page.width, page.height) == (612.0, 792.0)
    assert page.to_user(172.0, 92.0) == (72.0, 600.0)  # top-left frame to PDF user space


def test_NT3_a_span_stops_before_another_cells_anchor() -> None:
    # pdfplumber on eu-011: the first box covers rows 1-2 of columns 0-2, and a box anchored in
    # row 2, column 1 lies inside it; the outer cell keeps row 1 only
    boxes = [
        [(0.0, 0.0, 10.0, 5.0), (10.0, 0.0, 20.0, 5.0), (20.0, 0.0, 30.0, 5.0)],
        [(0.0, 5.0, 30.0, 20.0), None, None],
        [None, (10.0, 10.0, 20.0, 20.0), None],
    ]
    texts = [["a", "b", "c"], ["outer", None, None], [None, "inner", None]]
    cells = cells_from_boxes(boxes, texts)
    assert NCell(1, 0, cols=3, text="outer") in cells
    assert NCell(2, 1, text="inner") in cells
    table = NTable.filled(page=1, bbox=(0, 0, 30, 20), cells=cells)
    assert (table.n_rows, table.n_cols) == (3, 3)


def test_NT3_rows_are_cut_before_columns() -> None:
    # a 2 x 2 box with another anchor at its lower right keeps its first row, both columns
    boxes = [[(0.0, 0.0, 20.0, 20.0), None], [None, (10.0, 10.0, 20.0, 20.0)]]
    cells = cells_from_boxes(boxes, [["big", None], [None, "x"]])
    assert cells[0] == NCell(0, 0, cols=2, text="big")
