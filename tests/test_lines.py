from collections.abc import Sequence

import pytest
from hypothesis import given
from hypothesis import strategies as st

from inkgrid.core.lines import Line, body_size, fragments, group_lines
from inkgrid.model.config import Profile
from inkgrid.model.geometry import Rect
from inkgrid.model.page import Word
from layout_builder import P, place, text_line
from model_builders import mk_word

PROFILE = Profile()


def texts(lines: Sequence[Line]) -> list[list[str]]:
    return [[w.text for w in line.words] for line in lines]


def test_LN1_lines_come_out_top_to_bottom() -> None:
    words = place([P("Rates", 72, 120), P("Fee", 72, 100), P("table", 92, 100)])
    assert texts(group_lines(words, PROFILE)) == [["Fee", "table"], ["Rates"]]


def test_LN2_raised_superscript_shares_the_line() -> None:
    words = place([P("$0.40", 72, 100), P("2", 97, 96.5, superscript=True)])
    assert texts(group_lines(words, PROFILE)) == [["$0.40", "2"]]


def test_LN3_overlap_below_the_share_splits_lines() -> None:
    words = place([P("upper", 72, 100), P("lower", 150, 106)])
    assert texts(group_lines(words, PROFILE)) == [["upper"], ["lower"]]


def test_LN4_line_words_are_sorted_by_x() -> None:
    words = place(list(reversed(text_line(["a", "b", "c"], x=72, y=100))))
    assert texts(group_lines(words, PROFILE)) == [["a", "b", "c"]]


def test_LN5_wide_gaps_split_fragments() -> None:
    words = place([P("a", 72, 100), P("b", 80, 100), P("c", 105, 100)])
    (line,) = group_lines(words, PROFILE)
    assert texts(fragments(line, PROFILE)) == [["a", "b"], ["c"]]


def test_LN6_bold_is_decided_by_characters() -> None:
    bold = text_line(["Fee", "per", "lot"], x=72, y=100, bold=True)
    (heavy,) = group_lines(place([*bold, P("contractuals", 200, 100)]), PROFILE)
    assert heavy.bold is False
    (light,) = group_lines(place([*bold, P("due", 200, 100)]), PROFILE)
    assert light.bold is True


def test_LN7_body_size_carries_the_most_characters() -> None:
    body = place([P("x" * 40, 72, 100, size=10.2), P("y" * 12, 72, 200, size=14.0)])
    assert body_size(body) == 10.0
    tie = place([P("x" * 10, 72, 100, size=9.0), P("y" * 10, 72, 200, size=11.0)])
    assert body_size(tie) == 9.0
    with pytest.raises(ValueError, match="no words"):
        body_size(())


placements = st.lists(
    st.builds(
        P,
        text=st.text("abc", min_size=1, max_size=8),
        x=st.floats(0, 500),
        y=st.floats(0, 700),
        size=st.floats(5, 14),
    ),
    max_size=40,
)


@given(placements)
def test_LN8_every_word_is_in_one_line_and_one_fragment(ps: list[P]) -> None:
    words = place(ps)
    lines = group_lines(words, PROFILE)
    in_lines = [w.id for line in lines for w in line.words]
    assert sorted(in_lines) == [w.id for w in words]
    for line in lines:
        assert [w.bbox.x0 for w in line.words] == sorted(w.bbox.x0 for w in line.words)
        assert [w for f in fragments(line, PROFILE) for w in f.words] == list(line.words)


def test_LN9_a_doubled_text_layer_keeps_both_words() -> None:
    words = place([P("Fee", 72, 100), P("Fee", 72, 100)])
    assert texts(group_lines(words, PROFILE)) == [["Fee", "Fee"]]


# --- a raised mark glued to its value (spec 13 section 5) -----------------------------------------

# olmOCR 2d54e9: `.54` with a raised mark glued on, and the next column's reference line above it
VALUE = mk_word(id=0, text=".54", bbox=Rect(172.29, 157.24, 183.50, 166.20), size=8.97)
REST = mk_word(id=1, text="(.17)", bbox=Rect(190.0, 157.24, 210.0, 166.20), size=8.97)
OTHER = mk_word(id=2, text="chological", bbox=Rect(300.0, 150.15, 360.0, 159.12), size=8.97)


def _mark(*, superscript: bool = True) -> Word:
    return mk_word(
        id=3, text="n", bbox=Rect(183.51, 155.99, 186.99, 161.55), size=5.56,
        superscript=superscript,
    )  # fmt: skip


def test_MK1_a_raised_mark_joins_the_line_of_the_value_it_is_glued_to() -> None:
    lines = group_lines([VALUE, REST, OTHER, _mark()], PROFILE)
    assert texts(lines) == [["chological"], [".54", "n", "(.17)"]]


def test_MK2_a_mark_glued_to_a_word_of_its_own_line_stays() -> None:
    neighbour = mk_word(id=4, text="x", bbox=Rect(187.2, 150.15, 200.0, 159.12), size=8.97)
    lines = group_lines([VALUE, REST, OTHER, neighbour, _mark()], PROFILE)
    assert ["n", "x", "chological"] in texts(lines)


def test_MK3_a_small_word_not_flagged_superscript_stays() -> None:
    lines = group_lines([VALUE, REST, OTHER, _mark(superscript=False)], PROFILE)
    assert ["n", "chological"] in texts(lines)


marked = st.lists(
    st.builds(
        P,
        text=st.text("abc", min_size=1, max_size=4),
        x=st.floats(0, 200),
        y=st.floats(0, 60),
        size=st.floats(5, 14),
        superscript=st.booleans(),
    ),
    max_size=30,
)


@given(marked)
def test_MK4_every_word_stays_in_exactly_one_line(ps: list[P]) -> None:
    words = place(ps)
    lines = group_lines(words, PROFILE)
    assert sorted(w.id for line in lines for w in line.words) == [w.id for w in words]
    for line in lines:
        assert [w.bbox.x0 for w in line.words] == sorted(w.bbox.x0 for w in line.words)
    assert [line.top for line in lines] == sorted(line.top for line in lines)
