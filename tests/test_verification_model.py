import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from inkgrid.model.geometry import Rect
from inkgrid.model.page import Source
from inkgrid.model.verification import (
    Defect,
    DefectCode,
    PageCheck,
    VerificationReport,
    Verifier,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Source(sha256="0" * 64, pages=1, file_name=None)
VERIFIER = Verifier(inkgrid="0.1.0.dev0", pypdfium2="5.13.0", pdfium="153.0.7999.0")


def page(number: int = 1, **counts: Any) -> PageCheck:
    """A verified page whose 3 ink characters are all owned, with `counts` overriding."""
    fields: dict[str, Any] = {"ink_chars": 3, "owned_chars": 3} | counts
    return PageCheck(number=number, status=fields.pop("status", "verified"), **fields)


def report(
    pages: tuple[PageCheck, ...] = (),
    defects: tuple[Defect, ...] = (),
    advisories: tuple[Defect, ...] = (),
) -> VerificationReport:
    return VerificationReport(
        source=SOURCE,
        verifier=VERIFIER,
        pages=pages or (page(),),
        defects=defects,
        advisories=advisories,
    )


def lost(text: str, number: int = 1) -> Defect:
    return Defect(code=DefectCode.LOST, page=number, text=text, detail="no word owns it")


def test_RP0_a_clean_report_is_ok() -> None:
    assert report().ok
    assert not report(pages=(page(owned_chars=1, lost_chars=2),), defects=(lost("ab"),)).ok


def test_RP1_a_verified_page_accounts_for_every_ink_character() -> None:
    with pytest.raises(ValidationError, match="page 1"):
        page(ink_chars=4)
    page(ink_chars=6, lost_chars=1, outside_chars=1, clipped_chars=1)  # 3 + 1 + 1 + 1
    page(ink_chars=4, soft_hyphens=1)
    with pytest.raises(ValidationError, match="soft"):
        page(ink_chars=3, soft_hyphens=1)


def test_VO4_a_verified_page_counts_its_overprint_copies() -> None:
    page(ink_chars=5, overprint_chars=2)
    with pytest.raises(ValidationError, match="overprint"):
        page(ink_chars=3, overprint_chars=2)
    with pytest.raises(ValidationError, match="declared"):
        page(status="declared", ink_chars=5, owned_chars=0, declared_chars=5, overprint_chars=1)
    with pytest.raises(ValidationError, match="counts nothing"):
        page(status="unverified", ink_chars=0, owned_chars=0, overprint_chars=1)


def test_RP1_a_declared_page_holds_only_declared_ink() -> None:
    page(status="declared", ink_chars=5, owned_chars=0, declared_chars=5)
    with pytest.raises(ValidationError, match="declared"):
        page(status="declared", ink_chars=5, owned_chars=0, declared_chars=4)
    with pytest.raises(ValidationError, match="declared"):
        page(status="declared", ink_chars=3, owned_chars=3)
    with pytest.raises(ValidationError, match="declared"):
        page(ink_chars=4, declared_chars=1)


def test_RP1_an_unverified_page_counts_nothing() -> None:
    page(status="unverified", ink_chars=0, owned_chars=0)
    with pytest.raises(ValidationError, match="unverified"):
        page(status="unverified")


def test_RP2_lost_defects_match_the_pages_lost_count() -> None:
    with pytest.raises(ValidationError, match="lost"):
        report(pages=(page(owned_chars=0, lost_chars=3),), defects=(lost("ab"),))
    report(pages=(page(owned_chars=0, lost_chars=3),), defects=(lost("ab"), lost("c")))


def test_RP3_order_is_only_ever_an_advisory() -> None:
    order = Defect(
        code=DefectCode.ORDER, page=1, block="b1", cell=(0, 0), detail="reads BA", text="AB"
    )
    text = Defect(code=DefectCode.TEXT, page=1, block="b1", cell=(0, 0), detail="misplaced")
    report(advisories=(order,), defects=(text,))
    with pytest.raises(ValidationError, match="advisor"):
        report(defects=(order,))
    with pytest.raises(ValidationError, match="advisor"):
        report(advisories=(text,))


def test_RP4_table_codes_name_their_block_and_cell_codes_their_cell() -> None:
    with pytest.raises(ValidationError, match="cell"):
        Defect(code=DefectCode.TEXT, page=1, block="b1", detail="misplaced")
    with pytest.raises(ValidationError, match="block"):
        Defect(code=DefectCode.ORPHAN, page=1, detail="in a gap")
    for code in (DefectCode.VRULE, DefectCode.HRULE, DefectCode.ORDER):
        with pytest.raises(ValidationError, match="cell"):
            Defect(code=code, page=1, block="b1", detail="cut")
    Defect(code=DefectCode.ORPHAN, page=1, block="b1", detail="in a gap", bbox=Rect(0, 0, 1, 1))


def test_RP4_a_lost_defect_holds_its_characters() -> None:
    with pytest.raises(ValidationError, match="text"):
        lost("")


def test_RP5_unverified_defects_sit_on_unverified_pages_only() -> None:
    bad = page(status="unverified", ink_chars=0, owned_chars=0)
    unverified = Defect(code=DefectCode.UNVERIFIED, page=1, detail="PDFium cannot load it")
    report(pages=(bad,), defects=(unverified,))
    with pytest.raises(ValidationError, match="unverified"):
        report(pages=(page(),), defects=(unverified,))
    with pytest.raises(ValidationError, match="unverified"):
        report(pages=(bad,))


def test_RP5_pages_run_from_one_and_defects_name_one_of_them() -> None:
    with pytest.raises(ValidationError, match="page"):
        report(pages=(page(2),))
    with pytest.raises(ValidationError, match="page 2"):
        report(defects=(lost("a", number=2),))


def test_RP6_a_report_round_trips_through_json() -> None:
    euro = Defect(
        code=DefectCode.INVENTED, page=1, text="\u20ac\ufffd", detail="not on the page",
        bbox=Rect(1, 2, 3, 4),
    )  # fmt: skip
    rep = report(defects=(euro,))
    text = rep.model_dump_json()
    assert json.loads(text)["schema"] == "inkgrid.verification/1"
    assert VerificationReport.model_validate_json(text) == rep


def test_RP6_verification_schema_is_committed() -> None:
    spec = importlib.util.spec_from_file_location(
        "export_schemas", ROOT / "scripts" / "export_schemas.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    committed = json.loads((ROOT / "docs" / "schema" / "verification.schema.json").read_text())
    assert module.schemas()["verification.schema.json"] == committed


def test_RP7_a_decode_defect_names_its_block_and_holds_its_text() -> None:
    Defect(code=DefectCode.DECODE, page=1, block="b1", text="\u2022", detail="PDFium reads \u00ef")
    with pytest.raises(ValidationError, match="block"):
        Defect(code=DefectCode.DECODE, page=1, text="\u2022", detail="PDFium reads \u00ef")
    with pytest.raises(ValidationError, match="text"):
        Defect(code=DefectCode.DECODE, page=1, block="b1", detail="PDFium reads \u00ef")


def test_RP7_decode_sorts_between_invented_and_value() -> None:
    order = list(DefectCode)
    assert order.index(DefectCode.INVENTED) + 1 == order.index(DefectCode.DECODE)
    assert order.index(DefectCode.DECODE) + 1 == order.index(DefectCode.VALUE)


def test_RP8_only_a_verified_page_counts_ligatures_and_overlays() -> None:
    page(ligature_chars=1, overlay_chars=2)
    for field in ("ligature_chars", "overlay_chars"):
        with pytest.raises(ValidationError, match="unverified"):
            page(status="unverified", ink_chars=0, owned_chars=0, **{field: 1})
        with pytest.raises(ValidationError, match="declared"):
            page(status="declared", ink_chars=2, owned_chars=0, declared_chars=2, **{field: 1})
