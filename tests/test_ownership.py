from collections.abc import Sequence

from hypothesis import given
from hypothesis import strategies as st

from ink_builder import edited, ink_words, moved, page, stray, word_chars
from inkgrid.model.geometry import Rect
from inkgrid.model.page import Word
from inkgrid.verify.ink import InkChar, InkPage
from inkgrid.verify.ownership import PageOwnership, own_page
from model_builders import mk_word


def own(
    ink: InkPage, words: Sequence[Word], *, clipped: int = 0, invisible: int = 0
) -> PageOwnership:
    return own_page(ink, words, clipped_chars=clipped, invisible_chars=invisible)


def words_on_line(texts: Sequence[str], *, y: float = 100.0, first_id: int = 0) -> list[Word]:
    out, x = [], 72.0
    for i, text in enumerate(texts):
        out.append(mk_word(id=first_id + i, text=text, bbox=Rect(x, y, x + 5 * len(text), y + 10)))
        x += 5 * len(text) + 5
    return out


def clean(result: PageOwnership) -> bool:
    return not (result.lost or result.doubled or result.invented)


FEE = words_on_line(["Fee", "Rate"])


@given(
    st.lists(
        st.lists(st.text(alphabet="abcdef$.,01", min_size=1, max_size=8), min_size=1, max_size=6),
        min_size=1,
        max_size=5,
    )
)
def test_OW1_ink_made_from_words_goes_back_to_them(lines: list[list[str]]) -> None:
    words: list[Word] = []
    for n, texts in enumerate(lines):
        words += words_on_line(texts, y=100.0 + 10 * n, first_id=len(words))
    ink = ink_words(words)
    result = own(ink, words)
    made_from = [w.id for w in words for _ in w.text]
    assert [result.owner[ch.index] for ch in ink.chars if ch.is_ink] == made_from
    assert clean(result)
    assert result.owned == len(made_from)


def test_OW2_a_centre_on_a_shared_edge_belongs_to_the_next_word() -> None:
    a = mk_word(id=0, text="a", bbox=Rect(0, 0, 10, 10))
    b = mk_word(id=1, text="a", bbox=Rect(10, 0, 20, 10))
    ink = page([InkChar(0, "a", Rect(8, 0, 12, 10), "ink")])
    assert own(ink, [a, b]).owner == {0: 1}


def test_OW3_overprinted_titles_each_keep_their_characters() -> None:
    user = mk_word(id=0, text="User", bbox=Rect(39.84, 358.69, 128.67, 403.24))
    fee = mk_word(id=1, text="Fee", bbox=Rect(39.96, 364.8, 84.83, 393.84))
    measured = [
        ("U", 39.8, 68.7, 365.8, 403.2),
        ("s", 68.7, 90.9, 365.8, 403.2),
        ("e", 90.9, 113.1, 365.8, 403.2),
        ("r", 113.1, 128.7, 365.8, 403.2),
        ("F", 40.0, 55.9, 369.4, 393.8),
        ("e", 55.9, 70.3, 369.4, 393.8),
        ("e", 70.3, 84.8, 369.4, 393.8),
    ]
    ink = page([InkChar(0, c, Rect(x0, y0, x1, y1), "ink") for c, x0, x1, y0, y1 in measured])
    result = own(ink, [user, fee])
    assert [result.owner[i] for i in range(7)] == [0, 0, 0, 0, 1, 1, 1]
    assert clean(result)


def test_OW4_a_contested_character_goes_to_the_nearer_line() -> None:
    near = mk_word(id=1, text="e", bbox=Rect(0, 0, 20, 10))  # centre y 5
    far = mk_word(id=0, text="e", bbox=Rect(0, 2, 20, 14))  # centre y 8
    ink = page([InkChar(0, "e", Rect(8, 1, 12, 11), "ink")])  # centre y 6
    assert own(ink, [far, near]).owner == {0: 1}


def test_OW5_a_zero_width_word_contains_a_character_on_its_edge() -> None:
    mark = mk_word(id=0, text="a", bbox=Rect(10, 0, 10, 10))
    ink = page([InkChar(0, "a", Rect(8, 0, 12, 10), "ink")])
    assert own(ink, [mark]).owner == {0: 0}


def test_DC1_adjacent_stray_characters_are_one_lost_run() -> None:
    ink = edited(ink_words(FEE), lambda cs: [*cs, *stray("xy", 300, 300)])
    result = own(ink, FEE)
    assert ["".join(c.char for c in run) for run in result.lost] == ["xy"]


def test_DC1_lost_runs_break_at_owned_ink() -> None:
    ink = edited(ink_words(FEE), lambda cs: [*stray("x", 300, 300), *cs, *stray("y", 300, 300)])
    assert ["".join(c.char for c in run) for run in own(ink, FEE).lost] == ["x", "y"]


