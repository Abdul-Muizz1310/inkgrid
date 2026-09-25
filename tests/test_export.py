from doc_builder import B, C, W, build, line

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
    assert build([table]).to_markdown() == "Fee 0.10\nRebate 0.20\n"
