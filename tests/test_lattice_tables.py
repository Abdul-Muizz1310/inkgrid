from collections.abc import Mapping, Sequence

import pdf_factory
from inkgrid.core.tables.lattice import TableStage, lattice_tables
from inkgrid.core.tables.proto import ProtoTable, missing_header
from inkgrid.core.text import block_text
from inkgrid.model.config import Profile
from inkgrid.model.findings import FindingCode
from inkgrid.model.geometry import Rect
from inkgrid.model.page import Word
from layout_builder import CHAR_EM, P, place, text_line
from model_builders import mk_page

PROFILE = Profile()
Box = tuple[float, float, float, float]


def centred(text: str, box: Box, *, bold: bool = False, size: float = 9.0) -> P:
    x0, y0, x1, y1 = box
    width = CHAR_EM * size * len(text)
    return P(text, (x0 + x1 - width) / 2, (y0 + y1 - size) / 2, size=size, bold=bold)


def run(
    cells: Mapping[str, Box],
    *,
    extra: Sequence[P] = (),
    grids: Sequence[Sequence[Rect]] | None = None,
    read: bool = True,
    bold: bool = False,
) -> tuple[TableStage, tuple[Word, ...]]:
    words = place([*(centred(t, b, bold=bold) for t, b in cells.items()), *extra])
    page = mk_page(words=words)
    grid = [Rect(*b) for b in cells.values()]
    stage = lattice_tables(
        page, [grid] if grids is None else grids, words, PROFILE, frame=0, read=read
    )
    return stage, words


def texts(table: ProtoTable) -> list[tuple[int, int, int, int, str]]:
    return [
        (c.cell.row, c.cell.col, c.cell.row_span, c.cell.col_span, block_text(c.lines)[0])
        for c in table.cells
    ]


def test_LT1_the_ruled_grid_becomes_one_table() -> None:
    stage, words = run(pdf_factory.RULED_GRID_CELLS)
    (table,) = stage.tables
    assert (table.shape.row_edges[-1], len(table.shape.cells)) == (180, 10)
    assert (0, 1, 1, 2, "Rate") in texts(table)
    assert (1, 0, 2, 1, "Equity") in texts(table)
    assert table.header_rows == 1
    assert stage.claimed == frozenset(w.id for w in words)


def test_LT2_a_grid_that_is_not_a_table_claims_nothing() -> None:
    one_row = {"a": (72, 100, 172, 120), "b": (172, 100, 272, 120)}
    one_col = {"a": (72, 100, 172, 120), "b": (72, 120, 172, 140)}
    for cells in (one_row, one_col):
        stage, _ = run(cells)
        assert (stage.tables, stage.claimed) == ((), frozenset())
    lonely = {"Sensitivity": (72, 100, 272, 120)}
    grid = [
        Rect(72, 100, 272, 120),
        Rect(272, 100, 372, 120),
        Rect(72, 120, 272, 140),
        Rect(272, 120, 372, 140),
    ]
    stage, _ = run(lonely, grids=[grid])
    assert stage.tables == ()


def test_LT3_a_centre_on_an_interior_edge_goes_right() -> None:
    cells = {
        "Fee": (72, 100, 172, 120),
        "Cap": (172, 100, 272, 120),
        "a": (72, 120, 172, 140),
        "b": (172, 120, 272, 140),
    }
    edge_word = P("xy", 172 - CHAR_EM * 9, 125, size=9)  # centre x exactly 172
    stage, _ = run(cells, extra=[edge_word])
    (table,) = stage.tables
    holder = next(
        c for c in table.cells if any(w.text == "xy" for line in c.lines for w in line.words)
    )
    assert (holder.cell.row, holder.cell.col) == (1, 1)


def test_LT4_a_caption_row_is_a_header_and_a_banner() -> None:
    cells = {
        "Transaction": (72, 100, 372, 120),
        "Service": (72, 120, 222, 140),
        "Fee": (222, 120, 372, 140),
        "Order": (72, 140, 222, 160),
        "0.10": (222, 140, 372, 160),
    }
    (table,) = run(cells)[0].tables
    assert (table.header_rows, table.banner_rows) == (2, (0,))


