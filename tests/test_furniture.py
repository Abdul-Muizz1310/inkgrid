from collections.abc import Sequence
from itertools import pairwise

import pytest

from inkgrid.core.furniture import (
    FoundFurniture,
    find_furniture,
    line_key,
    page_number_token,
    prints_page_number,
)
from inkgrid.core.lines import Line
from inkgrid.model.config import Profile
from inkgrid.model.geometry import Rect
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


def test_FU4_a_one_page_footer_that_prints_no_role_is_not_furniture() -> None:
    # Recurrence needs 2 pages; on one page, S3 needs a page number or smaller type (spec 19 s. 1).
    specs = [[*body(1), *header("Acme Fee Guide", y=750)]]
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


def spanning_table(n: int) -> tuple[list[P], list[Rect]]:
    """A ruled table at the page's top whose first row's header spans columns 1-3 (eu-001)."""
    xs, top, pitch = (72.0, 272.0, 352.0, 432.0, 512.0), 56.0, 16.0
    cells = [Rect(xs[0], top, xs[1], top + 2 * pitch), Rect(xs[1], top, xs[4], top + pitch)]
    cells += [Rect(xs[c], top + pitch, xs[c + 1], top + 2 * pitch) for c in range(1, 4)]
    words = [*text_line(["Threshold", "for", "releases"], x=330, y=top + 3)]
    words += [P(t, xs[c + 1] + 10, top + pitch + 3) for c, t in enumerate(("air", "water", "land"))]
    for r in range(2, 8):
        y = top + pitch * r
        cells += [Rect(xs[c], y, xs[c + 1], y + pitch) for c in range(4)]
        words += text_line([f"Compound{'abc'[n - 1] * r}"], x=76, y=y + 3)
        words += [P(str(r * (c + 1)), xs[c + 1] + 10, y + 3) for c in range(3)]
    return words, cells


def test_FT1_a_spanning_header_in_the_top_band_stays_in_its_table() -> None:
    specs: list[list[P]] = [[*body(1), *header("Acme Fee Guide", y=740)]]
    grids: dict[int, list[list[Rect]]] = {}
    for n in (2, 3):
        words, cells = spanning_table(n)
        specs.append([*words, *header("Acme Fee Guide", y=740)])
        grids[n] = [cells]
    pages = pages_of(specs)
    assert "Threshold for releases" in {f.key for f in find_furniture(pages, PROFILE).lines}
    found = find_furniture(pages, PROFILE, grids=grids)
    assert {f.key for f in found.lines} == {"Acme Fee Guide"}
    assert [f.page for f in found.lines] == [1, 2, 3]


def test_FT2_a_stub_banner_below_a_column_header_stays_in_the_table() -> None:
    specs = []
    for n in range(1, 4):
        ps = [*header("Acme Statistics", y=40)]
        ps += header(f"Table {n}. Enrolment by {('level', 'control', 'region')[n - 1]}", y=58)
        ps += [
            P(t, x, 76)
            for x, t in zip(
                (72, 200, 300, 400), ("Year", "Total", "Public", "Private"), strict=True
            )
        ]
        ps += [P("Actual", 72, 90, bold=True)]
        for i in range(40):
            ps += [P(str(1990 + i), 72, 102 + 11 * i)]
            ps += [
                P(f"{n * (i + 1) * (k + 3)},{100 + i}", x, 102 + 11 * i)
                for k, x in enumerate((200, 300, 400))
            ]
        ps += header(f"Page {n}", y=700)
        specs.append(ps)
    found = find_furniture(pages_of(specs), PROFILE)
    assert {f.key for f in found.lines} == {"Acme Statistics", "Page"}
    assert len(found.lines) == 6


def test_FT3_a_footer_above_a_line_that_mirrors_between_pages_is_furniture() -> None:
    specs = []
    for n in (1, 2):
        outer = (
            f"S {n} Monthly Bulletin March 2006" if n % 2 else f"Monthly Bulletin March 2006 S {n}"
        )
        specs.append([*body(n, y=100), *header("ECB", y=740), *header(outer, y=752)])
    found = find_furniture(pages_of(specs), PROFILE)
    assert marked(found) == [(1, "footer", "ECB"), (2, "footer", "ECB")]


