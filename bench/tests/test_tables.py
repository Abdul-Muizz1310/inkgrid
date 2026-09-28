import pytest

from inkgrid_bench.tables import NCell, NDocument, NTable, cells_from_boxes


def spanning() -> NTable:
    cells = (
        NCell(0, 0, cols=2, text="Fee", header=True),
        NCell(1, 0, text="Equity"),
        NCell(1, 1, text="0.30"),
    )
    return NTable(page=1, bbox=(72.0, 100.0, 272.0, 140.0), cells=cells)


def test_NT1_a_table_round_trips_through_json() -> None:
    doc = NDocument(
        tool="t", version="1", pdf_sha256="0" * 64, pages=1, tables=(spanning(),), seconds=0.5
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
