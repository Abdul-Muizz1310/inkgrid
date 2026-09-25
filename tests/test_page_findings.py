from inkgrid.model.findings import FindingCode, Severity
from inkgrid.read.page_findings import engine_warning_findings, page_findings
from model_builders import mk_page, mk_word


def codes(**page: object) -> list[FindingCode]:
    has_image = bool(page.pop("has_image", False))
    has_curves = bool(page.pop("has_curves", False))
    found = page_findings(mk_page(**page), has_image=has_image, has_curves=has_curves)
    return [f.code for f in found]


def test_no_words_with_an_image_is_no_text_layer() -> None:
    assert codes(text_layer="none", words=(), has_image=True) == [FindingCode.NO_TEXT_LAYER]


def test_no_words_with_curves_is_no_text_layer() -> None:
    assert codes(text_layer="none", words=(), has_curves=True) == [FindingCode.NO_TEXT_LAYER]


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
        mk_page(number=4, clipped_chars=7, words=(mk_word(page=4),)),
        has_image=False,
        has_curves=False,
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
