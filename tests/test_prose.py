from collections.abc import Sequence
from typing import Literal

from inkgrid.core.layout import Region
from inkgrid.core.lines import group_lines
from inkgrid.core.prose import ProtoBlock, line_gaps, page_blocks
from inkgrid.model.config import Lexicon, Profile
from layout_builder import P, place, text_line

PROFILE = Profile()
LEXICON = Lexicon()
BODY = 10.0
BULLET = "\u2022"


def blocks_of(ps: Sequence[P], kind: Literal["prose", "rows"] = "prose") -> tuple[ProtoBlock, ...]:
    region = Region(kind, group_lines(place(ps), PROFILE))
    return page_blocks((region,), LEXICON, PROFILE, BODY, line_gaps((region,)))


def summary(blocks: Sequence[ProtoBlock]) -> list[tuple[str, str | None, str]]:
    return [
        (b.kind, b.label or b.number, " ".join(w.text for line in b.lines for w in line.words))
        for b in blocks
    ]


def lines(
    texts: Sequence[str],
    *,
    y: float,
    x: float = 72.0,
    size: float = 10.0,
    bold: bool = False,
    pitch: float = 12.0,
) -> list[P]:
    """One line per text, `pitch` apart, top to bottom."""
    out: list[P] = []
    for i, text in enumerate(texts):
        out += text_line(text.split(), x=x, y=y + pitch * i, size=size, bold=bold)
    return out


def test_PB1_a_paragraph_gap_splits_paragraphs() -> None:
    ps = lines(["One a", "one b", "one c."], y=100) + lines(["Two a", "two b."], y=146)
    blocks = blocks_of(ps)
    assert [b.kind for b in blocks] == ["paragraph", "paragraph"]
    assert [len(b.lines) for b in blocks] == [3, 2]


def test_PB2_a_large_bold_line_is_a_heading() -> None:
    ps = lines(["Transaction fees"], y=80, size=14, bold=True) + lines(["body a", "body b"], y=100)
    assert summary(blocks_of(ps)) == [
        ("heading", None, "Transaction fees"),
        ("paragraph", None, "body a body b"),
    ]


def test_PB3_a_heading_records_its_section_number() -> None:
    ps = lines(["2.1 Transaction fees"], y=88, bold=True) + lines(["body a"], y=100)
    assert summary(blocks_of(ps))[0] == ("heading", "2.1", "2.1 Transaction fees")


def test_PB4_a_year_does_not_number_a_heading() -> None:
    ps = lines(["2026 Fee schedule"], y=88, bold=True) + lines(["body a"], y=100)
    assert summary(blocks_of(ps))[0] == ("heading", None, "2026 Fee schedule")


def test_PB5_bullets_start_list_items() -> None:
    ps = lines([f"{BULLET} first", f"{BULLET} second", f"{BULLET} third"], y=100)
    ps += lines(["After the list"], y=146)
    assert summary(blocks_of(ps)) == [
        ("list_item", BULLET, f"{BULLET} first"),
        ("list_item", BULLET, f"{BULLET} second"),
        ("list_item", BULLET, f"{BULLET} third"),
        ("paragraph", None, "After the list"),
    ]


def test_PB6_enumerated_items_span_lines() -> None:
    ps = lines(["a) The charge is", "billed monthly", "b) Rebates apply"], y=100)
    assert summary(blocks_of(ps)) == [
        ("list_item", "a)", "a) The charge is billed monthly"),
        ("list_item", "b)", "b) Rebates apply"),
    ]


def test_PB7_small_type_opening_with_a_number_is_a_footnote() -> None:
    ps = lines(["body a", "body b"], y=100) + lines(["3 Applies to members"], y=130, size=7)
    assert summary(blocks_of(ps))[-1] == ("footnote", "3", "3 Applies to members")