def test_FT4_a_label_alone_in_a_box_stays_furniture() -> None:
    xs, ys = (0.0, 7.0, 134.0, 595.0), (750.0, 755.0, 772.0, 781.0)
    box = [Rect(x0, y0, x1, y1) for x0, x1 in pairwise(xs) for y0, y1 in pairwise(ys)]
    label = "Sensitivity: C1 Public"
    specs = [[*body(n, y=100), *text_line(label.split(), x=12, y=758, size=7)] for n in (1, 2, 3)]
    found = find_furniture(pages_of(specs), PROFILE, grids={n: [box] for n in (1, 2, 3)})
    assert marked(found) == [(n, "footer", label) for n in (1, 2, 3)]


def test_FT1_a_table_line_counts_no_page_for_its_key() -> None:
    specs: list[list[P]] = [
        [*header("Threshold for releases"), *body(1), *header("Acme Fee Guide", y=740)]
    ]
    grids: dict[int, list[list[Rect]]] = {}
    for n in (2, 3):
        words, cells = spanning_table(n)
        specs.append([*words, *header("Acme Fee Guide", y=740)])
        grids[n] = [cells]
    found = find_furniture(pages_of(specs), PROFILE, grids=grids)
    assert {f.key for f in found.lines} == {"Acme Fee Guide"}  # page 1's heading is on one page


def test_FT1_a_table_cell_that_repeats_a_running_header_stays_in_its_table() -> None:
    xs, ys = (72.0, 272.0, 472.0), (300.0, 316.0, 332.0, 348.0)
    cells = [Rect(x0, y0, x1, y1) for x0, x1 in pairwise(xs) for y0, y1 in pairwise(ys)]
    table = [P("Source", 80, 303), P("Rate", 280, 303), P("Other", 80, 335), P("Cap", 280, 335)]
    table += text_line(["Acme", "Fee", "Guide"], x=80, y=319)  # alone on its row
    specs = [[*header("Acme Fee Guide"), *body(n)] for n in (1, 2, 3)]
    specs[1] += table
    pages = pages_of(specs)
    assert len(find_furniture(pages, PROFILE).lines) == 4  # its key is furniture on every page
    found = find_furniture(pages, PROFILE, grids={2: [cells]})
    assert marked(found) == [(n, "header", "Acme Fee Guide") for n in (1, 2, 3)]


def test_FT2_a_stub_above_a_column_shaped_row_at_the_foot_is_not_furniture() -> None:
    specs = []
    for n in range(1, 4):
        row = [
            P(t, x, 740) for x, t in zip((72, 200, 300), ("Total", f"{n}9", f"{n}8"), strict=True)
        ]
        specs.append([*body(n), *header("Subtotal", y=726), *row, *header(f"Page {n}", y=760)])
    found = find_furniture(pages_of(specs), PROFILE)
    assert {f.key for f in found.lines} == {"Page"}


def test_FT4_a_grid_the_lattice_stage_could_not_accept_holds_no_table_line() -> None:
    # One row of three tall cells: the footer in the first, two words below it in the others.
    row = [Rect(72, 740, 272, 780), Rect(272, 740, 372, 780), Rect(372, 740, 472, 780)]
    untiled = [*row[:2], Rect(300, 740, 472, 780)]  # the last cell overlaps the second
    specs = [
        [*body(n), *header("Acme Fee Guide", y=745), P("Tel", 280, 766), P("Fax", 380, 766)]
        for n in (1, 2, 3)
    ]
    for cells in (row, untiled):
        found = find_furniture(pages_of(specs), PROFILE, grids={n: [cells] for n in (1, 2, 3)})
        assert [f.key for f in found.lines].count("Acme Fee Guide") == 3