def test_LT5_a_banner_below_the_header_is_not_a_header() -> None:
    cells = {
        "Description": (72, 100, 172, 120),
        "Type": (172, 100, 272, 120),
        "Fee": (272, 100, 372, 120),
        "Disk": (72, 120, 372, 140),
        "Months": (72, 140, 172, 160),
        "Monthly": (172, 140, 272, 160),
        "R0.00": (272, 140, 372, 160),
    }
    (table,) = run(cells)[0].tables
    assert (table.header_rows, table.banner_rows) == (1, (1,))


def test_LT6_a_table_opening_with_values_has_no_header() -> None:
    cells = {
        "0.10": (72, 100, 172, 120),
        "0.20": (172, 100, 272, 120),
        "0.30": (72, 120, 172, 140),
        "0.40": (172, 120, 272, 140),
    }
    stage, _ = run(cells)
    assert stage.tables[0].header_rows == 0
    assert stage.findings == ()  # raised in the pipeline, after continuation (spec 09 s. 4)
    assert [f.code for f in missing_header(stage.tables[0])] == [FindingCode.HEADER_NOT_FOUND]


def test_LT7_a_word_across_a_column_rule_is_reported() -> None:
    cells = {
        "Fee": (72, 100, 172, 120),
        "Cap": (172, 100, 272, 120),
        "a": (72, 120, 172, 140),
        "b": (172, 120, 272, 140),
    }
    long_word = P(
        "abcdefghijklmnopqrs", 172 + 3 - CHAR_EM * 9 * 19, 125, size=9
    )  # ends 3 pt past x = 172
    stage, _ = run(cells, extra=[long_word])
    crossing = [f for f in stage.findings if f.code is FindingCode.WORD_CROSSES_RULE]
    assert len(crossing) == 1
    assert "1 word" in crossing[0].detail


def test_LT8_a_page_camelot_read_without_a_grid_is_a_disagreement() -> None:
    stage, _ = run({"a": (72, 100, 172, 120)}, grids=[])
    assert [(f.code, f.page) for f in stage.findings] == [(FindingCode.LATTICE_DISAGREES, 1)]
    unread, _ = run({"a": (72, 100, 172, 120)}, grids=[], read=False)
    assert unread.findings == ()


def test_LT9_a_hyphenated_cell_closes_up() -> None:
    cells = {
        "Fee": (72, 100, 172, 140),
        "Cap": (172, 100, 272, 140),
        "a": (72, 140, 172, 160),
        "b": (172, 140, 272, 160),
    }
    wrapped = [P("execu-", 80, 110, size=9), P("tions", 80, 122, size=9)]
    stage, _ = run(
        {k: v for k, v in cells.items() if k != "Fee"},
        extra=wrapped,
        grids=[[Rect(*b) for b in cells.values()]],
    )
    (table,) = stage.tables
    first = next(c for c in table.cells if (c.cell.row, c.cell.col) == (0, 0))
    text, joins = block_text(first.lines)
    assert text == "executions"
    assert len(joins) == 1


def test_LT10_a_table_of_text_has_a_header_only_when_bold() -> None:
    cells = {
        "Service": (72, 100, 172, 120),
        "Detail": (172, 100, 272, 120),
        "Order": (72, 120, 172, 140),
        "Entry": (172, 120, 272, 140),
    }
    stage, _ = run(cells)
    (plain,) = stage.tables
    assert plain.header_rows == 0
    (missing,) = missing_header(plain)  # raised in the pipeline, after continuation
    assert "no values" in missing.detail
    words = place([centred(t, b, bold=t in {"Service", "Detail"}) for t, b in cells.items()])
    stage = lattice_tables(
        mk_page(words=words),
        [[Rect(*b) for b in cells.values()]],
        words,
        PROFILE,
        frame=0,
        read=True,
    )
    assert stage.tables[0].header_rows == 1


def test_LT11_a_note_mark_on_a_fee_does_not_make_it_a_header() -> None:
    cells = {
        "Service": (72, 100, 222, 120),
        "Fee": (222, 100, 372, 120),
        "Adding": (72, 120, 222, 140),
        "$0.0030": (222, 120, 372, 140),
    }
    mark = P("1", 330, 122, size=5, superscript=True)
    (table,) = run(cells, extra=[mark])[0].tables
    assert table.header_rows == 1


