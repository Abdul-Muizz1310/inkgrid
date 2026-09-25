from inkgrid.model.findings import FindingCode, Severity
from inkgrid.read.page_findings import PageSignals, engine_warning_findings, page_findings
from model_builders import mk_page, mk_word


def codes(signals: PageSignals | None = None, **page: object) -> list[FindingCode]:
    found = page_findings(mk_page(**page), signals or PageSignals())
    return [f.code for f in found]


def test_no_words_with_an_image_is_no_text_layer() -> None:
    assert codes(PageSignals(has_image=True), text_layer="none", words=()) == [
        FindingCode.NO_TEXT_LAYER
    ]


def test_no_words_with_curves_is_no_text_layer() -> None:
    assert codes(PageSignals(has_curves=True), text_layer="none", words=()) == [
        FindingCode.NO_TEXT_LAYER
    ]


def test_no_words_and_nothing_drawn_is_blank() -> None:
    assert codes(text_layer="none", words=()) == [FindingCode.BLANK_PAGE]


def test_unmapped_characters_are_a_partial_text_layer() -> None:
    assert codes(text_layer="partial", unmapped_chars=2) == [FindingCode.PARTIAL_TEXT_LAYER]


def test_mostly_hidden_text_over_an_image_is_an_ocr_layer() -> None:
    words = (mk_word(text="abcdef", hidden=True), mk_word(id=1, text="abcd"))
    found = codes(words=words, hidden_chars=6, image_area_ratio=0.9)
    assert found == [FindingCode.OCR_TEXT_LAYER]


def test_hidden_text_without_a_big_image_is_hidden_text() -> None:
    words = (mk_word(text="abcdef", hidden=True), mk_word(id=1, text="abcd"))
    assert codes(words=words, hidden_chars=6, image_area_ratio=0.2) == [FindingCode.HIDDEN_TEXT]


def test_a_little_hidden_text_over_an_image_is_hidden_text() -> None:
    words = (mk_word(text="ab", hidden=True), mk_word(id=1, text="abcdefgh"))
    assert codes(words=words, hidden_chars=2, image_area_ratio=0.9) == [FindingCode.HIDDEN_TEXT]


def test_clipped_characters_are_reported() -> None:
    assert codes(clipped_chars=7) == [FindingCode.CLIPPED_TEXT]


def test_findings_come_in_the_fixed_order() -> None:
    words = (mk_word(text="\ufffdb", hidden=True),)
    found = codes(
        text_layer="partial", words=words, unmapped_chars=1, hidden_chars=2, clipped_chars=3
    )
    assert found == [
        FindingCode.PARTIAL_TEXT_LAYER,
        FindingCode.HIDDEN_TEXT,
        FindingCode.CLIPPED_TEXT,
    ]


def test_findings_name_their_page_and_count() -> None:
    (finding,) = page_findings(
        mk_page(number=4, clipped_chars=7, words=(mk_word(page=4),)), PageSignals()
    )
    assert (finding.page, finding.severity) == (4, Severity.INFO)
    assert "7" in finding.detail


def test_a_clean_page_has_no_findings() -> None:
    assert codes() == []


def test_engine_warnings_are_distinct_and_capped() -> None:
    lines = [f"warning {i}" for i in range(25)] + ["warning 3", "  ", ""]
    found = engine_warning_findings(lines)
    assert len(found) == 21
    assert [f.detail for f in found[:3]] == ["warning 0", "warning 1", "warning 2"]
    assert "5 more" in found[-1].detail
    assert {f.code for f in found} == {FindingCode.PDF_ENGINE_WARNING}
    assert all(f.page is None for f in found)


def test_no_engine_warnings_no_findings() -> None:
    assert engine_warning_findings([]) == ()


def test_no_words_but_engine_warnings_is_no_text_layer_not_blank() -> None:
    signals = PageSignals(warnings=("library error: zlib error: invalid code lengths set",))
    found = page_findings(mk_page(text_layer="none", words=()), signals)
    assert [f.code for f in found] == [FindingCode.NO_TEXT_LAYER, FindingCode.PDF_ENGINE_WARNING]
    assert all(f.page == 1 for f in found)


def test_extraction_failure_is_an_unreadable_page() -> None:
    signals = PageSignals(extraction_error="RuntimeError: cannot parse content")
    found = page_findings(mk_page(text_layer="none", words=()), signals)
    assert [f.code for f in found] == [FindingCode.UNREADABLE_PAGE, FindingCode.NO_TEXT_LAYER]
    assert found[0].severity is Severity.ERROR
    assert "cannot parse content" in found[0].detail


def test_type3_characters_are_reported_with_their_count() -> None:
    (finding,) = page_findings(mk_page(), PageSignals(type3_chars=3))
    assert finding.code is FindingCode.TYPE3_FONT
    assert "3" in finding.detail


def test_page_engine_warnings_are_pinned_to_the_page() -> None:
    found = page_findings(
        mk_page(number=2, words=(mk_word(page=2),)), PageSignals(warnings=("w1", "w1", "w2"))
    )
    assert [(f.code, f.page, f.detail) for f in found] == [
        (FindingCode.PDF_ENGINE_WARNING, 2, "w1"),
        (FindingCode.PDF_ENGINE_WARNING, 2, "w2"),
    ]
