import pytest
from pydantic import ValidationError

from inkgrid.model.findings import SEVERITY, Finding, FindingCode, Severity

EXPECTED_ORDER = [
    "no_text_layer",
    "blank_page",
    "partial_text_layer",
    "ocr_text_layer",
    "hidden_text",
    "type3_font",
    "clipped_text",
    "overprinted_text",
    "pdf_engine_warning",
    "unreadable_page",
    "lattice_failed",
    "lattice_disagrees",
    "word_crosses_rule",
    "header_not_found",
    "table_left_as_text",
    "chart_left_as_text",
    "call_unresolved",
    "no_furniture_long_document",
]


def test_F1_every_code_has_a_severity() -> None:
    assert set(SEVERITY) == set(FindingCode)
    assert [c.value for c in FindingCode] == EXPECTED_ORDER


def test_F1_severity_table_matches_spec() -> None:
    errors = {c for c, s in SEVERITY.items() if s is Severity.ERROR}
    assert errors == {FindingCode.NO_TEXT_LAYER, FindingCode.UNREADABLE_PAGE}
    assert SEVERITY[FindingCode.HIDDEN_TEXT] is Severity.WARNING
    assert SEVERITY[FindingCode.BLANK_PAGE] is Severity.INFO
    assert SEVERITY[FindingCode("table_left_as_text")] is Severity.WARNING


def test_F2_mislabelled_severity_is_rejected() -> None:
    with pytest.raises(ValidationError, match="severity"):
        Finding(code=FindingCode.NO_TEXT_LAYER, severity=Severity.INFO, detail="x")


def test_F3_of_fills_in_the_severity() -> None:
    f = Finding.of(FindingCode.NO_TEXT_LAYER, "x", page=1)
    assert (f.severity, f.page, f.block, f.detail) == (Severity.ERROR, 1, None, "x")


def test_F4_page_zero_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Finding.of(FindingCode.BLANK_PAGE, "x", page=0)


def test_F4_unknown_code_in_json_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Finding.model_validate_json(
            '{"code":"made_up","severity":"info","page":null,"block":null,"detail":""}'
        )


def test_finding_json_round_trip() -> None:
    f = Finding.of(FindingCode.CLIPPED_TEXT, "7 characters", page=2)
    assert Finding.model_validate_json(f.model_dump_json()) == f


def test_finding_block_id_shape() -> None:
    assert Finding.of(FindingCode.CALL_UNRESOLVED, "x", block="b12").block == "b12"
    with pytest.raises(ValidationError):
        Finding.of(FindingCode.CALL_UNRESOLVED, "x", block="b0")


def test_OP1_overprinted_text_is_an_info_finding() -> None:
    f = Finding.of(FindingCode.OVERPRINTED_TEXT, "14 characters", page=1)
    assert f.severity == Severity.INFO


def test_CH1_a_chart_left_as_text_is_an_info_finding() -> None:
    f = Finding.of(FindingCode.CHART_LEFT_AS_TEXT, "a bar chart", page=1)
    assert f.severity == Severity.INFO
