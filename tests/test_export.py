import pdf_factory
from doc_builder import B, C, W, build, line
from inkgrid.model.document import Table
from lattice_builder import read_with_tables

BULLET = "\u2022"


def test_MD1_each_kind_has_its_form() -> None:
    doc = build(
        [
            B("heading", line(["Title"], y=100), fields={"level": 2}),
            B("paragraph", line(["Text"], y=120)),
            B("list_item", line([BULLET, "item"], y=140), fields={"label": BULLET}),
            B("list_item", line(["1.", "first"], y=160), fields={"label": "1."}),
            B("footnote", line(["3", "note"], y=180), fields={"label": "3"}),
            B("furniture", line(["Page", "1"], y=700), fields={"role": "footer"}),
        ]
    )
    assert doc.to_markdown() == "## Title\n\nText\n\n- item\n\n1. first\n\n[^3]: note\n"


def test_MD2_printed_text_is_never_read_as_markdown() -> None:
    doc = build(
        [
            B("paragraph", line(["#", "of", "trades"], y=100)),
            B("paragraph", line(["-", "5", "bp"], y=120)),
            B("paragraph", line(["2026.", "A", "year"], y=140)),
        ]
    )
    assert doc.to_markdown() == "\\# of trades\n\n\\- 5 bp\n\n2026\\. A year\n"


def test_MD3_a_document_of_furniture_renders_empty() -> None:
    doc = build([B("furniture", line(["Page", "1"], y=700), fields={"role": "footer"})])
    assert doc.to_markdown() == ""


def test_MD4_heading_levels_stop_at_six() -> None:
    doc = build([B("heading", line(["Deep"], y=100), fields={"level": 9})])
    assert doc.to_markdown() == "###### Deep\n"


def test_MD5_a_definition_bolds_its_term() -> None:
    words = line(["Member", "a", "firm", "admitted", "to", "trading"], y=100)
    fields = {"term": "Member", "body": "a firm admitted to trading"}
    doc = build([B("definition", words, fields=fields)])
    assert doc.to_markdown() == "**Member** a firm admitted to trading\n"


def test_MD6_a_table_renders_as_its_text() -> None:
    table = B(
        "table",
        [W("Fee", 110, 105), W("0.10", 210, 105), W("Rebate", 110, 125), W("0.20", 210, 125)],
        row_bands=[(100, 120), (120, 140)],
        col_bands=[(100, 200), (200, 300)],
        cells=[C(0, 0, [0]), C(0, 1, [1]), C(1, 0, [2]), C(1, 1, [3])],
    )
    assert build([table]).to_markdown() == (
        "|  |  |\n| --- | --- |\n| Fee | 0.10 |\n| Rebate | 0.20 |\n"
    )


def test_MD7_block_openings_and_tags_are_escaped_everywhere() -> None:
    doc = build(
        [
            B("list_item", line([BULLET, "#", "of", "trades"], y=100), fields={"label": BULLET}),
            B("footnote", line(["3", "-", "see", "below"], y=120), fields={"label": "3"}),
            B("paragraph", line(["Use", "<script>", "here"], y=140)),
            B("heading", line(["Fees", "<b>"], y=160), fields={"level": 2}),
        ]
    )
    assert doc.to_markdown().split("\n\n") == [
        "- \\# of trades",
        "[^3]: \\- see below",
        "Use \\<script> here",
        "## Fees \\<b>\n",
    ]


def ruled_table() -> Table:
    """LT1's table: `Rate` over columns 1-2 of the header, `Equity` over rows 1-2."""
    doc = read_with_tables(pdf_factory.ruled_grid())
    (table,) = doc.tables()
    return table


def test_EX1_markdown_writes_a_merged_value_once() -> None:
    lines = ruled_table().to_markdown().split("\n")
    assert lines[0] == "| Fee | Rate |  |"
    assert lines[1] == "| --- | --- | --- |"
    assert lines[2] == "| Equity | 0.10 | 0.20 |"
    assert lines[3] == "|  | 0.30 | 0.40 |"
    assert "".join(lines).count("Equity") == 1


def test_EX2_html_carries_the_spans() -> None:
    html = ruled_table().to_html()
    assert '<th colspan="2">Rate</th>' in html
    assert '<td rowspan="2">Equity</td>' in html
    assert html.count("<th>") + html.count("<th ") == 2


def test_EX3_dense_rows_flag_every_copy() -> None:
    rows = ruled_table().to_rows()
    assert [len(r) for r in rows] == [3, 3, 3, 3]
    copies = {(c.row, c.col, c.text) for r in rows for c in r if c.copy}
    assert copies == {(0, 2, "Rate"), (2, 0, "Equity")}
    assert rows[1][0].text == "Equity"
    assert rows[1][0].copy is False


def test_EX4_cell_text_is_escaped_in_both_forms() -> None:
    table = B(
        "table",
        [
            W("a", 110, 105),
            W("|", 120, 105),
            W("b", 130, 105),
            W("<b>", 140, 105),
            W("0.1", 210, 105),
            W("x", 110, 125),
            W("0.2", 210, 125),
        ],
        row_bands=[(100, 120), (120, 140)],
        col_bands=[(100, 200), (200, 300)],
        cells=[C(0, 0, [0, 1, 2, 3]), C(0, 1, [4]), C(1, 0, [5]), C(1, 1, [6])],
    )
    (built,) = build([table]).tables()
    assert "a \\| b \\<b>" in built.to_markdown()
    assert "a | b &lt;b&gt;" in built.to_html()
