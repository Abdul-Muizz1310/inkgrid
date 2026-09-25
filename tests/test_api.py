from pathlib import Path

import inkgrid
import pdf_factory
from inkgrid.read.pymupdf_reader import read_pdf


def test_A1_read_pages_reads_a_path(tmp_path: Path) -> None:
    data = pdf_factory.simple_text()
    path = tmp_path / "fees.pdf"
    path.write_bytes(data)
    reading = inkgrid.read_pages(path)
    assert reading == read_pdf(data, file_name="fees.pdf", password=None)


def test_A1_read_pages_accepts_bytes_and_a_password() -> None:
    reading = inkgrid.read_pages(pdf_factory.encrypted(user_pw="u"), password="u")
    assert [w.text for w in reading.words()] == ["secret"]
    assert reading.source.file_name is None


def test_A2_every_public_name_is_importable() -> None:
    for name in inkgrid.__all__:
        assert getattr(inkgrid, name) is not None, name


def test_A2_public_surface_is_exactly_the_spec() -> None:
    assert set(inkgrid.__all__) == {
        "__version__",
        "read_pages",
        "InkgridError",
        "PdfOpenError",
        "PasswordRequired",
        "WrongPassword",
        "InvariantError",
        "StrictModeError",
        "Reading",
        "PageModel",
        "PageInfo",
        "Word",
        "Rule",
        "Rect",
        "Interval",
        "Finding",
        "FindingCode",
        "Severity",
        "Document",
        "Block",
        "Heading",
        "Paragraph",
        "ListItem",
        "Footnote",
        "Definition",
        "Table",
        "Furniture",
        "Grid",
        "Cell",
        "Link",
        "LinkEnd",
        "Region",
        "Ledger",
        "Producer",
    }
