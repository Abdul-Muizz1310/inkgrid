import json
from collections.abc import Callable
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from doc_builder import B, C, W, as_json, build, from_json, line
from inkgrid.model.document import Document, Link, LinkEnd
from inkgrid.model.findings import Finding, FindingCode

ROOT = Path(__file__).resolve().parents[1]


def paragraph_doc() -> Document:
    return build([B("paragraph", line(["alpha", "beta"]))])


def table_2x2() -> B:
    return B(
        "table",
        [W("Fee", 110, 105), W("Cap", 210, 105), W("$0.40", 110, 125), W("$25", 210, 125)],
        row_bands=[(100, 120), (120, 140)],
        col_bands=[(100, 200), (200, 300)],
        cells=[C(0, 0, [0]), C(0, 1, [1]), C(1, 0, [2]), C(1, 1, [3])],
        header_rows=1,
    )


def continuation_doc() -> Document:
    parent = table_2x2()
    child = B(
        "table",
        [W("$0.50", 110, 105, page=2), W("$30", 210, 105, page=2)],
        row_bands=[(80, 100), (100, 120)],
        col_bands=[(100, 200), (200, 300)],
        cells=[
            C(0, 0, carried_text="Fee", source=((0, 0),)),
            C(0, 1, carried_text="Cap", source=((0, 1),)),
            C(1, 0, [0]),
            C(1, 1, [1]),
        ],
        header_rows=1,
    )
    link = Link(kind="continuation", from_=LinkEnd(block="b2"), to="b1", status="resolved")
    return build([parent, child], pages=2, links=[link])


def footnote_doc(**link: Any) -> Document:
    fields: dict[str, Any] = {
        "kind": "footnote_call",
        "from_": LinkEnd(block="b1"),
        "to": "b2",
        "label": "1",
        "method": "parenthetical",
        "status": "resolved",
    }
    fields.update(link)
    return build(
        [
            B("paragraph", line(["Rate", "(1)"])),
            B("footnote", line(["1", "Applies", "daily"], y=200), fields={"label": "1"}),
        ],
        links=[Link(**fields)],
    )


def broken(doc: Document, change: Callable[[dict[str, Any]], None]) -> None:
    data = as_json(doc)
    change(data)
    from_json(data)


# --- D1-D6: pages, partition, identity, text shape -------------------------------------------


def test_D1_minimal_document_is_valid_and_complete() -> None:
    doc = paragraph_doc()
    assert doc.complete
    assert doc.blocks[0].text == "alpha beta"
    assert doc.ledger.content_chars == 9


def test_D2_word_in_two_blocks_is_named() -> None:
    doc = build([B("paragraph", line(["alpha"])), B("paragraph", line(["beta"], y=120))])

    def change(d: dict[str, Any]) -> None:
        d["blocks"][1]["word_ids"].append(0)

    with pytest.raises(ValidationError, match="word 0 is in blocks b1 and b2"):
        broken(doc, change)


def test_D3_word_in_no_block_is_named() -> None:
    def change(d: dict[str, Any]) -> None:
        d["blocks"][0]["word_ids"] = [0]

    with pytest.raises(ValidationError, match="word 1 is in no block"):
        broken(paragraph_doc(), change)


@pytest.mark.parametrize(
    ("word_ids", "message"),
    [([0, 0, 1], "duplicate"), ([0, 1, 99], "word 99"), ([], "at least 1")],
    ids=["duplicate", "unknown", "empty"],
)
def test_D4_block_word_ids_must_be_real_and_unique(word_ids: list[int], message: str) -> None:
    def change(d: dict[str, Any]) -> None:
        d["blocks"][0]["word_ids"] = word_ids

    with pytest.raises(ValidationError, match=message):
        broken(paragraph_doc(), change)


