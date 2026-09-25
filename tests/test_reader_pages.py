import pytest

import pdf_factory
from inkgrid.model.findings import FindingCode, Severity
from inkgrid.model.page import Reading
from inkgrid.read.pymupdf_reader import read_pdf


def read(data: bytes) -> Reading:
    return read_pdf(data, file_name=None, password=None)


def codes(reading: Reading) -> list[FindingCode]:
    return [f.code for f in reading.findings]


def test_X1_words_carry_font_signals() -> None:
    words = list(read(pdf_factory.simple_text()).words())
    assert [(w.text, w.bold, w.italic, w.size) for w in words] == pdf_factory.SIMPLE_TEXT_WORDS
    assert all(w.horizontal and not w.hidden and not w.superscript for w in words)


def test_X2_superscript_marker_is_split_from_its_value() -> None:
    words = list(read(pdf_factory.superscript()).words())
    assert [(w.text, w.superscript) for w in words] == [("$0.40", False), ("2", True)]


def test_X3_font_change_mid_word_is_one_word() -> None:
    words = list(read(pdf_factory.font_change()).words())
    assert [w.text for w in words] == ["Transaction"]


def test_X4_render_mode_3_text_is_hidden_and_reported() -> None:
    reading = read(pdf_factory.hidden_text())
    words = list(reading.words())
    assert [(w.text, w.hidden) for w in words] == [
        ("visible", False),
        ("ignore", True),
        ("previous", True),
        ("instructions", True),
    ]
    assert reading.pages[0].hidden_chars == len("ignorepreviousinstructions")
    assert codes(reading) == [FindingCode.HIDDEN_TEXT]


def test_X5_invisible_text_over_a_page_image_is_an_ocr_layer() -> None:
    reading = read(pdf_factory.ocr_layer())
    assert reading.pages[0].image_area_ratio == pytest.approx(1.0)
    assert codes(reading) == [FindingCode.OCR_TEXT_LAYER]


def test_X6_image_only_page_has_no_text_layer() -> None:
    reading = read(pdf_factory.image_only())
    page = reading.pages[0]
    assert (page.words, page.text_layer) == ((), "none")
    assert page.image_area_ratio == pytest.approx(328 * 328 / (612 * 792), abs=1e-3)
    assert codes(reading) == [FindingCode.NO_TEXT_LAYER]
    assert reading.findings[0].severity is Severity.ERROR


def test_X7_empty_page_is_blank() -> None:
    assert codes(read(pdf_factory.blank())) == [FindingCode.BLANK_PAGE]


def test_X8_page_with_only_a_line_is_blank() -> None:
    reading = read(pdf_factory.line_only())
    assert codes(reading) == [FindingCode.BLANK_PAGE]
    assert len(reading.pages[0].rules) == 1


def test_X9_clipped_text_is_counted_not_read() -> None:
    reading = read(pdf_factory.clipped_text())
    assert [w.text for w in reading.words()] == ["inside"]
    assert reading.pages[0].clipped_chars == len("clipped")
    assert codes(reading) == [FindingCode.CLIPPED_TEXT]


def test_X10_unmapped_glyphs_are_a_partial_text_layer() -> None:
    reading = read(pdf_factory.unmapped_glyph())
    assert [w.text for w in reading.words()] == ["\ufffd\ufffdC"]
    assert (reading.pages[0].text_layer, reading.pages[0].unmapped_chars) == ("partial", 2)
    assert codes(reading) == [FindingCode.PARTIAL_TEXT_LAYER]


def test_X11_drawn_table_gives_exactly_its_rules() -> None:
    assert read(pdf_factory.ruled_table()).pages[0].rules == pdf_factory.RULED_TABLE_RULES


def test_X12_rotated_page_keeps_unrotated_geometry() -> None:
    page = read(pdf_factory.rotated()).pages[0]
    assert (page.width, page.height, page.rotation) == (612.0, 792.0, 90)
    assert page.words[0].bbox.x0 == 72.0


def test_X13_offset_mediabox_is_measured_from_its_corner() -> None:
    page = read(pdf_factory.offset_mediabox()).pages[0]
    assert (page.width, page.height) == (612.0, 792.0)
    assert page.words[0].text == "Offset"
    assert page.words[0].bbox.x0 == 172.0


def test_X14_cropbox_sets_size_and_origin() -> None:
    page = read(pdf_factory.cropbox()).pages[0]
    assert (page.width, page.height) == (500.0, 700.0)
    assert page.words[0].bbox.x0 == 50.0


def test_X15_word_ids_run_densely_across_pages() -> None:
    reading = read(pdf_factory.multipage(3))
    assert reading.source.pages == 3
    assert [(w.id, w.page, w.text) for w in reading.words()] == [
        (0, 1, "page"),
        (1, 1, "1"),
        (2, 2, "page"),
        (3, 2, "2"),
        (4, 3, "page"),
        (5, 3, "3"),
    ]


def test_X16_repaired_file_reads_with_engine_warnings() -> None:
    reading = read(pdf_factory.repaired())
    assert [w.text for w in reading.words()][:2] == ["Fee", "Schedule"]
    warnings = [f for f in reading.findings if f.code is FindingCode.PDF_ENGINE_WARNING]
    assert warnings
    assert any("repair" in f.detail for f in warnings)


def test_clean_page_has_no_findings() -> None:
    assert read(pdf_factory.simple_text()).findings == ()
