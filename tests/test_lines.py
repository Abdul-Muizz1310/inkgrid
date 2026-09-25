from collections.abc import Sequence

import pytest
from hypothesis import given
from hypothesis import strategies as st

from inkgrid.core.lines import Line, body_size, fragments, group_lines
from inkgrid.model.config import Profile
from layout_builder import P, place, text_line

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