def test_D5_block_ids_and_keys() -> None:
    doc = build([B("paragraph", line(["alpha"])), B("paragraph", line(["beta"], y=120))])

    def bad_id(d: dict[str, Any]) -> None:
        d["blocks"][0]["id"] = "b2"

    def same_key(d: dict[str, Any]) -> None:
        d["blocks"][1]["key"] = d["blocks"][0]["key"]

    with pytest.raises(ValidationError, match="block id"):
        broken(doc, bad_id)
    with pytest.raises(ValidationError, match="key"):
        broken(doc, same_key)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("alpha betaX", "characters"),
        ("alpha\tbeta", "whitespace"),
        ("alpha  beta", "whitespace"),
        (" alpha beta", "whitespace"),
    ],
    ids=["extra-char", "tab", "double-space", "leading-space"],
)
def test_D6_block_text_shape_and_characters(text: str, message: str) -> None:
    def change(d: dict[str, Any]) -> None:
        d["blocks"][0]["text"] = text

    with pytest.raises(ValidationError, match=message):
        broken(paragraph_doc(), change)


# --- D7-D9: hyphen joins ------------------------------------------------------------------------


def hyphen_doc(texts: list[str], text: str, joins: list[tuple[int, int]]) -> Document:
    return build([B("paragraph", line(texts), text=text, joins=joins)])


def test_D7_hyphen_join_accounts_for_the_dropped_hyphen() -> None:
    doc = hyphen_doc(["execu-", "tions"], "executions", [(0, 1)])
    assert doc.blocks[0].hyphen_joins == ((0, 1),)


def test_D8_text_without_its_join_fails() -> None:
    def change(d: dict[str, Any]) -> None:
        d["blocks"][0]["hyphen_joins"] = []

    with pytest.raises(ValidationError, match="characters"):
        broken(hyphen_doc(["execu-", "tions"], "executions", [(0, 1)]), change)


@pytest.mark.parametrize(
    ("texts", "text", "joins", "message"),
    [
        (["execu", "tions"], "executions", [(0, 1)], "hyphen"),
        (["execu-", "Tions"], "execuTions", [(0, 1)], "lower-case"),
        (["execu-", "tions"], "executions", [(0, 0)], "two different"),
    ],
    ids=["no-hyphen", "upper-case", "same-word"],
)
def test_D9_invalid_joins(
    texts: list[str], text: str, joins: list[tuple[int, int]], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        hyphen_doc(texts, text, joins)


def test_D9_join_naming_a_word_outside_the_block() -> None:
    doc = build(
        [
            B("paragraph", line(["execu-", "tions"]), text="executions", joins=[(0, 1)]),
            B("paragraph", line(["more"], y=120)),
        ]
    )

    def change(d: dict[str, Any]) -> None:
        d["blocks"][0]["hyphen_joins"] = [[0, 2]]

    with pytest.raises(ValidationError, match="outside"):
        broken(doc, change)


# --- D10-D12: regions ---------------------------------------------------------------------------


def test_D10_region_on_a_page_without_block_words() -> None:
    doc = build([B("paragraph", line(["alpha", "beta"]))], pages=2)

    def change(d: dict[str, Any]) -> None:
        d["blocks"][0]["regions"].append({"page": 2, "bbox": [0, 0, 10, 10]})

    with pytest.raises(ValidationError, match="region"):
        broken(doc, change)


def test_D10_word_outside_its_region() -> None:
    def change(d: dict[str, Any]) -> None:
        d["blocks"][0]["regions"][0]["bbox"] = [72, 100, 80, 110]

    with pytest.raises(ValidationError, match="outside"):
        broken(paragraph_doc(), change)


def test_D11_paragraph_across_two_pages() -> None:
    words = [*line(["the", "fee"], page=1, y=700), *line(["applies"], page=2, y=60)]
    doc = build([B("paragraph", words)], pages=2)
    assert [r.page for r in doc.blocks[0].regions] == [1, 2]


def test_D12_regions_out_of_order() -> None:
    words = [*line(["the", "fee"], page=1, y=700), *line(["applies"], page=2, y=60)]
    doc = build([B("paragraph", words)], pages=2)

    def change(d: dict[str, Any]) -> None:
        d["blocks"][0]["regions"].reverse()

    with pytest.raises(ValidationError, match="increasing"):
        broken(doc, change)


def test_D12_table_with_two_regions() -> None:
    def change(d: dict[str, Any]) -> None:
        region = d["blocks"][0]["regions"][0]
        d["blocks"][0]["regions"] = [region, {**region, "page": 2}]

    with pytest.raises(ValidationError, match="one region"):
        broken(build([table_2x2()], pages=2), change)


# --- D13-D21: grids and cells -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda g: g.update(n_rows=3), "row_bands"),
        (lambda g: g.update(col_bands=[[100, 210], [200, 300]]), "overlap"),
        (lambda g: g.update(col_bands=[[200, 300], [100, 200]]), "sorted"),
        (lambda g: g.update(header_rows=3), "header_rows"),
        (lambda g: g.update(banner_rows=[5]), "banner"),
        (lambda g: g.update(banner_rows=[1, 0]), "banner"),
    ],
    ids=["row-count", "overlap", "unsorted", "header-rows", "banner-range", "banner-order"],
)
def test_D13_D14_grid_shape(change: Callable[[dict[str, Any]], None], message: str) -> None:
    def apply(d: dict[str, Any]) -> None:
        change(d["blocks"][0]["grid"])

    with pytest.raises(ValidationError, match=message):
        broken(build([table_2x2()]), apply)


