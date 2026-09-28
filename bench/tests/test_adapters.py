from pathlib import Path

import pytest

import pdf_factory
from inkgrid_bench.adapters import camelot_lattice, inkgrid_read, pdfplumber_tables, pymupdf_tables
from inkgrid_bench.tables import Box, NTable

ADAPTERS = {
    "inkgrid": inkgrid_read.read,
    "pdfplumber": pdfplumber_tables.read,
    "pymupdf": pymupdf_tables.read,
    "camelot": camelot_lattice.read,
}
GRID = (72.0, 100.0, 372.0, 180.0)  # ruled_grid's drawn outline, unrotated, top-left frame


def iou(a: Box, b: Box) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union


def only(tables: list[NTable]) -> NTable:
    (table,) = tables
    return table


@pytest.mark.parametrize("tool", ADAPTERS)
def test_adapters_place_the_grid_where_it_is_drawn(tool: str, tmp_path: Path) -> None:
    pdf = tmp_path / "grid.pdf"
    pdf.write_bytes(pdf_factory.ruled_grid())
    table = only(ADAPTERS[tool](pdf))
    assert table.page == 1
    assert iou(table.bbox, GRID) > 0.9, table.bbox
    spans = {(c.text, c.rows, c.cols) for c in table.cells if c.text}
    assert {("Rate", 1, 2), ("Equity", 2, 1), ("0.60", 1, 1)} <= spans


@pytest.mark.parametrize("tool", ADAPTERS)
def test_adapters_place_boxes_in_the_cropbox_frame(tool: str, tmp_path: Path) -> None:
    if tool == "camelot":
        # Camelot reads a page whose CropBox is not its MediaBox as a wrong grid (9 x 7 for this
        # 4 x 3 table); inkgrid's own reader hands it a copy with equal boxes. Camelot alone is
        # scored as it is.
        pytest.skip("Camelot misreads a cropped page; scored as it is")
    pdf = tmp_path / "crop.pdf"
    pdf.write_bytes(pdf_factory.ruled_grid(cropbox=(50, 50, 562, 742)))
    table = only(ADAPTERS[tool](pdf))
    shifted = (GRID[0] - 50, GRID[1] - 50, GRID[2] - 50, GRID[3] - 50)
    assert iou(table.bbox, shifted) > 0.9, table.bbox


@pytest.mark.parametrize("tool", ADAPTERS)
@pytest.mark.parametrize("turned", ["landscape", "rotate90"])
def test_adapters_place_a_turned_pages_grid_unrotated(
    tool: str, turned: str, tmp_path: Path
) -> None:
    pdf = tmp_path / "landscape.pdf"
    data = (
        pdf_factory.ruled_landscape()
        if turned == "landscape"
        else pdf_factory.ruled_grid(rotation=90)
    )
    pdf.write_bytes(data)
    expected = inkgrid_read.read(pdf)[0].bbox
    assert iou(only(ADAPTERS[tool](pdf)).bbox, expected) > 0.8


def test_inkgrid_marks_its_header_rows(tmp_path: Path) -> None:
    pdf = tmp_path / "grid.pdf"
    pdf.write_bytes(pdf_factory.ruled_grid())
    table = only(inkgrid_read.read(pdf))
    assert {c.text for c in table.cells if c.header} == {"Fee", "Rate"}


@pytest.mark.parametrize("tool", ADAPTERS)
def test_adapters_place_boxes_on_an_offset_mediabox(tool: str, tmp_path: Path) -> None:
    pdf = tmp_path / "offset.pdf"
    pdf.write_bytes(pdf_factory.ruled_grid(mediabox=(-100, -100, 512, 692)))
    expected = inkgrid_read.read(pdf)[0].bbox
    assert iou(only(ADAPTERS[tool](pdf)).bbox, expected) > 0.9


@pytest.mark.parametrize("tool", ADAPTERS)
def test_adapters_read_an_unruled_table(tool: str, tmp_path: Path) -> None:
    # The rule-based peers find no table where nothing is drawn (measured on their pinned
    # versions); inkgrid reads its grid, header row flagged.
    pdf = tmp_path / "unruled.pdf"
    pdf.write_bytes(pdf_factory.unruled_table())
    tables = ADAPTERS[tool](pdf)
    if tool != "inkgrid":
        assert tables == []
        return
    table = only(tables)
    row = {r: [c for c in table.cells if c.row == r] for r in (0, 1)}
    assert [(c.text, c.header) for c in row[0]] == [(t, True) for t in pdf_factory.UNRULED_HEADER]
    assert [c.text for c in row[1]] == pdf_factory.UNRULED_ROWS[0]
