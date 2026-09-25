from collections.abc import Sequence

import pytest

from inkgrid.core.furniture import FoundFurniture, find_furniture, line_key
from inkgrid.core.lines import Line
from inkgrid.model.config import Profile
from inkgrid.model.page import PageModel
from layout_builder import P, place, text_line
from model_builders import mk_page

PROFILE = Profile()
BODY = [["alpha", "beta", "gamma"], ["delta", "epsilon"], ["zeta", "eta", "theta"]]


def body(page: int, *, y: float = 200.0) -> list[P]:
    """Three body lines that differ from page to page in their letters, as real text does."""
    suffix = "".join(chr(ord("a") + int(d)) for d in str(page))
    out: list[P] = []
    for i, words in enumerate(BODY):
        out += text_line([f"{w}{suffix}" for w in words], x=72, y=y + 40 * i)
    return out


def pages_of(specs: Sequence[Sequence[P]]) -> tuple[PageModel, ...]:
    pages = []
    next_id = 0
    for number, ps in enumerate(specs, 1):
        words = place(ps, page=number, first_id=next_id)
        next_id += len(words)
        pages.append(mk_page(number=number, words=words, text_layer="full" if words else "none"))
    return tuple(pages)


def marked(found: FoundFurniture) -> list[tuple[int, str, str]]:
    return [(f.page, f.role, " ".join(w.text for w in f.line.words)) for f in found.lines]


def header(text: str, y: float = 40.0) -> list[P]:
    return text_line(text.split(), x=72, y=y)


def test_FU1_running_header_and_footer_are_furniture() -> None:
    specs = [
        [*header("Acme Fee Guide"), *body(n), *header(f"Page {n} of 5", y=750)] for n in range(1, 6)
    ]
    pages = pages_of(specs)
    found = find_furniture(pages, PROFILE)
    assert marked(found) == [
        item
        for n in range(1, 6)
        for item in ((n, "header", "Acme Fee Guide"), (n, "footer", f"Page {n} of 5"))
    ]
    furniture_words = {w.id for page in pages for w in page.words if w.bbox.y0 in {40.0, 750.0}}
    assert found.word_ids == furniture_words


def test_FU2_page_number_position_and_roman_numerals_share_one_key() -> None:
    footers = [
        "i Acme Fee Guide",
        "Acme Fee Guide 2",
        "3 Acme Fee Guide",
        "Acme Fee Guide 4",
        "5 Acme Fee Guide",
    ]
    specs = [[*body(n), *header(text, y=750)] for n, text in enumerate(footers, 1)]
    found = find_furniture(pages_of(specs), PROFILE)
    assert {f.key for f in found.lines} == {"Acme Fee Guide"}
    assert [f.page for f in found.lines] == [1, 2, 3, 4, 5]
    assert {f.role for f in found.lines} == {"footer"}


def test_FU3_a_key_on_one_page_is_not_furniture() -> None:
    specs = [[*header("Acme Fee Guide"), *body(1)]] + [body(n) for n in range(2, 6)]
    assert find_furniture(pages_of(specs), PROFILE).lines == ()


def test_FU4_a_one_page_document_has_no_furniture() -> None:
    specs = [[*body(1), *header("Page 1 of 1", y=750)]]
    assert find_furniture(pages_of(specs), PROFILE).lines == ()


def test_FU5_a_bare_number_off_the_page_number_column_is_not_furniture() -> None:
    specs = [[*body(n), P(str(n), 300, 750)] for n in range(1, 5)]
    specs[1] = [*specs[1], P("3", 72, 720)]
    found = find_furniture(pages_of(specs), PROFILE)
    assert marked(found) == [(n, "page_number", str(n)) for n in range(1, 5)]


def test_FU6_an_alphabetic_key_is_marked_outside_the_band() -> None:
    specs = [[*body(n), *header("Acme Fee Guide", y=750)] for n in range(1, 5)]
    specs.append([*body(5, y=100), *header("Acme Fee Guide", y=300), *body(55, y=600)])
    found = find_furniture(pages_of(specs), PROFILE)
    assert [f.page for f in found.lines] == [1, 2, 3, 4, 5]


def test_FU7_a_line_mixing_furniture_and_body_is_not_marked() -> None:
    specs = [[*body(n), *header("Acme Fee Guide", y=750)] for n in range(1, 6)]
    specs[2] = [*body(3), *text_line(["Acme", "Fee", "Guide", "extra"], x=72, y=750)]
    found = find_furniture(pages_of(specs), PROFILE)
    assert [f.page for f in found.lines] == [1, 2, 4, 5]


def test_FU8_no_repeated_edge_lines_is_an_empty_result() -> None:
    found = find_furniture(pages_of([body(n) for n in range(1, 4)]), PROFILE)
    assert found.lines == ()
    assert found.word_ids == frozenset()


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("Page 3 of 12", "Page # of"),
        ("- 4 -", "- # -"),
        ("iv Annual civil fees", "Annual civil fees"),
        ("2026 Fee schedule 7", "Fee schedule"),
        ("xiv", "#"),
        ("- ii -", "- # -"),
    ],
)
def test_FU9_line_key(text: str, key: str) -> None:
    line = Line(place(text_line(text.split(), x=72, y=100)))
    assert line_key(line) == key


def test_FU10_right_aligned_page_numbers_are_one_column() -> None:
    specs = []
    for n in range(1, 13):
        number = str(n)
        width = 5.0 * len(number)
        specs.append([*body(n), P(number, 540 - width, 750)])
    found = find_furniture(pages_of(specs), PROFILE)
    assert marked(found) == [(n, "page_number", str(n)) for n in range(1, 13)]


def test_FU11_tier_rows_in_the_band_are_not_furniture() -> None:
    specs = []
    for n in range(1, 4):
        rows = [
            p
            for k in range(5)
            for p in text_line(["Tier", str(k), "volume", "rate"], x=72, y=700 + 12 * k)
        ]
        specs.append([*header("Acme Fee Guide"), *body(n), *rows])
    found = find_furniture(pages_of(specs), PROFILE)
    assert {f.key for f in found.lines} == {"Acme Fee Guide"}
    assert [f.page for f in found.lines] == [1, 2, 3]


def test_FU12_a_repeated_column_header_row_is_not_furniture() -> None:
    columns = [P("Tier", 72, 40), P("Volume", 250, 40), P("Rate", 400, 40)]
    specs = [[*columns, *body(n), *header(f"Page {n} of 3", y=750)] for n in range(1, 4)]
    found = find_furniture(pages_of(specs), PROFILE)
    assert {f.key for f in found.lines} == {"Page # of"}


def test_FU13_mirrored_page_numbers_are_found() -> None:
    specs = []
    for n in range(1, 13):
        number = str(n)
        x = 72.0 if n % 2 == 0 else 540 - 5.0 * len(number)
        specs.append([*body(n), P(number, x, 750)])
    found = find_furniture(pages_of(specs), PROFILE)
    assert marked(found) == [(n, "page_number", str(n)) for n in range(1, 13)]