def test_D15_two_by_two_table_is_valid() -> None:
    doc = build([table_2x2()])
    table = doc.tables()[0]
    assert table.text == "Fee Cap\n$0.40 $25"
    assert [c.text for c in table.grid.cells] == ["Fee", "Cap", "$0.40", "$25"]


def cell_change(index: int, **fields: Any) -> Callable[[dict[str, Any]], None]:
    def apply(d: dict[str, Any]) -> None:
        d["blocks"][0]["grid"]["cells"][index].update(fields)

    return apply


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (cell_change(0, row_span=0), "greater than 0"),
        (cell_change(1, col_span=2), "bounds"),
        (cell_change(0, col_span=2), "covered twice"),
        (cell_change(0, row=1, col=1), "sorted"),
    ],
    ids=["zero-span", "past-edge", "overlap", "unsorted"],
)
def test_D16_cells_tile_the_grid(change: Callable[[dict[str, Any]], None], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        broken(build([table_2x2()]), change)


def test_D17_merged_cell_spans_two_rows() -> None:
    spec = B(
        "table",
        [W("Customer", 110, 115), W("$0.10", 210, 105), W("$0.11", 210, 125)],
        row_bands=[(100, 120), (120, 140)],
        col_bands=[(100, 200), (200, 300)],
        cells=[C(0, 0, [0], row_span=2), C(0, 1, [1]), C(1, 1, [2])],
    )
    grid = build([spec]).tables()[0].grid
    assert grid.cells[0].row_span == 2


def test_D18_carried_cell_owns_no_words_and_has_text() -> None:
    doc = continuation_doc()

    def with_words(d: dict[str, Any]) -> None:
        d["blocks"][1]["grid"]["cells"][0]["word_ids"] = [4]

    def empty_text(d: dict[str, Any]) -> None:
        d["blocks"][1]["grid"]["cells"][0]["text"] = ""

    with pytest.raises(ValidationError, match="carried"):
        broken(doc, with_words)
    with pytest.raises(ValidationError, match="carried"):
        broken(doc, empty_text)


def test_D19_table_word_in_no_cell() -> None:
    with pytest.raises(ValidationError, match="in no cell"):
        broken(build([table_2x2()]), cell_change(3, word_ids=[], text=""))


def test_D19_word_in_two_cells() -> None:
    with pytest.raises(ValidationError, match="two cells"):
        broken(build([table_2x2()]), cell_change(1, word_ids=[1, 0], text="Cap Fee"))


def test_D19_cell_word_from_outside_the_table() -> None:
    doc = build([table_2x2(), B("paragraph", line(["note"], y=300))])
    with pytest.raises(ValidationError, match="not a word of"):
        broken(doc, cell_change(3, word_ids=[3, 4], text="$25 note"))


def test_D20_cell_word_outside_its_cell() -> None:
    def swap(d: dict[str, Any]) -> None:
        block = d["blocks"][0]
        block.update(word_ids=[1, 0, 2, 3], text="Cap Fee\n$0.40 $25")
        block["grid"]["cells"][0].update(word_ids=[1], text="Cap")
        block["grid"]["cells"][1].update(word_ids=[0], text="Fee")

    with pytest.raises(ValidationError, match="outside cell"):
        broken(build([table_2x2()]), swap)


def test_D21_carried_cells_need_a_continuation_link() -> None:
    def drop_link(d: dict[str, Any]) -> None:
        d["links"] = []

    with pytest.raises(ValidationError, match="continuation"):
        broken(continuation_doc(), drop_link)


# --- D22-D26: links -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"from": {"block": "b7", "cell": None}}, "b7"),
        ({"to": "b9"}, "b9"),
        ({"to": None}, "resolved"),
        ({"status": "unresolved"}, "unresolved"),
        ({"status": "rejected", "to": None}, "reason"),
    ],
    ids=["unknown-from", "unknown-to", "resolved-without-to", "unresolved-with-to", "no-reason"],
)
def test_D22_link_references_and_status(fields: dict[str, Any], message: str) -> None:
    def change(d: dict[str, Any]) -> None:
        d["links"][0].update(fields)

    with pytest.raises(ValidationError, match=message):
        broken(footnote_doc(), change)


