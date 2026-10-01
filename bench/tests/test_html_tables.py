from hypothesis import given
from hypothesis import strategies as st
from inkgrid_bench.html_tables import cells_from_html

from inkgrid_bench.tables import NCell, NTable


def test_HT1_spans_and_header_cells() -> None:
    html = (
        "<table><thead><tr><th colspan=2>Fees</th></tr></thead><tbody>"
        "<tr><td rowspan=2>A</td><td>1</td></tr><tr><td>2</td></tr></tbody></table>"
    )
    assert cells_from_html(html) == [
        NCell(0, 0, 1, 2, "Fees", header=True),
        NCell(1, 0, 2, 1, "A"),
        NCell(1, 1, 1, 1, "1"),
        NCell(2, 1, 1, 1, "2"),
    ]


def test_HT2_text_is_decoded_and_bad_spans_are_one() -> None:
    html = (
        "<table><tr><td>a &amp; <b>b</b></td><td rowspan='x'>c<br>d</td>"
        "<td colspan='0'>  e \n  f </td></tr></table>"
    )
    assert cells_from_html(html) == [
        NCell(0, 0, 1, 1, "a & b"),
        NCell(0, 1, 1, 1, "c d"),
        NCell(0, 2, 1, 1, "e f"),
    ]


def test_HT3_clipped_spans_stopped_overlaps_and_no_table() -> None:
    past = "<table><tr><td rowspan=3>A</td><td>1</td></tr><tr><td>2</td></tr></table>"
    assert cells_from_html(past)[0] == NCell(0, 0, 2, 1, "A")
    # Row 1's colspan=2 starts at column 0 and runs into the rowspan from row 0 at column 1.
    overlap = "<table><tr><td>x</td><td rowspan=2>y</td></tr><tr><td colspan=2>z</td></tr></table>"
    assert cells_from_html(overlap) == [
        NCell(0, 0, 1, 1, "x"),
        NCell(0, 1, 2, 1, "y"),
        NCell(1, 0, 1, 1, "z"),
    ]
    assert cells_from_html("<table></table>") == []
    assert cells_from_html("<p>no table</p>") == []


spans = st.integers(min_value=0, max_value=4)
cell = st.tuples(st.sampled_from(["td", "th"]), spans, spans, st.text("ab ", max_size=3))


@given(st.lists(st.lists(cell, min_size=0, max_size=4), min_size=1, max_size=5))
def test_HT4_cells_never_cover_a_position_twice(
    rows: list[list[tuple[str, int, int, str]]],
) -> None:
    html = (
        "<table>"
        + "".join(
            "<tr>"
            + "".join(f"<{t} rowspan={r} colspan={c}>{x}</{t}>" for t, r, c, x in row)
            + "</tr>"
            for row in rows
        )
        + "</table>"
    )
    cells = cells_from_html(html)
    NTable.filled(page=1, bbox=(0, 0, 1, 1), cells=cells)  # raises on a position covered twice
    assert all(c.rows >= 1 and c.cols >= 1 for c in cells)
