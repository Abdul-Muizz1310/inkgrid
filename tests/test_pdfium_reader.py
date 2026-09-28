import pytest

import inkgrid
import pdf_factory
from inkgrid.errors import PasswordRequired, WrongPassword
from inkgrid.model.page import Reading
from inkgrid.verify.ink import InkPage
from inkgrid.verify.pdfium_reader import read_ink


def ink_centres_in_words(data: bytes) -> list[str]:
    """Every ink character whose centre no word of the reader's reading contains."""
    reading: Reading = inkgrid.read_pages(data)
    ink = read_ink(data, None)
    stray = []
    for page, words in zip(ink.pages, reading.pages, strict=True):
        for ch in page.chars:
            if not ch.is_ink:
                continue
            x, y = ch.center
            if not any(
                w.bbox.x0 <= x < w.bbox.x1 and w.bbox.y0 <= y < w.bbox.y1 for w in words.words
            ):
                stray.append(f"page {page.number} {ch.char!r} at {ch.box}")
    return stray


@pytest.mark.parametrize(
    "name", ["simple_text", "offset_mediabox", "cropbox", "rotated", "landscape"]
)
def test_VR1_VR2_VR3_ink_sits_in_the_readers_words_in_the_same_frame(name: str) -> None:
    data = pdf_factory.OPENABLE[name]()
    assert read_ink(data, None).pages[0].chars
    assert ink_centres_in_words(data) == []


def test_VR2_a_cropbox_sets_the_frame_size() -> None:
    (page,) = read_ink(pdf_factory.cropbox(), None).pages
    assert (page.width, page.height) == (500.0, 700.0)


def test_VR6_a_clip_path_hides_its_characters() -> None:
    (page,) = read_ink(pdf_factory.clipped_text(), None).pages
    ink = [ch for ch in page.chars if ch.is_ink]
    assert "".join(ch.char for ch in ink if ch.clipped) == "clipped"
    assert "".join(ch.char for ch in ink if not ch.clipped) == "inside"


@pytest.mark.parametrize("nested", [False, True], ids=["page", "parent-form"])
def test_VR16_a_clip_around_a_form_hides_the_forms_text(nested: bool) -> None:
    data = pdf_factory.form_clipped(nested=nested)
    reading = inkgrid.read_pages(data)
    assert [w.text for w in reading.words()] == ["Shown"]  # MuPDF drops what the clip hides
    assert reading.pages[0].clipped_chars == len("Hidden")
    (page,) = read_ink(data, None).pages
    ink = [ch for ch in page.chars if ch.is_ink]
    assert "".join(ch.char for ch in ink if ch.clipped) == "Hidden"
    assert "".join(ch.char for ch in ink if not ch.clipped) == "Shown"


def test_VR17_a_clip_inside_a_scaled_form_is_mapped_through_the_forms_matrix() -> None:
    data = pdf_factory.scaled_form_clipped()
    reading = inkgrid.read_pages(data)
    assert [w.text for w in reading.words()] == ["Inside"]
    assert reading.pages[0].clipped_chars == len("Outside")
    (page,) = read_ink(data, None).pages
    ink = [ch for ch in page.chars if ch.is_ink]
    assert "".join(ch.char for ch in ink if not ch.clipped) == "Inside"
    assert "".join(ch.char for ch in ink if ch.clipped) == "Outside"


def test_VR7_characters_beyond_the_cropbox_are_outside() -> None:
    (page,) = read_ink(pdf_factory.outside_crop(), None).pages
    assert sum(1 for ch in page.chars if ch.is_ink and page.outside(ch)) == 18


def covered(data: bytes) -> list[str]:
    """Every reader rule no verifier rule covers: same axis, `at` within 1, extent within 1."""
    reading = inkgrid.read_pages(data)
    ink = read_ink(data, None)
    return [
        f"{rule.axis} at {rule.at} from {rule.start} to {rule.end}"
        for page, ink_page in zip(reading.pages, ink.pages, strict=True)
        for rule in page.rules
        if not any(
            v.axis == rule.axis
            and abs(v.at - rule.at) <= 1.0
            and v.start <= rule.start + 1.0
            and v.end >= rule.end - 1.0
            for v in ink_page.rules
        )
    ]


def test_VR8_the_verifier_sees_every_rule_the_reader_sees() -> None:
    data = pdf_factory.ruled_grid()
    assert read_ink(data, None).pages[0].rules
    assert covered(data) == []


def test_VR12_rules_inside_a_form_xobject_have_its_matrix_applied() -> None:
    data = pdf_factory.formed_rules()
    rules = read_ink(data, None).pages[0].rules
    assert rules
    assert all(100 - 1 <= r.at <= 496 + 1 for r in rules)  # the form sits in (100, 100, 406, 496)
    assert covered(data) == []


def test_VR13_an_encrypted_pdf_needs_its_password() -> None:
    data = pdf_factory.ruled_encrypted("u")
    assert read_ink(data, "u").pages[0].chars
    with pytest.raises(PasswordRequired):
        read_ink(data, None)
    with pytest.raises(WrongPassword):
        read_ink(data, "nope")


def test_VR14_a_page_pdfium_cannot_load_carries_its_error() -> None:
    first, second = read_ink(pdf_factory.null_second_kid(), None).pages
    assert first.error is None
    assert first.chars
    assert second == InkPage(2, 0.0, 0.0, error=second.error)
    assert second.error


def test_VR15_bytes_that_are_not_a_pdf_give_no_pages() -> None:
    ink = read_ink(b"not a pdf at all", None)
    assert ink.pages == ()
    assert ink.error


def test_versions_are_recorded() -> None:
    ink = read_ink(pdf_factory.simple_text(), None)
    assert ink.pypdfium2.startswith("5.")
    assert ink.pdfium.count(".") == 3