def test_D23_footnote_call_requires_label_method_and_a_footnote_target() -> None:
    with pytest.raises(ValidationError, match="label"):
        footnote_doc(label=None)
    with pytest.raises(ValidationError, match="method"):
        footnote_doc(method=None)

    def to_paragraph(d: dict[str, Any]) -> None:
        d["links"][0].update({"from": {"block": "b2", "cell": None}, "to": "b1"})

    with pytest.raises(ValidationError, match="footnote"):
        broken(footnote_doc(), to_paragraph)


def test_D24_continuation_rules() -> None:
    doc = continuation_doc()

    def with_method(d: dict[str, Any]) -> None:
        d["links"][0]["method"] = "named"

    def forward(d: dict[str, Any]) -> None:
        d["links"][0].update({"from": {"block": "b1", "cell": None}, "to": "b2"})

    def unresolved(d: dict[str, Any]) -> None:
        d["links"][0].update({"status": "unresolved", "to": None})

    with pytest.raises(ValidationError, match="method"):
        broken(doc, with_method)
    with pytest.raises(ValidationError, match="earlier"):
        broken(doc, forward)
    with pytest.raises(ValidationError, match="resolved"):
        broken(doc, unresolved)


def test_D24_continuation_between_table_and_paragraph() -> None:
    link = Link(kind="continuation", from_=LinkEnd(block="b2"), to="b1", status="resolved")
    with pytest.raises(ValidationError, match="table"):
        build(
            [B("paragraph", line(["alpha"])), B("paragraph", line(["beta"], y=120))],
            links=[link],
        )


def test_D25_link_cell_must_be_a_cell_anchor() -> None:
    link = Link(
        kind="footnote_call",
        from_=LinkEnd(block="b1", cell=(5, 5)),
        to=None,
        label="1",
        method="superscript",
        status="unresolved",
    )
    with pytest.raises(ValidationError, match="cell"):
        build([table_2x2()], links=[link])


def test_D26_valid_continuation() -> None:
    doc = continuation_doc()
    child = doc.tables()[1]
    assert [c.carried for c in child.grid.cells] == [True, True, False, False]
    assert child.text == "$0.50 $30"


# --- D27-D30: findings, ledger, helpers ---------------------------------------------------------