def test_FT6_a_ruled_box_repeated_on_every_page_is_running_furniture() -> None:
    box = [
        Rect(72, 36, 400, 54),
        Rect(400, 36, 540, 54),
        Rect(72, 54, 400, 72),
        Rect(400, 54, 540, 72),
    ]
    specs = []
    for n in (1, 2, 3):
        ps = [
            P("Acme", 76, 40),
            P("Doc", 404, 40),
            P("Fees", 76, 58),
            *text_line(["Revision", str(n)], x=404, y=58),
        ]
        specs.append([*ps, *body(n)])
    found = find_furniture(pages_of(specs), PROFILE, grids={n: [box] for n in (1, 2, 3)})
    assert {f.key for f in found.lines} == {"Acme Doc", "Fees Revision"}
    assert len(found.lines) == 6


def test_FT7_a_footer_in_three_parts_nearest_the_edge_breaks_no_run() -> None:
    specs = []
    for n in (1, 2, 3):
        parts = [
            P("Acme", 72, 745),
            P("Confidential", 280, 745),
            *text_line(["Page", str(n)], x=500, y=745),
        ]
        specs.append([*body(n), *header("Copyright 2026 Acme Exchange.", y=728), *parts])
    found = find_furniture(pages_of(specs), PROFILE)
    assert marked(found) == [(n, "footer", "Copyright 2026 Acme Exchange.") for n in (1, 2, 3)]


# --- One-page furniture, S3 (docs/specs/19-ocr-benchmark-fixes.md section 1) -------------------


def one_page(*ps: P) -> tuple[PageModel, ...]:
    return pages_of([list(ps)])


def test_FP1_a_one_page_footer_with_a_page_number_is_furniture() -> None:
    found = find_furniture(one_page(*body(1), *header("Page 1 of 1", y=750)), PROFILE)
    assert marked(found) == [(1, "footer", "Page 1 of 1")]


def test_FP2_a_running_head_ending_in_a_page_number_is_furniture() -> None:
    found = find_furniture(one_page(*header("Journal of Things 12"), *body(1)), PROFILE)
    assert marked(found) == [(1, "header", "Journal of Things 12")]


@pytest.mark.parametrize("number", [[P("7", 300, 750)], text_line(["-", "7", "-"], x=290, y=750)])
def test_FP3_a_lone_page_number_is_furniture(number: list[P]) -> None:
    found = find_furniture(one_page(*body(1), *number), PROFILE)
    assert [(f.role, " ".join(w.text for w in f.line.words)) for f in found.lines] == [
        ("page_number", " ".join(p.text for p in number))
    ]


def test_FP4_a_running_head_in_smaller_type_is_furniture() -> None:
    head = text_line(["Annals", "of", "Things"], x=72, y=40, size=7)
    assert marked(find_furniture(one_page(*head, *body(1)), PROFILE)) == [
        (1, "header", "Annals of Things")
    ]


def test_FP5_a_title_in_body_type_without_a_number_is_not_furniture() -> None:
    assert find_furniture(one_page(*header("Annals of Things"), *body(1)), PROFILE).lines == ()


def test_FP6_a_page_number_close_under_the_body_is_not_furniture() -> None:
    # The last body line ends at y = 290; `Page 2` sits 5 pt under it, less than a line's height.
    assert find_furniture(one_page(*body(1), *header("Page 2", y=295)), PROFILE).lines == ()


def test_FP7_a_ruled_tables_last_row_is_not_furniture() -> None:
    cells = [Rect(72, 700, 200, 720), Rect(200, 700, 330, 720)]
    cells += [Rect(72, 720, 200, 740), Rect(200, 720, 330, 740)]
    table = [P("Fee", 80, 705), P("Rate", 210, 705), P("Total", 80, 725), P("12", 210, 725)]
    pages = one_page(*body(1), *table)
    assert marked(find_furniture(pages, PROFILE)) == [(1, "footer", "Total 12")]
    assert find_furniture(pages, PROFILE, grids={1: [cells]}).lines == ()


