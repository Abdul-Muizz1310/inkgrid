from pathlib import Path

import pytest
from PIL import Image

import pdf_factory
from inkgrid_bench.draft import PageWord, build_truth, cell_text, crop, draft_table, overlay, ruler
from inkgrid_bench.heldout import load_truth


def word(box: tuple[float, float, float, float], text: str, line: int, n: int) -> PageWord:
    return (*box, text, 0, line, n)


WORDS = [
    word((10, 10, 40, 20), "Annual", 0, 0),
    word((42, 10, 60, 20), "fee", 0, 1),
    word((110, 10, 140, 20), "4,715", 0, 2),
    word((10, 30, 50, 40), "Port", 1, 0),
    word((10, 41, 50, 49), "rental", 2, 0),  # a second line in the same cell
    word((110, 30, 130, 40), "55", 1, 1),
]


def test_DR1_a_cells_text_is_its_words_in_reading_order() -> None:
    assert cell_text(WORDS, (0, 0, 100, 25)) == "Annual fee"
    assert cell_text(WORDS, (0, 25, 100, 50)) == "Port rental"
    assert cell_text(WORDS, (100, 0, 200, 25)) == "4,715"
    assert cell_text(WORDS, (200, 0, 300, 25)) == ""
    table = draft_table(
        WORDS, page=3, rows=[0, 25, 50], cols=[0, 100, 200], merges=[], header_rows=0, stub_cols=1
    )
    assert [(c.row, c.col, c.text, c.box) for c in table.cells] == [
        (0, 0, "Annual fee", (0.0, 0.0, 100.0, 25.0)),
        (0, 1, "4,715", (100.0, 0.0, 200.0, 25.0)),
        (1, 0, "Port rental", (0.0, 25.0, 100.0, 50.0)),
        (1, 1, "55", (100.0, 25.0, 200.0, 50.0)),
    ]
    assert (table.page, table.bbox, table.stub_cols) == (3, (0.0, 0.0, 200.0, 50.0), 1)
    merged = draft_table(
        WORDS, page=3, rows=[0, 25, 50], cols=[0, 100, 200], merges=[(0, 0, 2, 1)],
        header_rows=0, stub_cols=1,
    )  # fmt: skip
    first = merged.cells[0]
    assert (first.row, first.col, first.rows, first.text) == (0, 0, 2, "Annual fee Port rental")
    assert len(merged.cells) == 3


def test_DR2_a_merge_off_the_grid_or_over_another_is_refused() -> None:
    grid = {"page": 1, "rows": [0, 25, 50], "cols": [0, 100, 200], "header_rows": 0, "stub_cols": 0}
    with pytest.raises(ValueError, match="past the grid"):
        draft_table(WORDS, merges=[(1, 1, 2, 1)], **grid)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="covered twice"):
        draft_table(WORDS, merges=[(0, 0, 2, 1), (1, 0, 1, 2)], **grid)  # type: ignore[arg-type]


def test_DR3_the_renderings_are_the_page_at_their_dpi(tmp_path: Path) -> None:
    pdf = tmp_path / "grid.pdf"
    pdf.write_bytes(pdf_factory.ruled_grid())  # a 612 x 792 page
    table = draft_table(
        [], page=1, rows=[100, 200], cols=[100, 300], merges=[], header_rows=0, stub_cols=0
    )
    for path, dpi in (
        (ruler(pdf, 1, tmp_path / "r.png", dpi=72), 72),
        (overlay(pdf, 1, [table], tmp_path / "o.png", dpi=72), 72),
    ):
        with Image.open(path) as image:
            assert image.size == (612, 792), dpi
    with Image.open(
        crop(pdf, 1, (100, 100, 150, 120), tmp_path / "c.png", dpi=144, pad=0)
    ) as image:
        assert image.size == (100, 40)


def test_DR4_a_grid_file_builds_a_loadable_unverified_truth() -> None:
    grids = {
        "id": "x",
        "pages": [3, 4],
        "tables": [
            {"page": 3, "rows": [0, 25, 50], "cols": [0, 100, 200], "merges": [],
             "header_rows": 1, "stub_cols": 1, "text": {"1,1": "55 (corrected)"}},
        ],
    }  # fmt: skip
    built = build_truth(grids, {3: WORDS, 4: []}, drafted="2026-10-01")
    truth = load_truth(built)
    assert truth.verified is None
    assert truth.pages == (3, 4)
    (table,) = truth.tables
    assert [c.text for c in table.cells] == ["Annual fee", "4,715", "Port rental", "55 (corrected)"]
    assert build_truth(grids, {3: WORDS, 4: []}, drafted="2026-10-01") == built