def test_D27_findings_reference_real_pages_and_blocks() -> None:
    doc = build([B("paragraph", line(["alpha"]))], pages=2)

    def page3(d: dict[str, Any]) -> None:
        d["findings"] = [
            json.loads(Finding.of(FindingCode.BLANK_PAGE, "x", page=3).model_dump_json())
        ]

    def block9(d: dict[str, Any]) -> None:
        f = Finding.of(FindingCode.CALL_UNRESOLVED, "x", block="b9")
        d["findings"] = [json.loads(f.model_dump_json())]

    with pytest.raises(ValidationError, match="page 3"):
        broken(doc, page3)
    with pytest.raises(ValidationError, match="b9"):
        broken(doc, block9)


def test_D28_ledger_must_balance() -> None:
    def content(d: dict[str, Any]) -> None:
        d["ledger"]["content_chars"] += 1

    def clipped(d: dict[str, Any]) -> None:
        d["ledger"]["clipped_chars"] = 1

    with pytest.raises(ValidationError, match="content_chars"):
        broken(paragraph_doc(), content)
    with pytest.raises(ValidationError, match="clipped_chars"):
        broken(paragraph_doc(), clipped)


def test_ledger_counts_furniture_separately() -> None:
    doc = build(
        [
            B("furniture", line(["Page", "1"], y=780), fields={"role": "footer"}),
            B("paragraph", line(["alpha"])),
        ]
    )
    assert (doc.ledger.content_chars, doc.ledger.furniture_chars) == (5, 5)


def test_D29_error_finding_makes_document_incomplete() -> None:
    doc = build(
        [B("paragraph", line(["alpha"]))],
        pages=2,
        findings=[Finding.of(FindingCode.NO_TEXT_LAYER, "image-only", page=2)],
    )
    assert not doc.complete


def test_D30_tables_in_reading_order() -> None:
    first = table_2x2()
    second = B(
        "table",
        [W("A", 110, 405), W("B", 210, 405)],
        row_bands=[(400, 420)],
        col_bands=[(100, 200), (200, 300)],
        cells=[C(0, 0, [0]), C(0, 1, [1])],
    )
    doc = build([first, B("paragraph", line(["between"], y=300)), second])
    assert [t.id for t in doc.tables()] == ["b1", "b3"]


# --- D31-D33: serialization and a partition property --------------------------------------------


@pytest.mark.parametrize(
    "make", [lambda: build([table_2x2()]), continuation_doc], ids=["table", "continuation"]
)
def test_D31_json_round_trip_is_canonical(make: Callable[[], Document]) -> None:
    doc = make()
    text = doc.model_dump_json()
    again = Document.model_validate_json(text)
    assert again == doc
    assert again.model_dump_json() == text


def test_D31_link_serializes_from_key() -> None:
    assert '"from":{"block":"b2"' in continuation_doc().model_dump_json()


def test_D32_document_schema_is_committed() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "export_schemas", ROOT / "scripts" / "export_schemas.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    committed = json.loads((ROOT / "docs" / "schema" / "document.schema.json").read_text("utf-8"))
    assert module.schemas()["document.schema.json"] == committed


@st.composite
def partitions(draw: st.DrawFn) -> list[list[str]]:
    n = draw(st.integers(min_value=1, max_value=12))
    letters = [chr(ord("a") + i) for i in range(n)]
    cuts = sorted(draw(st.sets(st.integers(1, n - 1), max_size=n - 1))) if n > 1 else []
    bounds = [0, *cuts, n]
    return [letters[a:b] for a, b in pairwise(bounds)]


@given(partitions())
def test_D33_random_partitions_validate_and_doubling_fails(groups: list[list[str]]) -> None:
    blocks = [B("paragraph", line(g, y=100 + 20 * i)) for i, g in enumerate(groups)]
    doc = build(blocks)
    assert sorted(w for b in doc.blocks for w in b.word_ids) == list(range(len(doc.words)))
    if len(doc.blocks) > 1:

        def double(d: dict[str, Any]) -> None:
            d["blocks"][1]["word_ids"].append(0)

        with pytest.raises(ValidationError, match="word 0 is in blocks"):
            broken(doc, double)