def test_FP8_larger_type_prints_its_role_only_by_a_page_number() -> None:
    title = text_line(["Annals", "of", "Things"], x=72, y=40, size=14)
    foot = [*text_line(["Annals", "page"], x=72, y=750, size=12), P("9", 520, 750, size=12)]
    found = find_furniture(one_page(*title, *body(1), *foot), PROFILE)
    assert marked(found) == [(1, "footer", "Annals page 9")]


def test_FP9_a_page_of_three_lines_has_no_furniture() -> None:
    ps = [*header("alpha beta", y=200), *header("gamma delta", y=240), *header("Page 1", y=750)]
    assert find_furniture(one_page(*ps), PROFILE).lines == ()


def test_FP10_only_a_bands_outermost_line_can_be_furniture() -> None:
    second = text_line(["Volume", "two"], x=72, y=60, size=7)
    ps = [*header("Annals of Things"), *second, *body(1)]
    assert find_furniture(one_page(*ps), PROFILE).lines == ()


@pytest.mark.parametrize("label", ["(4)", "*"])
def test_FP11_a_footnote_in_note_type_is_not_furniture(label: str) -> None:
    note = text_line([label, "Applies", "to", "members"], x=72, y=750, size=7)
    assert find_furniture(one_page(*body(1), *note), PROFILE).lines == ()


def test_FP12_a_note_the_page_calls_is_not_furniture() -> None:
    note = text_line(["1", "Supported", "by", "grant"], x=72, y=750, size=7)
    call = P("1", 250, 197, size=6, superscript=True)
    assert find_furniture(one_page(*body(1), call, *note), PROFILE).lines == ()
    assert marked(find_furniture(one_page(*body(1), *note), PROFILE)) == [
        (1, "footer", "1 Supported by grant")
    ]


def test_FP13_a_numbered_item_is_not_furniture() -> None:
    item = header("3. The driver sightlines")
    assert find_furniture(one_page(*item, *body(1)), PROFILE).lines == ()


def test_FP14_a_year_is_no_page_number() -> None:
    title = header("Annual Report 2022")
    assert find_furniture(one_page(*title, *body(1)), PROFILE).lines == ()


def test_FP15_a_two_page_document_keeps_recurrence() -> None:
    specs = [[*body(1), *header("Page 1", y=750)], body(2)]
    assert find_furniture(pages_of(specs), PROFILE).lines == ()


def prose(y: float, *, size: float = 10.0, lines: int = 6) -> list[P]:
    """Single-spaced body lines, 14 pt apart, each a different run of letters."""
    out: list[P] = []
    for i in range(lines):
        words = [f"w{i}{j}" + "abcde"[j % 5] for j in range(8)]
        out += text_line(words, x=72, y=y + 14 * i, size=size)
    return out


def three_cells(y: float, cells: tuple[str, str, str], size: float = 10.0) -> list[P]:
    return [P(text, x, y, size=size) for text, x in zip(cells, (72, 250, 400), strict=True)]


def widget_rows(y: float) -> list[P]:
    """Six 10 pt rows of a three-column table, 14 pt apart."""
    return [
        p
        for i in range(6)
        for p in three_cells(y + 14 * i, (f"Widget{i}", f"{i + 2}", f"{i + 1}.50"))
    ]


@pytest.mark.parametrize(
    "ps",
    [
        # 8 pt fee rows 18 pt apart at the foot, under the body
        [
            *prose(120),
            *[
                p
                for i in range(5)
                for p in three_cells(230 + 18 * i, (f"Service{i}", f"{i + 2}", f"{i + 1}.50"), 8)
            ],
        ],
        # the table's 8 pt header row is the page's top line
        [*three_cells(40, ("Item", "Quantity", "Price"), 8), *widget_rows(58)],
        # its total row is set apart at the foot
        [
            *three_cells(40, ("Item", "Quantity", "Price")),
            *widget_rows(58),
            *three_cells(158, ("Total", "21.00", "27")),
        ],
    ],
    ids=["fee-rows-at-the-foot", "header-row-at-the-top", "total-row-at-the-foot"],
)
def test_FP17_a_table_row_at_a_one_page_edge_is_not_furniture(ps: list[P]) -> None:
    assert find_furniture(one_page(*ps), PROFILE).lines == ()


