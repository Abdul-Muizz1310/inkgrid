from collections.abc import Sequence
from typing import Any

import camelot
import pytest

import pdf_factory
from inkgrid.model.geometry import Rect, turn_rect
from inkgrid.model.lattice import LatticeReading, RuledGrid
from inkgrid.read.camelot_reader import Edges, merged_groups, read_lattice
from inkgrid.read.pymupdf_reader import page_frames, read_pdf


def lattice(data: bytes, engine: str = "vector") -> LatticeReading:
    frames = page_frames(data, None)
    return read_lattice(data, frames, [f.number for f in frames], engine=engine, password=None)


def cells_by_word(data: bytes, grid: RuledGrid) -> dict[str, Rect]:
    """Each word of the page by the one cell its centre falls in."""
    out: dict[str, Rect] = {}
    for word in read_pdf(data, file_name=None, password=None).pages[grid.page - 1].words:
        x, y = word.bbox.center
        (cell,) = [c for c in grid.cells if c.contains_point(x, y)]
        out[word.text] = cell
    return out


def shifted(dx: float, dy: float) -> dict[str, Rect]:
    return {
        t: Rect(x0 + dx, y0 + dy, x1 + dx, y1 + dy)
        for t, (x0, y0, x1, y1) in pdf_factory.RULED_GRID_CELLS.items()
    }


def test_CM1_merged_cells_come_back_as_one_rectangle_each() -> None:
    data = pdf_factory.ruled_grid()
    (grid,) = lattice(data).grids
    assert len(grid.cells) == 10
    assert cells_by_word(data, grid) == shifted(0, 0)


@pytest.mark.parametrize(
    ("data", "dx", "dy"),
    [
        pytest.param(pdf_factory.ruled_grid(mediabox=(-100, -100, 512, 692)), 100, -100, id="CM2"),
        pytest.param(pdf_factory.ruled_grid(cropbox=(50, 50, 550, 750)), -50, -50, id="CM3"),
        pytest.param(pdf_factory.ruled_grid(rotation=90), 0, 0, id="CM4-90"),
        pytest.param(pdf_factory.ruled_grid(rotation=180), 0, 0, id="CM4-180"),
        pytest.param(pdf_factory.ruled_grid(rotation=270), 0, 0, id="CM4-270"),
    ],
)
def test_CM2_to_CM4_cells_are_placed_where_the_words_are(data: bytes, dx: float, dy: float) -> None:
    (grid,) = lattice(data).grids
    assert cells_by_word(data, grid) == shifted(dx, dy)


def test_CM5_a_landscape_grid_is_placed_where_the_words_are() -> None:
    data = pdf_factory.ruled_landscape()
    (grid,) = lattice(data).grids
    on_screen = {t: turn_rect(c, 90, 612, 792) for t, c in cells_by_word(data, grid).items()}
    assert on_screen == {t: Rect(*r) for t, r in pdf_factory.RULED_LANDSCAPE_CELLS.items()}


def test_CM6_a_camelot_failure_costs_one_page(monkeypatch: pytest.MonkeyPatch) -> None:
    real = camelot.read_pdf

    def flaky(data: bytes, pages: str, **kw: Any) -> Any:
        if pages == "2":
            msg = "rendering failed"
            raise RuntimeError(msg)
        return real(data, pages, **kw)

    monkeypatch.setattr(camelot, "read_pdf", flaky)
    reading = lattice(pdf_factory.ruled_grid_pages(3))
    assert sorted(g.page for g in reading.grids) == [1, 3]
    assert [(f.code.value, f.page) for f in reading.findings] == [("lattice_failed", 2)]
    assert "RuntimeError: rendering failed" in reading.findings[0].detail


def edges(rows: Sequence[str]) -> list[list[Edges]]:
    """A grid of edge flags from strings like 'lrtb', one per cell."""
    return [
        [Edges(left="l" in c, right="r" in c, top="t" in c, bottom="b" in c) for c in row.split()]
        for row in rows
    ]


def test_CM7_a_merge_that_is_not_a_rectangle_stays_split() -> None:
    assert merged_groups(edges(["ltb rtb", "lrtb lrtb"])) == [
        (0, 0, 1, 2),
        (1, 0, 2, 1),
        (1, 1, 2, 2),
    ]
    l_shape = edges(["lt t", "lb lrtb"])  # (0,0)-(0,1) and (0,0)-(1,0) open, (1,1) closed
    assert merged_groups(l_shape) == [(0, 0, 1, 1), (0, 1, 1, 2), (1, 0, 2, 1), (1, 1, 2, 2)]


@pytest.mark.parametrize("engine", ["combined", "raster"])
def test_CM8_every_engine_reads_the_same_cells(engine: str) -> None:
    data = pdf_factory.ruled_grid()
    (grid,) = lattice(data, engine).grids
    placed = cells_by_word(data, grid)
    for text, want in shifted(0, 0).items():
        got = placed[text]
        assert (
            max(
                abs(a - b)
                for a, b in zip(
                    (got.x0, got.y0, got.x1, got.y1),
                    (want.x0, want.y0, want.x1, want.y1),
                    strict=True,
                )
            )
            <= 1.0
        )
