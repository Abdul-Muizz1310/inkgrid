from collections.abc import Sequence

from doc_builder import B, C, W, build
from ink_builder import edited, ink_of, page, stray
from inkgrid.model.document import Document
from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.verification import VerificationReport
from inkgrid.verify.ink import Ink, InkPage
from inkgrid.verify.report import verify_document

VERSION = "0.1.0.dev0"


def ink(*pages: InkPage, error: str | None = None) -> Ink:
    return Ink(pages=pages, pypdfium2="5.13.0", pdfium="153.0.7999.0", error=error)


def verify(doc: Document, *pages: InkPage, error: str | None = None) -> VerificationReport:
    return verify_document(doc, ink(*pages, error=error), inkgrid_version=VERSION)


def codes(report: VerificationReport) -> list[tuple[str, int]]:
    return [(d.code.value, d.page) for d in report.defects]


def unreadable(page: int | None) -> Finding:
    return Finding.of(FindingCode.UNREADABLE_PAGE, "cannot read it", page=page)


PARA = B("paragraph", [W("Fees", 72, 100), W("apply", 97, 100)])


def test_a_document_verified_against_its_own_ink_is_ok() -> None:
    doc = build([PARA])
    report = verify(doc, ink_of(doc))
    assert report.ok
    (check,) = report.pages
    assert (check.status, check.ink_chars, check.owned_chars) == ("verified", 9, 9)
    assert report.verifier.pdfium == "153.0.7999.0"
    assert report.source == doc.source


def test_lost_invented_and_doubled_become_defects_with_their_block() -> None:
    doc = build([PARA])
    broken = edited(ink_of(doc), lambda cs: [*cs[1:], *stray("xy", 300, 300)])
    report = verify(doc, broken)
    assert [(d.code.value, d.text, d.block) for d in report.defects] == [
        ("lost", "xy", None),
        ("invented", "F", "b1"),
    ]
    assert report.pages[0].lost_chars == 2
    assert "'x y'" not in report.defects[0].detail


def test_a_lost_run_quotes_its_spaces_in_the_detail() -> None:
    doc = build([PARA])
    run = [*stray("ab", 300, 300), *stray(" ", 310, 300, kind="space"), *stray("cd", 315, 300)]
    report = verify(doc, edited(ink_of(doc), lambda cs: [*cs, *run]))
    (defect,) = report.defects
    assert defect.text == "abcd"
    assert "'ab cd'" in defect.detail


def test_DC8_a_page_the_reader_declared_unreadable_is_declared() -> None:
    doc = build([PARA], pages=2, findings=[unreadable(2)])
    second = page(stray("lost", 72, 100), number=2)
    report = verify(doc, ink_of(doc), second)
    assert report.ok
    assert (report.pages[1].status, report.pages[1].declared_chars) == ("declared", 4)


def test_DC9_a_document_page_pdfium_cannot_load_or_count_is_unverified() -> None:
    doc = build([PARA], pages=2)
    failed = InkPage(2, 0.0, 0.0, error="Failed to load page.")
    assert codes(verify(doc, ink_of(doc), failed)) == [("unverified", 2)]
    assert codes(verify(doc, ink_of(doc))) == [("unverified", 2)]
    report = verify(doc, error="Failed to load document")
    assert codes(report) == [("unverified", 1), ("unverified", 2)]
    assert "Failed to load document" in report.defects[0].detail


def test_DC10_an_extra_pdfium_page_is_lost_unless_declared() -> None:
    doc = build([PARA])
    extra = page(stray("more", 72, 100), number=2)
    report = verify(doc, ink_of(doc), extra)
    assert [(d.code.value, d.page, d.text) for d in report.defects] == [("lost", 2, "more")]
    declared = build([PARA], findings=[unreadable(None)])
    report = verify(declared, ink_of(declared), extra)
    assert report.ok
    assert report.pages[1].status == "declared"


def test_DC10_an_extra_page_pdfium_cannot_load_is_unverified_unless_declared() -> None:
    doc = build([PARA])
    failed = InkPage(2, 0.0, 0.0, error="Failed to load page.")
    assert codes(verify(doc, ink_of(doc), failed)) == [("unverified", 2)]
    declared = build([PARA], findings=[unreadable(None)])
    assert verify(declared, ink_of(declared), failed).ok


def test_DC11_a_page_whose_size_the_engines_disagree_on_is_unverified() -> None:
    doc = build([PARA])
    narrow = page(ink_of(doc).chars, width=611.0)
    report = verify(doc, narrow)
    assert codes(report) == [("unverified", 1)]
    assert "612" in report.defects[0].detail
    assert codes(verify(doc, page(ink_of(doc).chars, width=611.6))) == []


def table_doc() -> Document:
    """A 1 x 2 table whose `Charge` overflows two characters into the next cell."""
    table = B(
        "table",
        [W("Charge", 140, 205), W("Rate", 225, 205)],
        row_bands=[(200, 220)],
        col_bands=[(100, 160), (160, 220), (220, 280)],
        cells=[C(0, 0, [0]), C(0, 1, []), C(0, 2, [1])],
    )
    return build([table, PARA])


def test_tables_are_checked_on_their_page() -> None:
    doc = table_doc()
    report = verify(doc, ink_of(doc))
    assert report.ok
    assert report.pages[0].overflow_chars == 2


def test_values_are_checked_on_their_page() -> None:
    doc = build([B("paragraph", [W("2", 100, 100)]), B("paragraph", [W("7", 105, 100)])])
    ink = ink_of(doc)
    space = next(ch.index for ch in ink.chars if ch.kind == "generated")
    glued = edited(ink, lambda cs: [c for c in cs if c.index != space])
    assert [(d.code.value, d.text) for d in verify(doc, glued).defects] == [("value", "27")]


def test_defects_are_ordered_by_page_then_code() -> None:
    doc = build([PARA], pages=2)
    first = edited(ink_of(doc), lambda cs: [*cs[1:], *stray("x", 300, 300)])
    report = verify(doc, first)
    assert [(d.page, d.code.value) for d in report.defects] == [
        (1, "lost"),
        (1, "invented"),
        (2, "unverified"),
    ]


def test_RP6_an_assembled_report_round_trips_through_json() -> None:
    doc = build([B("paragraph", [W("\u20ac5", 72, 100), W("\ufffdB", 92, 100)])])
    broken = edited(ink_of(doc), lambda cs: cs[1:])
    report = verify(doc, broken)
    assert [d.text for d in report.defects] == ["\u20ac"]
    assert VerificationReport.model_validate_json(report.model_dump_json()) == report


def pages_of(report: VerificationReport) -> Sequence[str]:
    return [p.status for p in report.pages]


def test_every_page_either_engine_counts_is_reported() -> None:
    doc = build([PARA], pages=2)
    assert pages_of(verify(doc, ink_of(doc))) == ["verified", "unverified"]
