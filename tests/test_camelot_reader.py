from collections.abc import Sequence
from typing import Any, ClassVar

import camelot
import pytest

import pdf_factory
from inkgrid.model.geometry import Rect, turn_rect
from inkgrid.model.lattice import LatticeReading, RuledGrid
from inkgrid.read.camelot_reader import Edges, frame_core, merged_groups, read_lattice
from inkgrid.read.pymupdf_reader import lattice_copy, page_frames, read_pdf


def lattice(data: bytes, engine: str = "vector", password: str | None = None) -> LatticeReading:
    frames = page_frames(data, password)
    copy = lattice_copy(data, password)
    return read_lattice(copy, frames, [f.number for f in frames], engine=engine, password=None)


def cells_by_word(data: bytes, grid: RuledGrid, password: str | None = None) -> dict[str, Rect]:
    """Each word of the page by the one cell its centre falls in."""
    out: dict[str, Rect] = {}
    for word in read_pdf(data, file_name=None, password=password).pages[grid.page - 1].words:
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


ENGINES = ["vector", "combined", "raster"]
CROP = (50, 50, 550, 750)


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize(
    ("data", "dx", "dy"),
    [
        pytest.param(pdf_factory.ruled_grid(mediabox=(-100, -100, 512, 692)), 100, -100, id="CM2"),
        pytest.param(pdf_factory.ruled_grid(cropbox=CROP), -50, -50, id="CM3"),
        pytest.param(pdf_factory.ruled_grid(rotation=90), 0, 0, id="CM4-90"),
        pytest.param(pdf_factory.ruled_grid(rotation=180), 0, 0, id="CM4-180"),
        pytest.param(pdf_factory.ruled_grid(rotation=270), 0, 0, id="CM4-270"),
        pytest.param(pdf_factory.ruled_grid(rotation=90, cropbox=CROP), -50, -50, id="CM4-90-crop"),
        pytest.param(
            pdf_factory.ruled_grid(rotation=180, cropbox=CROP), -50, -50, id="CM4-180-crop"
        ),
        pytest.param(
            pdf_factory.ruled_grid(rotation=270, cropbox=CROP), -50, -50, id="CM4-270-crop"
        ),
    ],
)
def test_CM2_to_CM4_and_CM8_cells_are_placed_where_the_words_are(
    data: bytes, dx: float, dy: float, engine: str
) -> None:
    (grid,) = lattice(data, engine).grids
    near(cells_by_word(data, grid), shifted(dx, dy))


def near(got: dict[str, Rect], want: dict[str, Rect]) -> None:
    """The same cells for the same words, each edge within 1 pt."""
    assert got.keys() == want.keys()
    for text, cell in want.items():
        edges = zip(
            (got[text].x0, got[text].y0, got[text].x1, got[text].y1),
            (cell.x0, cell.y0, cell.x1, cell.y1),
            strict=True,
        )
        assert max(abs(a - b) for a, b in edges) <= 1.0, text


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("cropbox", [None, (0, 0, 612, 750)], ids=["full", "crop"])
def test_CM5_a_landscape_grid_is_placed_where_the_words_are(
    engine: str, cropbox: tuple[float, float, float, float] | None
) -> None:
    data = pdf_factory.ruled_landscape(cropbox)
    page = read_pdf(data, file_name=None, password=None).pages[0]
    (grid,) = lattice(data, engine).grids
    placed = cells_by_word(data, grid)
    on_screen = {t: turn_rect(c, 90, page.width, page.height) for t, c in placed.items()}
    shift = page.height - 792  # a CropBox trimming the page's foot moves the screen's x origin
    want = {
        t: Rect(x0 + shift, y0, x1 + shift, y1)
        for t, (x0, y0, x1, y1) in pdf_factory.RULED_LANDSCAPE_CELLS.items()
    }
    near(on_screen, want)


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


