import pytest

import pdf_factory
from inkgrid.errors import PdfOpenError
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


@pytest.mark.parametrize("mode", [4, 5, 6])
def test_X17_fill_and_clip_modes_read_once(mode: int) -> None:
    words = list(read(pdf_factory.render_mode(mode)).words())
    assert [(w.text, w.hidden) for w in words] == [(f"mode{mode}", False)]


def test_X18_clip_only_and_transparent_text_is_hidden() -> None:
    seven = read(pdf_factory.render_mode(7))
    assert [(w.text, w.hidden) for w in seven.words()] == [("mode7", True)]
    assert codes(seven) == [FindingCode.HIDDEN_TEXT]
    ghost = read(pdf_factory.alpha_zero())
    assert [(w.text, w.hidden) for w in ghost.words()] == [("seen", False), ("ghost", True)]
    assert codes(ghost) == [FindingCode.HIDDEN_TEXT]


def test_X19_text_outside_the_cropbox_is_counted_as_clipped() -> None:
    reading = read(pdf_factory.outside_crop())
    assert [w.text for w in reading.words()] == ["insidecrop"]
    assert reading.pages[0].clipped_chars == len("outsidecrop") + len("offpage")
    assert codes(reading) == [FindingCode.CLIPPED_TEXT]


def test_OP1_a_banner_drawn_twice_is_read_once() -> None:
    reading = read(pdf_factory.overprinted_banner())
    assert [w.text for w in reading.words()] == ["HIGHLIGHTS", "FROM", "between"]
    assert reading.pages[0].overprinted_chars == len("HIGHLIGHTSFROM")
    (finding,) = reading.findings
    assert finding.code is FindingCode.OVERPRINTED_TEXT
    assert finding.severity is Severity.INFO
    assert "14" in finding.detail


def test_OP2_text_stroked_then_filled_is_read_once() -> None:
    reading = read(pdf_factory.stroked_then_filled())
    assert [w.text for w in reading.words()] == ["PRESS"]
    assert reading.pages[0].overprinted_chars == len("PRESS")


def test_OP7_a_copy_is_never_counted_as_clipped() -> None:
    reading = read(pdf_factory.overprinted_banner())
    assert reading.pages[0].clipped_chars == 0
    assert FindingCode.CLIPPED_TEXT not in codes(reading)


def test_T31_type3_digit_glyphs_read_as_glyphs_without_unicode() -> None:
    reading = read(pdf_factory.type3_digits())
    assert [w.text for w in reading.words()] == ["t", "\ufffd", "[\ufffd,"]
    assert reading.pages[0].unmapped_chars == 2
    assert reading.pages[0].invisible_chars == 0


def test_GN1_a_dingbats_glyph_name_reads_by_the_dingbats_list() -> None:
    reading = read(pdf_factory.glyph_named(b"ABCDEF+ZapfDingbatsITC", 3, b"a71"))
    assert [w.text for w in reading.words()] == ["\u25cf", "after"]
    assert reading.pages[0].unmapped_chars == 0


def test_GN2_a_digit_glyph_name_elsewhere_reads_as_no_unicode() -> None:
    reading = read(pdf_factory.glyph_named(b"ABCDEF+LASY10", 50, b"a50"))
    assert [w.text for w in reading.words()] == ["\ufffd", "after"]
    assert reading.pages[0].unmapped_chars == 1


def test_X20_type3_font_is_reported() -> None:
    reading = read(pdf_factory.type3_font())
    assert [w.text for w in reading.words()] == ["aaa", "plain"]
    (finding,) = reading.findings
    assert finding.code is FindingCode.TYPE3_FONT
    assert finding.page == 1
    assert "3" in finding.detail


def test_X21_page_tree_declaring_missing_pages() -> None:
    reading = read(pdf_factory.count_mismatch())
    assert reading.source.pages == 1
    assert [w.text for w in reading.words()] == ["AB"]
    unreadable = [f for f in reading.findings if f.code is FindingCode.UNREADABLE_PAGE]
    assert len(unreadable) == 1
    assert unreadable[0].severity is Severity.ERROR
    assert unreadable[0].page is None
    assert "1 of 2" in unreadable[0].detail


def test_X22_undecodable_content_is_not_a_blank_page() -> None:
    reading = read(pdf_factory.broken_flate())
    assert reading.pages[0].words == ()
    found = codes(reading)
    assert FindingCode.NO_TEXT_LAYER in found
    assert FindingCode.BLANK_PAGE not in found
    engine = [f for f in reading.findings if f.code is FindingCode.PDF_ENGINE_WARNING]
    assert engine
    assert all(f.page == 1 for f in engine)


def test_X23_lone_surrogate_mapping_reads_as_replacement_character() -> None:
    reading = read(pdf_factory.surrogate_tounicode())
    assert [w.text for w in reading.words()] == ["\ufffdB"]
    assert reading.pages[0].text_layer == "partial"
    assert codes(reading) == [FindingCode.PARTIAL_TEXT_LAYER]
    reading.model_dump_json()


def test_X25_page_whose_extraction_fails_is_unreadable_not_blank() -> None:
    reading = read(pdf_factory.nested_graphics_states())
    assert len(reading.pages) == 1
    assert reading.pages[0].words == ()
    unreadable = [f for f in reading.findings if f.code is FindingCode.UNREADABLE_PAGE]
    assert [(f.page, f.severity) for f in unreadable] == [(1, Severity.ERROR)]
    assert "nested graphics states" in unreadable[0].detail
    found = codes(reading)
    assert FindingCode.NO_TEXT_LAYER in found
    assert FindingCode.BLANK_PAGE not in found


def test_X26_page_tree_where_no_page_loads_is_not_a_pdf() -> None:
    with pytest.raises(PdfOpenError, match="none of its 1 declared pages"):
        read(pdf_factory.null_page_kid())


def test_X27_page_that_cannot_load_ends_the_reading() -> None:
    reading = read(pdf_factory.null_second_kid())
    assert reading.source.pages == 1
    assert [w.text for w in reading.words()] == ["AB"]
    unreadable = [f for f in reading.findings if f.code is FindingCode.UNREADABLE_PAGE]
    assert [(f.page, f.severity) for f in unreadable] == [(None, Severity.ERROR)]
    assert "1 of 2" in unreadable[0].detail


@pytest.mark.parametrize("name", pdf_factory.OPENABLE)
def test_X24_every_reading_round_trips_through_json(name: str) -> None:
    reading = read(pdf_factory.OPENABLE[name]())
    text = reading.model_dump_json()
    assert Reading.model_validate_json(text) == reading
