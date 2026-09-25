from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

import inkgrid
import pdf_factory
from inkgrid import Document, Profile, StrictModeError
from inkgrid.read.pymupdf_reader import read_pdf


def test_A1_read_pages_reads_a_path(tmp_path: Path) -> None:
    data = pdf_factory.simple_text()
    path = tmp_path / "fees.pdf"
    path.write_bytes(data)
    reading = inkgrid.read_pages(path)
    assert reading == read_pdf(data, file_name="fees.pdf", password=None)


def test_A1_read_pages_accepts_bytes_and_a_password() -> None:
    reading = inkgrid.read_pages(pdf_factory.encrypted(user_pw="u"), password="u")
    assert [w.text for w in reading.words()] == ["secret"]
    assert reading.source.file_name is None


def test_A2_every_public_name_is_importable() -> None:
    for name in inkgrid.__all__:
        assert getattr(inkgrid, name) is not None, name


def test_A2_public_surface_is_exactly_the_spec() -> None:
    assert set(inkgrid.__all__) == {
        "__version__",
        "read",
        "read_pages",
        "Profile",
        "Lexicon",
        "InkgridError",
        "PdfOpenError",
        "PasswordRequired",
        "WrongPassword",
        "InvariantError",
        "StrictModeError",
        "Reading",
        "PageModel",
        "PageInfo",
        "Word",
        "Rule",
        "Rect",
        "Interval",
        "Finding",
        "FindingCode",
        "Severity",
        "Document",
        "Block",
        "Heading",
        "Paragraph",
        "ListItem",
        "Footnote",
        "Definition",
        "Table",
        "Furniture",
        "Grid",
        "Cell",
        "Link",
        "LinkEnd",
        "Region",
        "Ledger",
        "Producer",
    }


@pytest.mark.parametrize("name", pdf_factory.OPENABLE)
def test_RD1_read_builds_a_document_for_every_fixture(name: str) -> None:
    assert isinstance(inkgrid.read(pdf_factory.OPENABLE[name]()), Document)


def test_RD2_two_columns_read_left_then_right() -> None:
    doc = inkgrid.read(pdf_factory.two_column())
    texts = [b.text for b in doc.blocks]
    assert texts.index(" ".join(pdf_factory.TWO_COLUMN_LEFT)) < texts.index(
        " ".join(pdf_factory.TWO_COLUMN_RIGHT)
    )


def test_RD3_strict_mode_raises_on_an_error_finding() -> None:
    with pytest.raises(StrictModeError, match=r"no_text_layer on page 1"):
        inkgrid.read(pdf_factory.image_only(), strict=True)


def test_RD4_without_strict_mode_the_document_is_incomplete() -> None:
    doc = inkgrid.read(pdf_factory.image_only())
    assert doc.complete is False
    assert doc.blocks == ()


def test_RD5_an_unknown_lattice_is_a_value_error_before_reading() -> None:
    with pytest.raises(ValueError, match="lattice"):
        inkgrid.read(b"not a pdf", lattice="fast")


def test_RD6_the_producer_records_a_custom_profile() -> None:
    profile = Profile(id="custom/1", paragraph_gap_ratio=2.0)
    doc = inkgrid.read(pdf_factory.simple_text(), profile=profile)
    assert doc.producer.profile == "custom/1"
    assert doc.producer.lexicon == "generic/1"


def test_RD7_reading_is_deterministic() -> None:
    data = pdf_factory.two_column()
    assert inkgrid.read(data).model_dump_json() == inkgrid.read(data).model_dump_json()


def test_RD8_a_profile_that_skipped_validation_is_rejected_before_reading() -> None:
    bad = Profile().model_copy(update={"paragraph_gap_ratio": -1.0})
    with pytest.raises(ValidationError):
        inkgrid.read(b"not a pdf", profile=bad)


@pytest.mark.parametrize(
    "kwargs", [{"profile": {"id": "p/1"}}, {"lexicon": "generic/1"}], ids=["profile", "lexicon"]
)
def test_RD9_configuration_of_the_wrong_type_is_a_type_error(kwargs: dict[str, Any]) -> None:
    with pytest.raises(TypeError, match=r"Profile|Lexicon"):
        inkgrid.read(b"not a pdf", **kwargs)


def test_RD10_a_document_round_trips_through_json() -> None:
    doc = inkgrid.read(pdf_factory.furnished())
    assert Document.model_validate_json(doc.model_dump_json()) == doc
