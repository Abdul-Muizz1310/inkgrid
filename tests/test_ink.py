import pytest

from inkgrid.model.geometry import Rect
from inkgrid.verify.ink import InkChar, InkPage, char_kind, in_polygon, join_surrogates

SQUARE = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))


def kind(code: int, *, generated: bool = False, hyphen: bool = False, map_error: bool = False):
    return char_kind(code, generated=generated, hyphen=hyphen, map_error=map_error)


def test_VR4_generated_characters_hyphens_and_spaces() -> None:
    assert kind(0x20, generated=True)[0] == "generated"
    assert kind(0x0A, generated=True)[0] == "generated"
    assert kind(0x02) == ("hyphen", "-")
    assert kind(ord("-"), hyphen=True) == ("hyphen", "-")
    assert kind(0x20) == ("space", " ")
    assert kind(0xA0) == ("space", "\u00a0")


def test_VR5_invisible_unmapped_and_ink() -> None:
    for code in (0x200B, 0x00AD, 0xE000, 0x0007):
        assert kind(code)[0] == "invisible", hex(code)
    assert kind(0xFFFD) == ("unmapped", "\ufffd")
    assert kind(0xD800) == ("unmapped", "\ufffd")  # a lone surrogate cannot be written as JSON
    assert kind(ord("A"), map_error=True) == ("unmapped", "A")
    assert kind(ord("A")) == ("ink", "A")


def test_VR5_a_code_point_past_unicode_is_unmapped() -> None:
    assert kind(0x110000) == ("unmapped", "\ufffd")


def test_VR5_only_ink_hyphens_and_unmapped_characters_are_ink() -> None:
    box = Rect(0, 0, 5, 10)
    kinds = {k: InkChar(0, "x", box, k).is_ink for k in ("ink", "hyphen", "unmapped")}
    assert kinds == {"ink": True, "hyphen": True, "unmapped": True}
    for k in ("space", "generated", "invisible"):
        assert not InkChar(0, " ", box, k).is_ink


def test_in_polygon_half_open_edges() -> None:
    assert in_polygon(SQUARE, 5, 5)
    assert not in_polygon(SQUARE, 15, 5)
    assert in_polygon(SQUARE, 0, 5)  # the left edge is inside
    assert not in_polygon(SQUARE, 10, 5)  # the right edge is outside


def test_in_polygon_concave() -> None:
    ell = ((0.0, 0.0), (10.0, 0.0), (10.0, 4.0), (4.0, 4.0), (4.0, 10.0), (0.0, 10.0))
    assert in_polygon(ell, 2, 8)
    assert not in_polygon(ell, 8, 8)


def test_in_polygon_needs_three_points() -> None:
    assert not in_polygon(((0.0, 0.0), (10.0, 10.0)), 5, 5)


def test_outside_the_frame_is_half_open() -> None:
    page = InkPage(number=1, width=100, height=50)
    at = [
        InkChar(0, "a", Rect(x - 1, y - 1, x + 1, y + 1), "ink")
        for x, y in ((0, 0), (100, 10), (99, 49), (-2, 10))
    ]
    assert [page.outside(ch) for ch in at] == [False, True, False, True]


def test_an_error_page_holds_nothing() -> None:
    with pytest.raises(ValueError, match="error"):
        InkPage(1, 10, 10, chars=(InkChar(0, "a", Rect(0, 0, 1, 1), "ink"),), error="no")


def test_CK1_map_errors_nul_and_c1_controls_are_unmapped() -> None:
    for code in (0x1F, 0x1C):
        assert kind(code, map_error=True) == ("unmapped", chr(code))
    for code in (0x83, 0x92, 0x00):
        assert kind(code)[0] == "unmapped", hex(code)
    assert kind(ord("A"), map_error=True) == ("unmapped", "A")


def test_CK2_spaces_c0_controls_and_line_end_hyphens() -> None:
    assert kind(0x20, map_error=True)[0] == "space"
    assert kind(0x09)[0] == "space"
    assert kind(0x1C)[0] == "space"
    assert kind(0x07)[0] == "invisible"
    assert kind(0x02, map_error=True)[0] == "unmapped"
    assert kind(0x02) == ("hyphen", "-")


def test_CK3_a_surrogate_pair_is_one_character() -> None:
    assert join_surrogates([(3, 0x41), (4, 0xD835), (5, 0xDC51), (6, 0x42)]) == [
        (3, 3, 0x41),
        (4, 5, 0x1D451),
        (6, 6, 0x42),
    ]
    assert kind(0x1D451) == ("ink", "\U0001d451")


def test_CK4_a_surrogate_without_its_partner_stays_unmapped() -> None:
    assert join_surrogates([(4, 0xD835), (5, 0x41)]) == [(4, 4, 0xD835), (5, 5, 0x41)]
    assert join_surrogates([(9, 0xD835)]) == [(9, 9, 0xD835)]  # the page's last character
    assert join_surrogates([(4, 0xDC51), (5, 0xD835)]) == [(4, 4, 0xDC51), (5, 5, 0xD835)]
    assert kind(0xD835) == ("unmapped", "�")