def test_LT12_qualified_fees_are_values_and_numbered_labels_are_not() -> None:
    words = [
        *text_line(["Tier", "1"], x=80, y=105, size=9),
        *text_line(["Fee", "(47)"], x=230, y=105, size=9),
        *text_line(["{CK}", "$0.00"], x=80, y=125, size=9),
        *text_line(["$5,000", "per", "month"], x=230, y=125, size=9),
    ]
    grid = [
        Rect(72, 100, 222, 120),
        Rect(222, 100, 372, 120),
        Rect(72, 120, 222, 140),
        Rect(222, 120, 372, 140),
    ]
    placed = place(words)
    stage = lattice_tables(mk_page(words=placed), [grid], placed, PROFILE, frame=0, read=True)
    assert stage.tables[0].header_rows == 1


def prose_cell(tag: str, x: float, y: float, lines: int = 6) -> list[P]:
    """`lines` lines of seven words at 9 pt, 12 pt apart."""
    return [
        p
        for i in range(lines)
        for p in text_line([f"{tag}{i}{j}" for j in range(7)], x=x, y=y + 12 * i, size=9)
    ]


def test_LT13_a_ruled_page_layout_of_prose_is_not_a_table() -> None:
    grid = [Rect(40, 40, 572, 70), Rect(40, 70, 306, 160), Rect(306, 70, 572, 160)]
    title = text_line(["Official", "Bulletin"], x=50, y=50, size=9)
    columns = place([*title, *prose_cell("l", 50, 80), *prose_cell("r", 316, 80)])
    stage = lattice_tables(mk_page(words=columns), [grid], columns, PROFILE, frame=0, read=True)
    assert (stage.tables, stage.claimed) == ((), frozenset())
    values = place([*title, *prose_cell("l", 50, 80), *text_line(["0.10"], x=316, y=80, size=9)])
    stage = lattice_tables(mk_page(words=values), [grid], values, PROFILE, frame=0, read=True)
    assert len(stage.tables) == 1
    short = place([*title, *prose_cell("l", 50, 80, lines=4), *prose_cell("r", 316, 80, lines=4)])
    stage = lattice_tables(mk_page(words=short), [grid], short, PROFILE, frame=0, read=True)
    assert len(stage.tables) == 1


def test_LT14_rotated_text_in_a_cell_reads_in_its_own_order() -> None:
    cells = {"a": (172, 100, 272, 160), "0.10": (72, 160, 172, 180), "0.20": (172, 160, 272, 180)}
    # Bottom-to-top text: the first word sits lower on the page than the second.
    rotated = [
        P("Maker", 110, 140, size=9, horizontal=False),
        P("fee", 110, 110, size=9, horizontal=False),
    ]
    grid = [Rect(72, 100, 172, 160), *(Rect(*b) for b in cells.values())]
    stage, _ = run(cells, extra=rotated, grids=[grid])
    (table,) = stage.tables
    first = next(c for c in table.cells if (c.cell.row, c.cell.col) == (0, 0))
    assert block_text(first.lines)[0] == "Maker fee"


def test_LT15_the_header_reaches_down_to_its_merged_cells() -> None:
    cells = {
        "Description": (72, 100, 172, 140),  # spans rows 0-1
        "Fee": (172, 100, 272, 120),
        "$5": (172, 120, 272, 140),
        "Order": (72, 140, 172, 160),
        "$6": (172, 140, 272, 160),
    }
    (table,) = run(cells)[0].tables
    assert table.header_rows == 2


def test_LT16_an_empty_cell_spanning_the_body_does_not_make_it_header() -> None:
    cells = {
        "Tier": (72, 100, 172, 120),
        "Fee": (172, 100, 272, 120),
        "Band": (72, 120, 172, 140),
        "$5": (172, 120, 272, 140),
        "Other": (72, 140, 172, 160),
        "$6": (172, 140, 272, 160),
    }
    sliver = Rect(272, 100, 280, 160)  # an empty column past the last, spanning every row (JSE p20)
    stage, _ = run(cells, grids=[[*(Rect(*b) for b in cells.values()), sliver]])
    (table,) = stage.tables
    assert table.header_rows == 1
