import pytest
from hypothesis import given
from hypothesis import strategies as st

from inkgrid.model.geometry import Rect
from inkgrid.read.raw import RawChar, RawLine, RawSpan
from inkgrid.read.words import build_words

HORIZONTAL = (1.0, 0.0)


def span(
    text: str,
    x0: float,
    *,
    y0: float = 100.0,
    h: float = 10.0,
    w: float = 5.0,
    flags: int = 0,
    char_flags: int = 16,
    font: str = "Helvetica",
    size: float = 10.0,
    alpha: int = 255,
) -> RawSpan:
    chars = tuple(
        RawChar(c, (x0 + i * w, y0, x0 + (i + 1) * w, y0 + h)) for i, c in enumerate(text)
    )
    return RawSpan(
        font=font, size=size, flags=flags, char_flags=char_flags, alpha=alpha, chars=chars
    )


def line(*spans: RawSpan, direction: tuple[float, float] = HORIZONTAL) -> RawLine:
    return RawLine(direction=direction, spans=spans)


def texts(*lines: RawLine) -> list[str]:
    return [w.text for w in build_words(lines, page=1, first_id=0).words]


def test_W1_one_span_two_words() -> None:
    out = build_words([line(span("Hello world", 72))], page=1, first_id=5)
    assert [(w.id, w.text) for w in out.words] == [(5, "Hello"), (6, "world")]
    assert out.words[0].bbox == Rect(72, 100, 97, 110)
    assert out.words[0].page == 1
    assert (out.invisible_chars, out.unmapped_chars, out.hidden_chars) == (0, 0, 0)


def test_W2_font_change_mid_word_is_one_word() -> None:
    bold = span("action", 97, flags=16, font="Helvetica-Bold")
    word = build_words([line(span("Trans", 72), bold)], page=1, first_id=0).words
    assert [w.text for w in word] == ["Transaction"]
    assert (word[0].font, word[0].bold) == ("Helvetica-Bold", True)


def test_W3_superscript_marker_is_its_own_word() -> None:
    marker = span("2", 97, y0=96, h=7, flags=1, size=6.5)
    words = build_words([line(span("$0.40", 72), marker)], page=1, first_id=0).words
    assert [(w.text, w.superscript, w.size) for w in words] == [
        ("$0.40", False, 10.0),
        ("2", True, 6.5),
    ]


def test_W22_a_raised_smaller_mark_is_its_own_word() -> None:
    # PHLX p14: a 7.31 pt `1` on a raised baseline, glued to 8.78 pt text (MuPDF sets no flag)
    mark = span("1", 72, y0=748.7, h=8.09, w=4.0, size=7.31)
    text = span("A surcharge", 76, y0=750.86, h=9.72, size=8.78)
    words = build_words([line(mark, text)], page=1, first_id=0).words
    assert [(w.text, w.superscript) for w in words] == [
        ("1", False),
        ("A", False),
        ("surcharge", False),
    ]


def test_W23_a_mark_neither_smaller_nor_raised_stays_joined() -> None:
    small_caps = span("2", 72, y0=102.6, h=7.0, w=4.0, size=7.0)  # bottom 0.4 pt above `Fee`'s
    assert texts(line(small_caps, span("Fee", 76))) == ["2Fee"]
    raised = span("2", 72, y0=96.0, h=10.0, w=4.0, size=10.0)  # raised, but not smaller
    assert texts(line(raised, span("Fee", 76))) == ["2Fee"]


@pytest.mark.parametrize(
    ("gap", "expected"),
    [
        (0.7, ["Trans", "action"]),
        (0.6, ["Transaction"]),
        (-1.0, ["Transaction"]),
        (-1.1, ["Trans", "action"]),
    ],
)
def test_W4_join_gap_limits(gap: float, expected: list[str]) -> None:
    assert texts(line(span("Trans", 72), span("action", 97 + gap))) == expected


def test_W5_spans_in_different_lines_never_join() -> None:
    assert texts(line(span("Trans", 72)), line(span("action", 97))) == ["Trans", "action"]


def test_W6_join_needs_vertical_overlap() -> None:
    low = span("action", 97, y0=107.5)
    assert texts(line(span("Trans", 72), low)) == ["Trans", "action"]


def test_W7_soft_hyphen_is_invisible_and_does_not_split() -> None:
    out = build_words([line(span("soft\u00adhy", 72))], page=1, first_id=0)
    assert ([w.text for w in out.words], out.invisible_chars) == (["softhy"], 1)


def test_W8_zero_width_space_splits_and_counts_as_invisible() -> None:
    out = build_words([line(span("zero\u200bwidth", 72))], page=1, first_id=0)
    assert ([w.text for w in out.words], out.invisible_chars) == (["zero", "width"], 1)