def test_CM11_a_table_with_no_cells_is_skipped_with_a_finding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = camelot.read_pdf

    class Empty:  # the shape Camelot returned for a degenerate grid: rows that hold no cells
        cells: ClassVar[list[list[Any]]] = [[], []]
        pdf_size = (612.0, 792.0)
        shape = (2, 0)

    def with_empty(data: bytes, pages: str, **kw: Any) -> Any:
        return [*real(data, pages, **kw), Empty()]

    monkeypatch.setattr(camelot, "read_pdf", with_empty)
    reading = lattice(pdf_factory.ruled_grid())
    assert [g.page for g in reading.grids] == [1]
    assert [(f.code.value, f.page) for f in reading.findings] == [("lattice_failed", 1)]
    assert "no cells" in reading.findings[0].detail


def test_CM11_merged_groups_of_no_cells_is_empty() -> None:
    assert merged_groups([]) == []
    assert merged_groups([[], []]) == []


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


def test_CM9_encrypted_documents_keep_their_tables() -> None:
    owner_only = pdf_factory.ruled_encrypted(None)
    assert len(lattice(owner_only).grids) == 1
    locked = pdf_factory.ruled_encrypted("secret")
    (grid,) = lattice(locked, password="secret").grids
    near(cells_by_word(locked, grid, password="secret"), shifted(0, 0))


@pytest.mark.parametrize(
    "data",
    [
        pdf_factory.ruled_grid(mediabox=(-100, -100, 512, 692)),
        pdf_factory.ruled_grid(cropbox=CROP),
        pdf_factory.ruled_grid(rotation=90, cropbox=CROP),
        pdf_factory.ruled_grid(rotation=180, cropbox=(10, 10, 602, 782)),
        pdf_factory.ruled_landscape((0, 0, 612, 750)),
    ],
    ids=["offset", "crop", "crop-90", "crop-180", "landscape-crop"],
)
def test_LC1_the_lattice_copy_shows_every_word_where_the_original_does(data: bytes) -> None:
    copy = lattice_copy(data, None)
    original = read_pdf(data, file_name=None, password=None)
    copied = read_pdf(copy, file_name=None, password=None)
    assert [(w.text, w.bbox) for w in copied.words()] == [
        (w.text, w.bbox) for w in original.words()
    ]


def test_LC1_the_lattice_copy_is_decrypted() -> None:
    copy = lattice_copy(pdf_factory.ruled_encrypted("secret"), "secret")
    assert [w.text for w in read_pdf(copy, file_name=None, password=None).words()][:1] == ["Fee"]


def test_CM10_a_group_with_a_drawn_edge_inside_stays_split() -> None:
    crossed = edges(["lt rtb", "lb rbt"])
    assert merged_groups(crossed) == [(0, 0, 1, 1), (0, 1, 1, 2), (1, 0, 2, 1), (1, 1, 2, 2)]


# --- a frame's core (spec 14 section 4.2) ---------------------------------------------------------

US022 = """lrt- l-tb --tb --tb --tb --tb --tb --tb --tb --tb --tb -rt-
lr-- lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lr--
lr-- lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lr--
lr-- lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lr--
lr-- lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lr--
lr-- lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lr--
lr-- lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lr--
lr-- lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lr--
lr-- lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lr--
lr-b l-t- --t- --t- --t- --t- --t- --t- --t- --t- --t- -r--
lrtb l--b ---b ---b ---b ---b ---b ---b ---b ---b ---b -r-b"""
C45171 = """l-t- --tb --tb --tb --tb --tb --tb --tb --tb --tb --tb --tb --tb --tb --tb -rt-
lr-- lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lr--
lr-- lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lr--
lr-- lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lr--
lr-- lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lrtb lr--
l--b --tb --tb --tb --tb --tb --tb --tb --tb --tb --tb --tb --tb --tb --tb -r-b"""
CAPTION_IN_BOX = """lrt- l-tb --tb -rtb
lrtb lrtb lrtb lrtb
lrtb lrtb lrtb lrtb"""


def test_FR2_a_frames_core_is_found_from_its_edge_flags() -> None:
    # practice us-022 and olmOCR c45171 (measured): a ruled table inside a frame's open ring
    assert frame_core(edges(US022.splitlines())) == (1, 1, 9, 11)
    assert frame_core(edges(C45171.splitlines())) == (1, 1, 5, 15)
    assert frame_core(edges(CAPTION_IN_BOX.splitlines())) is None
    assert frame_core(edges(["lrtb lrtb", "lrtb lrtb"])) is None  # a plain table is its own grid