def test_DC2_a_stray_character_inside_a_word_is_lost() -> None:
    ink = edited(ink_words(FEE), lambda cs: [*cs, *stray("q", 76, 100)])
    result = own(ink, FEE)
    assert ["".join(c.char for c in run) for run in result.lost] == ["q"]
    assert not result.invented


def test_DC3_a_word_character_with_no_ink_is_invented() -> None:
    ink = edited(ink_words(FEE), lambda cs: cs[1:])  # drop the F
    result = own(ink, FEE)
    assert [(g.word.text, g.missing) for g in result.invented] == [("Fee", "F")]
    assert not result.lost


def test_DC4_a_word_read_twice_over_one_ink_is_doubled() -> None:
    first, twin = (mk_word(id=i, text="Fee", bbox=Rect(72, 100, 87, 110)) for i in (0, 1))
    result = own(ink_words([first]), [first, twin])
    assert [(g.word.id, g.missing) for g in result.doubled] == [(1, "Fee")]
    assert not result.invented


def test_DC5_an_unmapped_character_matches_anything_on_either_side() -> None:
    word = mk_word(id=0, text="\ufffdB", bbox=Rect(72, 100, 82, 110))
    ink = page([InkChar(0, "A", Rect(72, 100, 77, 110), "ink"), *word_chars(word)[1:]])
    result = own(ink, [word])
    assert clean(result)
    assert result.unmapped == 1
    plain = mk_word(id=0, text="AB", bbox=Rect(72, 100, 82, 110))
    ink = page([InkChar(0, "\ufffd", Rect(72, 100, 77, 110), "unmapped"), *word_chars(plain)[1:]])
    result = own(ink, [plain])
    assert clean(result)
    assert result.unmapped == 1


def test_DC6_ink_outside_the_frame_is_benign_up_to_the_readers_count() -> None:
    ink = edited(ink_words(FEE), lambda cs: [*cs, *stray("o", -20, 100)])
    assert own(ink, FEE, clipped=1).outside == 1
    assert clean(own(ink, FEE, clipped=1))
    assert ["".join(c.char for c in r) for r in own(ink, FEE, clipped=0).lost] == ["o"]
    assert own(ink, FEE, clipped=0).outside == 0


def test_DC7_clipped_ink_is_benign_up_to_the_readers_count() -> None:
    ink = edited(ink_words(FEE), lambda cs: [*cs, *stray("c", 300, 300, clipped=True)])
    assert own(ink, FEE, clipped=1).clipped == 1
    assert clean(own(ink, FEE, clipped=1))
    assert ["".join(c.char for c in r) for r in own(ink, FEE, clipped=0).lost] == ["c"]


def test_DC7_a_clipped_character_under_a_word_is_never_offered_to_it() -> None:
    ink = edited(ink_words(FEE), lambda cs: [*cs, *stray("q", 76, 100, clipped=True)])
    result = own(ink, FEE, clipped=1)
    assert clean(result)
    assert result.clipped == 1


def test_DC13_a_line_end_soft_hyphen_is_benign_up_to_the_invisible_count() -> None:
    soft = words_on_line(["soft"])
    ink = edited(ink_words(soft), lambda cs: [*cs, *stray("-", 92, 100, kind="hyphen")])
    assert own(ink, soft, invisible=1).soft_hyphens == 1
    assert clean(own(ink, soft, invisible=1))
    assert ["".join(c.char for c in r) for r in own(ink, soft, invisible=0).lost] == ["-"]


def test_DC13_a_soft_hyphen_left_over_in_a_word_is_benign_too() -> None:
    soft = words_on_line(["soft"])
    ink = edited(ink_words(soft), lambda cs: [*cs, *stray("-", 88, 100, kind="hyphen")])
    result = own(ink, soft, invisible=1)
    assert clean(result)
    assert result.soft_hyphens == 1


def test_DC14_a_line_end_hyphen_pairs_with_the_words_hyphen() -> None:
    hard = words_on_line(["hard-"])
    ink = edited(
        ink_words(hard),
        lambda cs: [*cs[:4], InkChar(0, "-", cs[4].box, "hyphen"), *cs[5:]],
    )
    result = own(ink, hard)
    assert clean(result)
    assert result.soft_hyphens == 0
    assert result.owned == 5


def test_every_ink_character_is_counted_once() -> None:
    ink = edited(
        ink_words(FEE),
        lambda cs: [*cs[1:], *stray("xy", 300, 300), *stray("o", -20, 0), moved(cs[0], 0)],
    )
    result = own(ink, FEE, clipped=1)
    total = sum(1 for ch in ink.chars if ch.is_ink)
    lost = sum(len(run) for run in result.lost)
    assert result.owned + lost + result.outside + result.clipped + result.soft_hyphens == total