@pytest.mark.parametrize("text", ["a\ue000b", "a\x07b"], ids=["private-use", "control"])
def test_W9_private_use_and_control_characters_are_dropped(text: str) -> None:
    out = build_words([line(span(text, 72))], page=1, first_id=0)
    assert ([w.text for w in out.words], out.invisible_chars) == (["ab"], 1)


def test_W10_unmapped_glyphs_stay_and_are_counted() -> None:
    out = build_words([line(span("\ufffd\ufffdC", 72))], page=1, first_id=0)
    assert ([w.text for w in out.words], out.unmapped_chars) == (["\ufffd\ufffdC"], 2)


def test_W11_render_mode_3_marks_words_hidden() -> None:
    out = build_words([line(span("secret note", 72, char_flags=0))], page=1, first_id=0)
    assert [w.hidden for w in out.words] == [True, True]
    assert out.hidden_chars == 10


def test_W12_hidden_and_visible_spans_do_not_join() -> None:
    assert texts(line(span("ab", 72, char_flags=0), span("cd", 82))) == ["ab", "cd"]


def test_W13_unicode_spaces_split_words() -> None:
    assert texts(line(span("a\tb\u00a0c\u202fd\u2009e", 72))) == ["a", "b", "c", "d", "e"]


def test_W14_vertical_lines_never_join_and_are_not_horizontal() -> None:
    down = (0.0, -1.0)
    words = build_words(
        [line(span("ab", 72), span("cd", 82), direction=down)], page=1, first_id=0
    ).words
    assert [(w.text, w.horizontal) for w in words] == [("ab", False), ("cd", False)]


@pytest.mark.parametrize(
    ("font", "flags", "char_flags", "bold", "italic"),
    [
        ("Helvetica-Bold", 0, 16, True, False),
        ("Arial,BoldMT", 0, 16, True, False),
        ("Times-Italic", 0, 16, False, True),
        ("Foo-Oblique", 0, 16, False, True),
        ("ABCDEF+Arial-BoldMT", 0, 16, True, False),
        ("XYZABC+TimesNewRomanPS-ItalicMT", 0, 16, False, True),
        ("Helvetica", 16, 16, True, False),
        ("Helvetica", 0, 24, True, False),
        ("Helvetica", 2, 16, False, True),
        ("Helvetica", 0, 16, False, False),
    ],
)
def test_W15_bold_and_italic_signals(
    font: str, flags: int, char_flags: int, bold: bool, italic: bool
) -> None:
    s = span("x", 72, font=font, flags=flags, char_flags=char_flags)
    word = build_words([line(s)], page=1, first_id=0).words[0]
    assert (word.bold, word.italic) == (bold, italic)


def test_W16_whitespace_and_invisible_only_span_yields_no_words() -> None:
    out = build_words([line(span(" \t\u200b\u00ad ", 72))], page=1, first_id=0)
    assert out.words == ()
    assert out.invisible_chars == 2


@st.composite
def touching_spans(draw: st.DrawFn) -> list[str]:
    return draw(st.lists(st.text(alphabet="ab \t", min_size=1, max_size=6), min_size=1, max_size=6))


@given(touching_spans())
def test_W17_touching_spans_split_exactly_on_whitespace(parts: list[str]) -> None:
    spans = []
    x = 72.0
    for part in parts:
        spans.append(span(part, x))
        x += 5.0 * len(part)
    words = build_words([line(*spans)], page=1, first_id=0).words
    assert [w.text for w in words] == "".join(parts).split()
    assert [w.id for w in words] == list(range(len(words)))


def test_W18_mode_7_clip_only_text_is_hidden() -> None:
    out = build_words([line(span("secret", 72, char_flags=80, alpha=0))], page=1, first_id=0)
    assert [(w.text, w.hidden) for w in out.words] == [("secret", True)]
    assert out.hidden_chars == 6


@pytest.mark.parametrize("same_line", [True, False], ids=["same-line", "own-line"])
def test_W19_clip_copy_of_visible_text_is_not_a_second_word(same_line: bool) -> None:
    visible = span("mode4", 72)
    copy = span("mode4", 72, char_flags=80, alpha=0)
    lines = [line(visible, copy)] if same_line else [line(visible), line(copy)]
    out = build_words(lines, page=1, first_id=0)
    assert [(w.text, w.hidden) for w in out.words] == [("mode4", False)]
    assert out.hidden_chars == 0


def test_W20_alpha_zero_fill_is_hidden() -> None:
    out = build_words([line(span("ghost", 72, char_flags=16, alpha=0))], page=1, first_id=0)
    assert [(w.text, w.hidden) for w in out.words] == [("ghost", True)]


def test_W21_lone_surrogate_reads_as_replacement_character() -> None:
    out = build_words([line(span("\ud800B", 72))], page=1, first_id=0)
    assert [w.text for w in out.words] == ["\ufffdB"]
    assert out.unmapped_chars == 1
