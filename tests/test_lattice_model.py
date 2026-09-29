from typing import Any

import pytest
from pydantic import ValidationError

import pdf_factory
from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.geometry import Rect
from inkgrid.model.lattice import LatticeReading, PageFrame, RuledGrid
from inkgrid.read.pymupdf_reader import page_frames


def test_ruled_grid_needs_cells_of_positive_size() -> None:
    assert RuledGrid(page=1, cells=(Rect(0, 0, 10, 10),)).cells[0] == Rect(0, 0, 10, 10)
    with pytest.raises(ValidationError):
        RuledGrid(page=1, cells=())
    with pytest.raises(ValidationError, match="positive size"):
        RuledGrid(page=1, cells=(Rect(0, 0, 0, 10),))


def lattice(**kw: Any) -> LatticeReading:
    fields: dict[str, Any] = {"engine": "vector", "camelot": "2.0.0", "pages": (1,), "grids": ()}
    fields.update(kw)
    return LatticeReading(**fields)


def test_lattice_reading_holds_only_pages_it_read() -> None:
    assert lattice().pages == (1,)
    with pytest.raises(ValidationError, match="page 2"):
        lattice(grids=(RuledGrid(page=2, cells=(Rect(0, 0, 10, 10),)),))
    with pytest.raises(ValidationError, match="page 3"):
        lattice(findings=(Finding.of(FindingCode.LATTICE_FAILED, "boom", page=3),))


def test_page_frames_report_rotation_and_cropbox_size() -> None:
    (crop,) = page_frames(pdf_factory.cropbox(), None)
    assert crop == PageFrame(number=1, rotation=0, width=500, height=700)
    (turned,) = page_frames(pdf_factory.rotated(), None)
    assert (turned.rotation, turned.width, turned.height) == (90, 612, 792)


def test_FR2_a_grids_core_lies_inside_it() -> None:
    cells = (Rect(0, 0, 50, 10), Rect(50, 0, 100, 10), Rect(0, 10, 100, 40))
    assert RuledGrid(page=1, cells=cells).core is None
    assert RuledGrid(page=1, cells=cells, core=Rect(10, 5, 90, 35)).core == Rect(10, 5, 90, 35)
    with pytest.raises(ValidationError, match="core"):
        RuledGrid(page=1, cells=cells, core=Rect(10, 5, 110, 35))