@pytest.mark.parametrize("label", ["(1)", "1.", "*"])
def test_FP18_a_footnote_just_under_body_size_is_not_furniture(label: str) -> None:
    note = text_line([label, "Prices", "exclude", "VAT"], x=72, y=300, size=10)
    assert find_furniture(one_page(*prose(120, size=11), *note), PROFILE).lines == ()


@pytest.mark.parametrize(
    ("text", "size", "y"),
    [
        ("Jane Doe, MD", 16, 40),
        ("Appendix C", 14, 40),
        ("Office of the Mayor, Washington, DC", 10, 40),
        ("Homework 3", 16, 40),
        ("Form 1040", 14, 40),
        ("12 March 2024", 10, 40),
        ("Overall width 120 cm", 10, 300),
        ("I certify that the statements above are true", 10, 300),
    ],
)
def test_FP20_a_title_date_or_closing_line_is_not_furniture(
    text: str, size: float, y: float
) -> None:
    line = text_line(text.split(), x=72, y=y, size=size)
    assert find_furniture(one_page(*line, *prose(120)), PROFILE).lines == ()


def test_FP21_a_number_set_apart_from_a_head_in_larger_type_still_prints_its_role() -> None:
    head = [*text_line(["Annals", "of", "Things"], x=72, y=40, size=12), P("153", 520, 40, size=12)]
    assert marked(find_furniture(one_page(*head, *prose(120)), PROFILE)) == [
        (1, "header", "Annals of Things 153")
    ]


@pytest.mark.parametrize("text", ["Page 2 of 28", "1 of 14", "- Page 5 of 5 -"])
def test_FP23_a_page_count_in_heading_type_is_furniture(text: str) -> None:
    foot = text_line(text.split(), x=72, y=750, size=10)
    assert marked(find_furniture(one_page(*prose(120, size=8), *foot), PROFILE)) == [
        (1, "footer", text)
    ]


def test_FP22_a_footer_in_three_parts_under_prose_is_furniture() -> None:
    parts = [
        P("Acme", 72, 750, size=8),
        P("Confidential", 280, 750, size=8),
        P("Page", 500, 750, size=8),
    ]
    parts.append(P("3", 522, 750, size=8))
    assert marked(find_furniture(one_page(*prose(120), *parts), PROFILE)) == [
        (1, "footer", "Acme Confidential Page 3")
    ]


@pytest.mark.parametrize("token", ["7", "xii", "2/5", "[4]", "|81", "0004"])
def test_FP_page_number_tokens(token: str) -> None:
    assert page_number_token(token)


@pytest.mark.parametrize("token", ["2020", "1999", "3.", "(4)", "a)", "civil", "12345", "1/22222"])
def test_FP_tokens_that_are_no_page_number(token: str) -> None:
    assert not page_number_token(token)


@pytest.mark.parametrize(
    ("text", "prints"),
    [
        ("- 7 -", True),
        ("Page 2 of 5", True),
        ("1 / 1", True),
        ("Vacuum 83", True),
        ("34 Observer #7", True),
        ("(4) Applies", False),
        ("Annual Report 2022", False),
        ("Annals of Things", False),
        ("xii", True),
        ("- iv -", True),
        ("Appendix C", False),
        ("Jane Doe, MD", False),
        ("I certify that", False),
        ("Overall width 120 cm", False),
        ("12 March 2024", False),
    ],
)
def test_FP_lines_that_print_a_page_number(text: str, prints: bool) -> None:
    line = Line(place(text_line(text.split(), x=72, y=100)))
    assert prints_page_number(line) is prints
