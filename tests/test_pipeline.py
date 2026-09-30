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


def test_PB15_reader_boxes_keep_paragraph_breaks() -> None:
    doc = build(pdf_factory.spaced_paragraphs())
    for page, paragraphs in enumerate(pdf_factory.SPACED_PARAGRAPHS, 1):
        expected = [" ".join(p) for p in paragraphs]
        blocks = [b for b in doc.blocks if b.regions[0].page == page]
        assert [(b.kind, b.text) for b in blocks] == [("paragraph", t) for t in expected]


def test_PL6_a_landscape_page_reads_as_the_reader_sees_it() -> None:
    doc = build(pdf_factory.landscape())
    assert content(doc) == [
        ("heading", pdf_factory.LANDSCAPE_TITLE),
        *(("paragraph", " ".join(p)) for p in pdf_factory.LANDSCAPE_PARAGRAPHS),
    ]
    by_id = {w.id: w for w in doc.words}
    for block in doc.blocks:
        assert all(block.regions[0].bbox.contains_rect(by_id[w].bbox) for w in block.word_ids)


def test_PL7_sideways_text_keeps_the_unrotated_frame() -> None:
    doc = build(pdf_factory.rotated())
    assert content(doc) == [("paragraph", "Rotated")]


def test_MK1_a_marked_value_keeps_its_mark_on_its_row() -> None:
    doc = build(pdf_factory.marked_value())
    by_text = {w.text: w.id for w in doc.words}
    (home,) = [b for b in doc.blocks if by_text[".54"] in b.word_ids]
    ids = list(home.word_ids)
    assert ids.index(by_text["*"]) == ids.index(by_text[".54"]) + 1
    assert {b.kind for b in doc.blocks} == {"paragraph"}


def furniture(doc: Document) -> list[tuple[int, str]]:
    return [(b.regions[0].page, b.text) for b in doc.blocks if b.kind == "furniture"]


def test_FT2_a_stub_banner_below_a_column_header_is_not_furniture() -> None:
    doc = build(pdf_factory.stub_banner_pages())
    assert furniture(doc) == [
        (n, text) for n in (1, 2, 3) for text in ("Acme Statistics", f"Page {n}")
    ]
    assert sum(1 for b in doc.blocks if "Actual" in b.text) == 3


def test_FT3_a_footer_above_a_mirrored_line_is_furniture() -> None:
    doc = build(pdf_factory.mirrored_footer_pages())
    assert furniture(doc) == [(1, "ECB"), (2, "ECB")]
