from typing import Any

import pytest
from pydantic import ValidationError

from inkgrid.model.config import Lexicon, Profile

SPEC_DEFAULTS = {
    "line_overlap": 0.5,
    "fragment_gap_em": 1.0,
    "gutter_min_em": 1.0,
    "column_min_lines": 3,
    "prose_min_words": 4.0,
    "paragraph_gap_ratio": 1.75,
    "paragraph_gap_floor": 2.0,
    "size_change_ratio": 0.1,
    "heading_size_ratio": 1.1,
    "heading_max_words": 15,
    "heading_max_lines": 2,
    "footnote_size_ratio": 0.9,
    "furniture_share": 0.4,
    "furniture_band": 0.1,
    "furniture_x_tol": 3.0,
    "long_document_pages": 8,
}
SPEC_BULLETS = (
    "\u2022",
    "\u25aa",
    "\u25e6",
    "\u25a0",
    "\u25a1",
    "\u25cf",
    "\u25cb",
    "\u2023",
    "\u2043",
    "\u2219",
    "\u00b7",
    "\u2013",
    "\u2014",
    "-",
    "*",
)


def test_CF1_defaults_carry_the_default_ids() -> None:
    assert Profile().id == "default/1"
    assert Lexicon().id == "generic/1"
    assert Profile.default() == Profile()
    assert Lexicon.default() == Lexicon()
    assert Profile().model_dump(exclude={"id"}) == SPEC_DEFAULTS
    assert Lexicon().bullets == SPEC_BULLETS


@pytest.mark.parametrize(
    "change",
    [
        {"paragraph_gap_ratio": 0.0},
        {"furniture_share": 1.5},
        {"line_overlap": 1.0},
        {"column_min_lines": 0},
    ],
)
def test_CF2_out_of_range_values_are_rejected(change: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Profile(id="custom/1", **change)


def test_CF3_a_changed_configuration_needs_a_new_id() -> None:
    with pytest.raises(ValidationError, match="default/1"):
        Profile(paragraph_gap_ratio=2.0)
    with pytest.raises(ValidationError, match="generic/1"):
        Lexicon(bullets=("*",))


def test_CF4_a_variant_with_its_own_id_is_valid() -> None:
    profile = Profile(id="custom/1", paragraph_gap_ratio=2.0)
    assert profile.paragraph_gap_ratio == 2.0
    assert profile.line_overlap == 0.5


@pytest.mark.parametrize("bullets", [(), ("**",), ("*", "*")])
def test_CF5_bullets_are_distinct_single_characters(bullets: tuple[str, ...]) -> None:
    with pytest.raises(ValidationError, match="bullet"):
        Lexicon(id="x/1", bullets=bullets)