def test_PB8_small_type_opening_with_a_superscript_is_a_footnote() -> None:
    ps = lines(["body a"], y=100)
    ps += [
        P("*", 72, 128, size=5, superscript=True),
        *text_line(["Excludes", "fees"], x=76, y=130, size=7),
    ]
    assert summary(blocks_of(ps))[-1] == ("footnote", "*", "* Excludes fees")


def test_PB9_a_bold_sentence_is_a_paragraph() -> None:
    ps = lines(["Fees are billed."], y=88, bold=True) + lines(["body a"], y=100)
    assert summary(blocks_of(ps))[0] == ("paragraph", None, "Fees are billed.")


def test_PB10_a_small_parenthesized_label_is_a_footnote_not_a_list_item() -> None:
    ps = lines(["body a"], y=100) + lines(["(3) Applies to members"], y=130, size=7)
    assert summary(blocks_of(ps))[-1] == ("footnote", "3", "(3) Applies to members")


def test_PB11_a_bold_bullet_line_is_a_list_item() -> None:
    ps = lines([f"{BULLET} Item"], y=88, bold=True) + lines(["body a"], y=100)
    assert summary(blocks_of(ps))[0] == ("list_item", BULLET, f"{BULLET} Item")


def test_PB12_a_bold_block_over_two_lines_is_a_paragraph() -> None:
    ps = lines(
        ["one two three four", "five six seven eight", "nine ten eleven twelve"], y=100, bold=True
    )
    assert [b.kind for b in blocks_of(ps)] == ["paragraph"]


def test_PB13_a_hanging_indent_rows_region_reads_as_list_items() -> None:
    ps: list[P] = []
    for i in range(3):
        y = 100 + 24 * i
        ps += [P(f"{i + 1}.", 72, y), *text_line(["charge", "applies"], x=90, y=y)]
        ps += text_line(["continued"], x=90, y=y + 12)
    blocks = blocks_of(ps, kind="rows")
    assert [(b.kind, b.label, len(b.lines)) for b in blocks] == [
        ("list_item", "1.", 2),
        ("list_item", "2.", 2),
        ("list_item", "3.", 2),
    ]


def test_PB14_a_body_size_line_opening_with_a_superscript_is_a_paragraph() -> None:
    ps = [P("2", 72, 98, size=6, superscript=True), *text_line(["Rates", "apply"], x=76, y=100)]
    assert [b.kind for b in blocks_of(ps)] == ["paragraph"]


def test_PB17_each_type_size_keeps_its_own_leading() -> None:
    loose = [
        *lines(["Alpha one two", "alpha three four", "alpha five six."], y=100, pitch=14),
        *lines(
            ["Beta one two", "beta three four", "beta five six."], y=100 + 2 * 14 + 26, pitch=14
        ),
    ]
    tight = lines([f"row {n} value" for n in range(8)], y=400, size=7, pitch=7)
    regions = (Region("prose", group_lines(place(loose + tight), PROFILE)),)
    blocks = page_blocks(regions, LEXICON, PROFILE, BODY, line_gaps(regions))
    assert [len(b.lines) for b in blocks] == [3, 3, 8]


def test_PB18_a_sentence_that_runs_on_is_not_broken_by_its_gap() -> None:
    tight = lines([f"Tight {n} line." for n in range(8)], y=100, pitch=10)
    item = lines(
        ["The fee is payable by any", "entity that has been granted", "status on the exchange."],
        y=200,
        pitch=14,
    )
    after = lines(["Fees apply monthly.", "Rebates are paid later."], y=260, pitch=14)
    regions = (Region("prose", group_lines(place(tight + item + after), PROFILE)),)
    blocks = page_blocks(regions, LEXICON, PROFILE, BODY, line_gaps(regions))
    texts = [" ".join(w.text for line in b.lines for w in line.words) for b in blocks]
    assert "The fee is payable by any entity that has been granted status on the exchange." in texts
    assert texts[-2:] == ["Fees apply monthly.", "Rebates are paid later."]
