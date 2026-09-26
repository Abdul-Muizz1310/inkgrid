import pdf_factory
from inkgrid.core.tables.pages import lattice_pages
from inkgrid.core.tables.shape import ShapeCell, grid_shape
from inkgrid.model.geometry import Rect
from inkgrid.model.page import Rule
from model_builders import mk_page, mk_reading, mk_word


def rules(page: int, h: int, v: int) -> tuple[Rule, ...]:
    across = [
        Rule(page=page, axis="h", at=100 + 10 * i, start=72, end=300, thickness=0.5)
        for i in range(h)
    ]
    down = [
        Rule(page=page, axis="v", at=72 + 10 * i, start=100, end=200, thickness=0.5)
        for i in range(v)
    ]
    return (*across, *down)


def test_LP1_camelot_reads_only_pages_with_rules_both_ways() -> None:
    counts = [(2, 2), (5, 1), (1, 3), (0, 0)]
    pages = tuple(
        mk_page(number=n, words=(mk_word(id=n - 1, page=n),), rules=rules(n, h, v))
        for n, (h, v) in enumerate(counts, 1)
    )
    assert lattice_pages(mk_reading(pages)) == (1,)


def test_GS1_rectangles_become_rows_columns_and_spans() -> None:
    rects = [Rect(*r) for r in pdf_factory.RULED_GRID_CELLS.values()]
    shape = grid_shape(rects)
    assert shape is not None
    assert shape.row_edges == (100, 120, 140, 160, 180)
    assert shape.col_edges == (72, 172, 272, 372)
    by_start = {(c.row, c.col): c for c in shape.cells}
    assert by_start[0, 1] == ShapeCell(0, 1, 1, 2, Rect(172, 100, 372, 120))
    assert by_start[1, 0] == ShapeCell(1, 0, 2, 1, Rect(72, 120, 172, 160))
    assert [(c.row, c.col) for c in shape.cells] == sorted(by_start)
    assert len(shape.cells) == 10


def test_GS2_overlaps_and_holes_are_not_grids() -> None:
    assert grid_shape([Rect(0, 0, 20, 10), Rect(10, 0, 30, 10)]) is None
    assert grid_shape([Rect(0, 0, 10, 10), Rect(10, 0, 20, 10), Rect(0, 10, 10, 20)]) is None


def test_GS3_edges_within_half_a_point_are_one_edge() -> None:
    shape = grid_shape([Rect(0, 0, 10, 10), Rect(10.3, 0, 20, 10)])
    assert shape is not None
    assert shape.col_edges == (0, 10, 20)
    assert [(c.col, c.col_span) for c in shape.cells] == [(0, 1), (1, 1)]
