import contextlib

import pymupdf
import pytest

import pdf_factory
from inkgrid.errors import PasswordRequired, PdfOpenError, WrongPassword
from inkgrid.read.pymupdf_reader import read_pdf


def read(data: bytes, password: str | None = None):
    return read_pdf(data, file_name=None, password=password)


@pytest.mark.parametrize(
    "data",
    [b"hello world", pdf_factory.simple_text()[:400], b"%PDF-1.7\n"],
    ids=["not-pdf", "truncated", "header-only"],
)
def test_O1_O3_unreadable_inputs_raise_pdf_open_error(data: bytes) -> None:
    with pytest.raises(PdfOpenError, match="not a readable PDF"):
        read(data)


@pytest.mark.parametrize(
    "data",
    [b"hello world", pdf_factory.simple_text()[:400], b"%PDF-1.7\n", pdf_factory.repaired()],
    ids=["not-pdf", "truncated", "header-only", "repaired"],
)
def test_O4_reading_never_writes_to_stdout_or_stderr(
    data: bytes, capfd: pytest.CaptureFixture[str]
) -> None:
    with contextlib.suppress(PdfOpenError):
        read(data)
    assert capfd.readouterr() == ("", "")


def test_O5_user_password() -> None:
    data = pdf_factory.encrypted(user_pw="u", owner_pw="o")
    with pytest.raises(PasswordRequired):
        read(data)
    with pytest.raises(WrongPassword):
        read(data, password="nope")
    assert [w.text for w in read(data, password="u").words()] == ["secret"]


def test_O6_owner_only_encryption_opens_without_a_password() -> None:
    assert [w.text for w in read(pdf_factory.owner_only()).words()] == ["open"]


def test_O7_password_for_an_unencrypted_file_is_ignored() -> None:
    assert read(pdf_factory.simple_text(), password="whatever").source.pages == 1


def test_O8_zero_pages_is_unreadable() -> None:
    with pytest.raises(PdfOpenError, match="no pages"):
        read(pdf_factory.zero_pages())


@pytest.mark.parametrize(
    "data", [pdf_factory.repaired(), b"hello world"], ids=["repaired", "failed-open"]
)
def test_O9_mupdf_display_settings_are_restored(data: bytes) -> None:
    before = (pymupdf.TOOLS.mupdf_display_errors(), pymupdf.TOOLS.mupdf_display_warnings())
    with contextlib.suppress(PdfOpenError):
        read(data)
    after = (pymupdf.TOOLS.mupdf_display_errors(), pymupdf.TOOLS.mupdf_display_warnings())
    assert after == before


def test_O10_reading_is_deterministic() -> None:
    data = pdf_factory.ruled_table()
    assert read(data).model_dump_json() == read(data).model_dump_json()


def test_reading_reports_source_and_reader() -> None:
    data = pdf_factory.simple_text()
    reading = read_pdf(data, file_name="fees.pdf", password=None)
    assert reading.source.file_name == "fees.pdf"
    assert len(reading.source.sha256) == 64
    assert reading.reader.pymupdf == pymupdf.VersionBind
    assert [w.text for w in reading.words()] == [t for t, *_ in pdf_factory.SIMPLE_TEXT_WORDS]