# --- D34-D45: the invariants the final M0 review found untested or too weak ----------------


def two_page_doc() -> Document:
    return build([B("paragraph", [*line(["alpha"], page=1), *line(["beta"], page=2)])], pages=2)


def test_D34_page_count_and_numbering() -> None:
    def count(d: dict[str, Any]) -> None:
        d["source"]["pages"] = 3

    def numbering(d: dict[str, Any]) -> None:
        d["pages"][1]["number"] = 1

    with pytest.raises(ValidationError, match="source says 3 pages"):
        broken(two_page_doc(), count)
    with pytest.raises(ValidationError, match="page number 1 at position 2"):
        broken(two_page_doc(), numbering)


def test_D35_word_ids_and_pages() -> None:
    def gap(d: dict[str, Any]) -> None:
        d["words"][1]["id"] = 2

    def backwards(d: dict[str, Any]) -> None:
        d["words"][0]["page"] = 2
        d["words"][1]["page"] = 1

    def beyond(d: dict[str, Any]) -> None:
        d["words"][1]["page"] = 3

    with pytest.raises(ValidationError, match="word id 2 where 1 was expected"):
        broken(two_page_doc(), gap)
    with pytest.raises(ValidationError, match="after a word on page 2"):
        broken(two_page_doc(), backwards)
    with pytest.raises(ValidationError, match="page 3 of 2"):
        broken(two_page_doc(), beyond)


def test_D36_text_layer_matches_the_words() -> None:
    doc = build([B("paragraph", line(["alpha"]))], pages=2)

    def none_with_words(d: dict[str, Any]) -> None:
        d["pages"][0]["text_layer"] = "none"

    def unmapped_but_full(d: dict[str, Any]) -> None:
        d["pages"][0]["unmapped_chars"] = 1

    with pytest.raises(ValidationError, match="text_layer"):
        broken(doc, none_with_words)
    with pytest.raises(ValidationError, match="text_layer"):
        broken(doc, unmapped_but_full)


@pytest.mark.parametrize(
    ("index", "text"), [(0, "FeeX"), (2, "04.$0")], ids=["extra-char", "scrambled"]
)
def test_D37_cell_text_must_be_its_words_in_order(index: int, text: str) -> None:
    with pytest.raises(ValidationError, match="text of cell"):
        broken(build([table_2x2()]), cell_change(index, text=text))


def test_D38_block_text_is_checked_in_order() -> None:
    with pytest.raises(ValidationError, match="characters"):
        build([B("paragraph", line(["12", "34"]), text="13 24")])


def test_D39_joins_are_unique_applied_and_adjacent() -> None:
    with pytest.raises(ValidationError, match="twice"):
        hyphen_doc(["execu-", "tions"], "executions", [(0, 1), (0, 1)])
    with pytest.raises(ValidationError, match="characters"):
        hyphen_doc(["execu-", "tions"], "execu- tions", [(0, 1)])
    with pytest.raises(ValidationError, match="follow"):
        build(
            [
                B(
                    "paragraph",
                    line(["execu-", "big", "tions"]),
                    text="executions big",
                    joins=[(0, 2)],
                )
            ]
        )


def test_D40_keys_are_content_derived() -> None:
    doc = build([B("paragraph", line(["alpha"])), B("paragraph", line(["beta"], y=120))])

    def fake(d: dict[str, Any]) -> None:
        d["blocks"][0]["key"] = "k0000000000000000"

    def suffixed(d: dict[str, Any]) -> None:
        d["blocks"][0]["key"] += ":7"

    with pytest.raises(ValidationError, match="key"):
        broken(doc, fake)
    with pytest.raises(ValidationError, match="key"):
        broken(doc, suffixed)


