import pytest

import inkgrid
import pdf_factory
from doc_builder import without_last_paragraph
from inkgrid.errors import PasswordRequired, WrongPassword


@pytest.mark.parametrize("name", pdf_factory.OPENABLE)
def test_VA1_every_fixture_verifies_with_no_defect(name: str) -> None:
    data = pdf_factory.OPENABLE[name]()
    report = inkgrid.verify(inkgrid.read(data), data)
    assert report.defects == ()
    assert report.source.sha256 == inkgrid.read_pages(data).source.sha256


def test_VA2_a_document_is_verified_only_against_its_own_pdf() -> None:
    doc = inkgrid.read(pdf_factory.simple_text())
    with pytest.raises(inkgrid.SourceMismatch, match="SHA-256") as caught:
        inkgrid.verify(doc, pdf_factory.two_column())
    assert doc.source.sha256[:16] in str(caught.value)


def test_VA3_the_document_must_be_a_document() -> None:
    with pytest.raises(TypeError, match="Document"):
        inkgrid.verify("doc", pdf_factory.simple_text())  # type: ignore[arg-type]


def test_VA4_an_encrypted_pdf_is_verified_with_its_password() -> None:
    data = pdf_factory.ruled_encrypted("u")
    doc = inkgrid.read(data, password="u")
    assert inkgrid.verify(doc, data, password="u").ok
    with pytest.raises(PasswordRequired):
        inkgrid.verify(doc, data)
    with pytest.raises(WrongPassword):
        inkgrid.verify(doc, data, password="nope")


def test_VA5_a_removed_paragraph_is_lost_on_its_page() -> None:
    data = pdf_factory.table_between_paragraphs()
    doc, text = without_last_paragraph(inkgrid.read(data))
    report = inkgrid.verify(doc, data)
    assert [(d.code.value, d.page, d.text) for d in report.defects] == [("lost", 1, text)]
    assert not report.ok


def test_RP6_a_lost_lone_surrogate_is_reported_as_json() -> None:
    data = pdf_factory.surrogate_tounicode()  # PDFium reads the A as U+D800, MuPDF as U+FFFD
    doc, _ = without_last_paragraph(inkgrid.read(data))
    report = inkgrid.verify(doc, data)
    assert [(d.code.value, d.text) for d in report.defects] == [("lost", "\ufffdB")]
    assert inkgrid.VerificationReport.model_validate_json(report.model_dump_json()) == report


@pytest.mark.parametrize(
    ("name", "statuses"),
    [
        ("nested_graphics_states", ["declared"]),
        ("count_mismatch", ["verified", "declared"]),
        ("null_second_kid", ["verified", "declared"]),
    ],
)
def test_DC12_pages_the_reader_declared_unreadable_are_declared(
    name: str, statuses: list[str]
) -> None:
    data = pdf_factory.OPENABLE[name]()
    report = inkgrid.verify(inkgrid.read(data), data)
    assert report.ok
    assert [p.status for p in report.pages] == statuses


def test_verify_is_public() -> None:
    assert "verify" in inkgrid.__all__


def test_OP6_a_shadow_drawn_five_times_verifies_clean() -> None:
    data = pdf_factory.wordart_shadow()
    doc = inkgrid.read(data)
    assert [w.text for w in doc.words] == ["Y", "a", "h", "o", "o", "!"]
    report = inkgrid.verify(doc, data)
    assert report.ok, report.defects
    assert report.pages[0].overprint_chars > 0  # PDFium kept some copies
