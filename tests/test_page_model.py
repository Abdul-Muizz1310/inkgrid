from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.geometry import Rect
from inkgrid.model.page import PageModel, Reading, Rule, Source
from model_builders import READER, SHA, mk_page, mk_reading, mk_word


@pytest.mark.parametrize(
    "text",
    ["a b", "", "a\tb", "a\u00a0b", "a\u200bb", "\ue000"],
    ids=["space", "empty", "tab", "nbsp", "zwsp-cf", "private-use-co"],
)
def test_P1_word_text_rejects_whitespace_and_invisible(text: str) -> None:
    with pytest.raises(ValidationError):
        mk_word(text=text)


def test_P2b_lone_surrogate_is_rejected() -> None:
    with pytest.raises(ValidationError, match="U\\+D800"):
        mk_word(text="a\ud800")


def test_P2_replacement_character_is_legal() -> None:
    assert mk_word(text="\ufffd").text == "\ufffd"


@pytest.mark.parametrize("field", [{"size": -1.0}, {"page": 0}, {"id": -1}])
def test_P3_word_rejects_out_of_range_numbers(field: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        mk_word(**field)


@pytest.mark.parametrize("field", [{"start": 5, "end": 5}, {"axis": "x"}, {"thickness": -1}])
def test_P4_rule_rejects_bad_fields(field: dict[str, Any]) -> None:
    fields: dict[str, Any] = {
        "page": 1,
        "axis": "h",
        "at": 10,
        "start": 0,
        "end": 5,
        "thickness": 1,
    }
    fields.update(field)
    with pytest.raises(ValidationError):
        Rule(**fields)


def test_rule_measures() -> None:
    h = Rule(page=1, axis="h", at=100, start=10, end=110, thickness=2)
    v = Rule(page=1, axis="v", at=50, start=0, end=30, thickness=1)
    assert h.length == 100.0
    assert h.rect == Rect(10, 99, 110, 101)
    assert v.rect == Rect(49.5, 0, 50.5, 30)


def test_P5_page_rejects_word_from_another_page() -> None:
    with pytest.raises(ValidationError, match="page"):
        mk_page(words=(mk_word(page=2),))


def test_P5_page_rejects_rule_from_another_page() -> None:
    rule = Rule(page=2, axis="h", at=10, start=0, end=5, thickness=1)
    with pytest.raises(ValidationError, match="page"):
        mk_page(rules=(rule,))


@pytest.mark.parametrize("field", [{"rotation": 45}, {"width": 0.0}])
def test_P6_page_rejects_bad_geometry(field: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        mk_page(**field)


def test_P7_text_layer_none_requires_no_words() -> None:
    with pytest.raises(ValidationError, match="text_layer"):
        mk_page(text_layer="none")
    with pytest.raises(ValidationError, match="text_layer"):
        mk_page(text_layer="full", words=())
    assert mk_page(text_layer="none", words=()).words == ()


def test_P8_text_layer_partial_iff_unmapped() -> None:
    with pytest.raises(ValidationError, match="text_layer"):
        mk_page(text_layer="partial", unmapped_chars=0)
    with pytest.raises(ValidationError, match="text_layer"):
        mk_page(text_layer="full", unmapped_chars=3)
    assert mk_page(text_layer="partial", unmapped_chars=3).text_layer == "partial"


def test_P9_image_area_ratio_is_bounded() -> None:
    with pytest.raises(ValidationError):
        mk_page(image_area_ratio=1.5)


def test_P10_reading_page_count_must_match_source() -> None:
    with pytest.raises(ValidationError, match="pages"):
        Reading(
            source=Source(sha256=SHA, pages=2, file_name=None),
            reader=READER,
            pages=(mk_page(),),
            findings=(),
        )


def test_P11_page_numbers_run_in_order() -> None:
    with pytest.raises(ValidationError, match="number"):
        mk_reading((mk_page(), mk_page(number=3, words=(mk_word(id=1, page=3),))))
    with pytest.raises(ValidationError):
        Reading(
            source=Source(sha256=SHA, pages=1, file_name=None),
            reader=READER,
            pages=(),
            findings=(),
        )


def test_P12_word_ids_are_dense_across_pages() -> None:
    with pytest.raises(ValidationError, match="word id"):
        mk_reading((mk_page(words=(mk_word(id=0), mk_word(id=2))),))
    with pytest.raises(ValidationError, match="word id"):
        mk_reading(
            (
                mk_page(words=(mk_word(id=0), mk_word(id=1))),
                mk_page(number=2, words=(mk_word(id=0, page=2),)),
            )
        )


def test_P13_reading_findings_reference_real_pages_and_no_blocks() -> None:
    two = (mk_page(), mk_page(number=2, words=(mk_word(id=1, page=2),)))
    with pytest.raises(ValidationError, match="page"):
        mk_reading(two, (Finding.of(FindingCode.BLANK_PAGE, "x", page=5),))
    with pytest.raises(ValidationError, match="block"):
        mk_reading(two, (Finding.of(FindingCode.CALL_UNRESOLVED, "x", block="b1"),))


@pytest.mark.parametrize("sha", ["A" * 64, "0" * 63])
def test_P14_sha256_shape(sha: str) -> None:
    with pytest.raises(ValidationError):
        Source(sha256=sha, pages=1, file_name=None)


def test_reading_words_iterates_in_id_order() -> None:
    r = mk_reading(
        (
            mk_page(words=(mk_word(id=0), mk_word(id=1, text="b"))),
            mk_page(number=2, words=(mk_word(id=2, page=2, text="c"),)),
        )
    )
    assert [w.text for w in r.words()] == ["a", "b", "c"]


def test_reading_serializes_schema_key() -> None:
    assert mk_reading((mk_page(),)).model_dump_json().startswith('{"schema":"inkgrid.reading/1"')


@st.composite
def readings(draw: st.DrawFn) -> Reading:
    n_pages = draw(st.integers(min_value=1, max_value=3))
    pages: list[PageModel] = []
    next_id = 0
    for number in range(1, n_pages + 1):
        n_words = draw(st.integers(min_value=0, max_value=5))
        words = []
        for _ in range(n_words):
            x0 = draw(st.floats(0, 500, allow_nan=False))
            y0 = draw(st.floats(0, 700, allow_nan=False))
            text = draw(
                st.text(alphabet=st.characters(categories=["L", "N"]), min_size=1, max_size=8)
            )
            words.append(
                mk_word(id=next_id, page=number, bbox=Rect(x0, y0, x0 + 20, y0 + 10), text=text)
            )
            next_id += 1
        layer = "full" if words else "none"
        pages.append(mk_page(number=number, text_layer=layer, words=tuple(words)))
    return mk_reading(tuple(pages))


@given(readings())
def test_P15_reading_json_round_trip_is_canonical(reading: Reading) -> None:
    text = reading.model_dump_json()
    again = Reading.model_validate_json(text)
    assert again == reading
    assert again.model_dump_json() == text