@pytest.mark.parametrize(
    "spec",
    [
        B("list_item", line(["\u2022", "item"]), fields={"label": "-"}),
        B("footnote", line(["1", "note"]), fields={"label": "9"}),
        B("heading", line(["2.1", "Fees"]), fields={"level": 1, "number": "3"}),
        B("definition", line(["Term", "body", "text"]), fields={"term": "Term", "body": "other"}),
    ],
    ids=["list-label", "footnote-label", "heading-number", "definition-split"],
)
def test_D41_kind_fields_come_from_the_text(spec: B) -> None:
    with pytest.raises(ValidationError, match=r"label|number|term"):
        build([spec])


def test_D41_valid_kind_fields() -> None:
    doc = build(
        [
            B("list_item", line(["\u2022", "item"]), fields={"label": "\u2022"}),
            B("footnote", line(["(1)", "note"], y=120), fields={"label": "1"}),
            B("heading", line(["2.1", "Fees"], y=140), fields={"level": 1, "number": "2.1"}),
            B(
                "definition",
                line(["Term", "body", "text"], y=160),
                fields={"term": "Term", "body": "body text"},
            ),
        ]
    )
    assert [b.kind for b in doc.blocks] == ["list_item", "footnote", "heading", "definition"]


def test_D42_blank_cells_are_representable() -> None:
    blank_corner = B(
        "table",
        [W("Fee", 110, 105), W("Cap", 210, 105), W("$0.40", 110, 125)],
        row_bands=[(100, 120), (120, 140)],
        col_bands=[(100, 200), (200, 300)],
        cells=[C(0, 0, [0]), C(0, 1, [1]), C(1, 0, [2]), C(1, 1, [])],
    )
    blank_merged = B(
        "table",
        [W("$0.10", 210, 105), W("$0.11", 210, 125)],
        row_bands=[(100, 120), (120, 140)],
        col_bands=[(100, 200), (200, 300)],
        cells=[C(0, 0, [], row_span=2), C(0, 1, [0]), C(1, 1, [1])],
    )
    doc = build([blank_corner, B("paragraph", line(["gap"], y=200)), blank_merged])
    assert doc.tables()[0].grid.cells[3].text == ""
    assert doc.tables()[1].grid.cells[0].row_span == 2


def test_D43_every_position_is_covered() -> None:
    spec = B(
        "table",
        [W("Fee", 110, 105), W("Cap", 210, 105), W("$0.40", 110, 125)],
        row_bands=[(100, 120), (120, 140)],
        col_bands=[(100, 200), (200, 300)],
        cells=[C(0, 0, [0]), C(0, 1, [1]), C(1, 0, [2])],
    )
    with pytest.raises(ValidationError, match=r"position \(1, 1\) is covered by no cell"):
        build([spec])


def test_D44_carried_cells_copy_the_parent_header() -> None:
    def not_header(d: dict[str, Any]) -> None:
        d["blocks"][1]["grid"]["cells"][0]["source"] = [[1, 0]]
        d["blocks"][1]["grid"]["cells"][0]["text"] = "$0.40"

    def invented(d: dict[str, Any]) -> None:
        d["blocks"][1]["grid"]["cells"][0]["text"] = "Rebate"

    with pytest.raises(ValidationError, match="header"):
        broken(continuation_doc(), not_header)
    with pytest.raises(ValidationError, match="carried"):
        broken(continuation_doc(), invented)


def test_D45_altered_copies_cannot_slip_in() -> None:
    doc = paragraph_doc()
    bad = doc.words[0].model_copy(update={"size": -3.0})
    with pytest.raises(ValidationError):
        Document(**{**dict(doc), "words": (bad, *doc.words[1:])})


def test_D45_a_page_model_is_not_a_page_info() -> None:
    from model_builders import mk_page

    doc = paragraph_doc()
    page = mk_page(words=doc.words)
    with pytest.raises(ValidationError):
        Document(**{**dict(doc), "pages": (page,)})
