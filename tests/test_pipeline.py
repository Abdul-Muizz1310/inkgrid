import pytest

import pdf_factory
from inkgrid.core.pipeline import build_document
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.document import Document
from inkgrid.read.pymupdf_reader import read_pdf


def build(data: bytes) -> Document:
    reading = read_pdf(data, file_name=None, password=None)
    return build_document(reading, lexicon=Lexicon(), profile=Profile(), lattice="combined")


def content(doc: Document) -> list[tuple[str, str]]:
    return [(b.kind, b.text) for b in doc.blocks if b.kind != "furniture"]


@pytest.mark.parametrize("name", pdf_factory.OPENABLE)
def test_PL1_every_fixture_builds_a_valid_document(name: str) -> None:
    doc = build(pdf_factory.OPENABLE[name]())
    assert Document.model_validate_json(doc.model_dump_json()) == doc


def test_PL2_two_columns_read_in_column_order() -> None:
    doc = build(pdf_factory.two_column())
    assert content(doc) == [
        ("heading", pdf_factory.TWO_COLUMN_TITLE),
        ("paragraph", " ".join(pdf_factory.TWO_COLUMN_LEFT)),
        ("paragraph", " ".join(pdf_factory.TWO_COLUMN_RIGHT)),
        ("paragraph", pdf_factory.TWO_COLUMN_CLOSING),
    ]


def test_PL3_running_header_and_footer_frame_each_page() -> None:
    doc = build(pdf_factory.furnished())
    pages = pdf_factory.FURNISHED_PAGES
    expected = []
    for n in range(1, pages + 1):
        expected += [
            ("furniture", pdf_factory.FURNISHED_HEADER),
            ("paragraph", " ".join(pdf_factory.furnished_body(n))),
            ("furniture", f"Page {n} of {pages}"),
        ]
    assert [(b.kind, b.text) for b in doc.blocks] == expected


@pytest.mark.parametrize("name", ["image_only", "blank"])
def test_PL4_a_document_without_text_has_no_blocks(name: str) -> None:
    doc = build(pdf_factory.OPENABLE[name]())
    assert doc.blocks == ()
    assert doc.words == ()


def test_PL5_a_page_of_only_furniture_has_no_content_blocks() -> None:
    doc = build(pdf_factory.furniture_only_page())
    on_page_3 = [b.kind for b in doc.blocks if b.regions[0].page == 3]
    assert on_page_3 == ["furniture", "furniture"]
