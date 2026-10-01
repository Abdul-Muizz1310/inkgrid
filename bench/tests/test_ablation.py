from pathlib import Path

from inkgrid_bench.ablation import ocr_tables, words_from_tsv

import pdf_factory
from inkgrid.model.geometry import Rect
from inkgrid.read.pymupdf_reader import read_pdf
from inkgrid_bench import pages
from inkgrid_bench.adapters import inkgrid_read
from inkgrid_bench.tables import NPage

HEADER = (
    "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"
)
ROWS = [
    "1\t1\t0\t0\t0\t0\t0\t0\t2550\t3300\t-1\t",
    "5\t1\t1\t1\t1\t1\t300\t600\t150\t40\t96.5\tFees",
    "5\t1\t1\t1\t1\t2\t500\t600\t100\t40\t-1\t   ",
    "4\t1\t1\t1\t1\t0\t300\t600\t500\t40\t-1\t",
    "5\t1\t1\t1\t1\t3\t700\t600\t100\t40\t91.0\tA\x01b",
]
TSV = "\n".join([HEADER, *ROWS]) + "\n"
SCALE = 72 / 300


def test_AB1_tesseract_words_in_points_on_their_page() -> None:
    upright = NPage(box=(0.0, 0.0, 612.0, 792.0), rotation=0)
    first, second = words_from_tsv(TSV, page=1, frame=upright, scale=SCALE, first_id=0)
    assert (first.id, first.text, first.bbox, first.size) == (
        0,
        "Fees",
        Rect(72, 144, 108, 153.6),
        9.6,
    )
    assert (second.id, second.text, second.bbox) == (1, "Ab", Rect(168, 144, 192, 153.6))
    assert first.horizontal
    assert not first.bold
    assert first.font == "tesseract"
    turned = NPage(box=(0.0, 0.0, 612.0, 792.0), rotation=90)
    (word, _) = words_from_tsv(TSV, page=1, frame=turned, scale=SCALE, first_id=5)
    # shown at (72, 144)-(108, 153.6) on a page turned 90 degrees: (144, 684)-(153.6, 720) unturned
    assert (word.id, word.bbox, word.horizontal) == (5, Rect(144, 684, 153.6, 720), False)


def tsv_of(data: bytes) -> dict[int, str]:
    """The fixture's own words as Tesseract would print them, page by page."""
    out: dict[int, str] = {}
    for page in read_pdf(data, file_name=None, password=None).pages:
        rows = [HEADER]
        for w in page.words:
            left, top = round(w.bbox.x0 / SCALE), round(w.bbox.y0 / SCALE)
            width, height = round(w.bbox.width / SCALE), round(w.bbox.height / SCALE)
            rows.append(
                f"5\t{page.number}\t1\t1\t1\t1\t{left}\t{top}\t{width}\t{height}\t95\t{w.text}"
            )
        out[page.number] = "\n".join(rows) + "\n"
    return out


def test_AB2_inkgrid_fed_its_own_words_through_tesseract_reads_the_same_table(
    tmp_path: Path,
) -> None:
    data = pdf_factory.ruled_grid()
    pdf = tmp_path / "ruled_grid.pdf"
    pdf.write_bytes(data)
    tsv = tsv_of(data)
    tables = ocr_tables(data, pages.frames(pdf), lambda number: tsv[number])
    expected = inkgrid_read.read(pdf)
    assert [(t.page, t.cells) for t in tables] == [(t.page, t.cells) for t in expected]
    assert len(tables) == 1
