from typing import Any

import pytest

from inkgrid_bench.heavy import docling_tables, marker_tables, unstructured_tables
from inkgrid_bench.tables import NCell, NPage, NTable

UPRIGHT = (NPage(box=(0.0, 0.0, 612.0, 792.0), rotation=0),)
TURNED = (NPage(box=(0.0, 0.0, 612.0, 792.0), rotation=90),)  # displays 792 x 612
# A table displayed at (66, 84)-(546, 304) on the turned page sits here on the unrotated page.
TURNED_BACK = (84.0, 246.0, 304.0, 726.0)
CELLS = (NCell(0, 0, 1, 2, "Fees", header=True), NCell(1, 0, 1, 1, "A"), NCell(1, 1, 1, 1, "1"))
HTML = "<table><tr><th colspan=2>Fees</th></tr><tr><td>A</td><td>1</td></tr></table>"


def docling_cell(
    row: int, col: int, cols: int, text: str, *, header: bool = False
) -> dict[str, Any]:
    return {
        "start_row_offset_idx": row,
        "start_col_offset_idx": col,
        "row_span": 1,
        "col_span": cols,
        "text": text,
        "column_header": header,
        "row_header": False,
    }


def docling_doc(size: tuple[float, float], box: dict[str, Any]) -> dict[str, Any]:
    cells = [
        docling_cell(0, 0, 2, "Fees", header=True),
        docling_cell(1, 0, 1, "A"),
        docling_cell(1, 1, 1, "1"),
    ]
    return {
        "pages": {"1": {"page_no": 1, "size": {"width": size[0], "height": size[1]}}},
        "tables": [{"prov": [{"page_no": 1, "bbox": box}], "data": {"table_cells": cells}}],
    }


def test_DC1_docling_cells_and_a_bottom_left_box() -> None:
    box = {"l": 100.0, "t": 700.0, "r": 300.0, "b": 600.0, "coord_origin": "BOTTOMLEFT"}
    (table,) = docling_tables(docling_doc((612.0, 792.0), box), UPRIGHT)
    assert table == NTable(page=1, bbox=(100.0, 92.0, 300.0, 192.0), cells=CELLS)


def test_DC2_a_docling_box_on_a_turned_page_is_turned_back() -> None:
    box = {"l": 66.0, "t": 528.0, "r": 546.0, "b": 308.0, "coord_origin": "BOTTOMLEFT"}
    (table,) = docling_tables(docling_doc((792.0, 612.0), box), TURNED)
    assert table.bbox == TURNED_BACK


def test_DC3_a_malformed_docling_export_is_the_documents_error() -> None:
    box = {"l": 100.0, "t": 700.0, "r": 300.0, "b": 600.0, "coord_origin": "BOTTOMLEFT"}
    doc = docling_doc((612.0, 792.0), box)
    del doc["tables"][0]["data"]["table_cells"][1]["row_span"]
    with pytest.raises(ValueError, match="row_span"):
        docling_tables(doc, UPRIGHT)
    centred = {**box, "coord_origin": "CENTER"}
    with pytest.raises(ValueError, match="CENTER"):
        docling_tables(docling_doc((612.0, 792.0), centred), UPRIGHT)


def marker_page(index: int, tables: list[tuple[str, list[float]]]) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = [
        {
            "id": f"/page/{index}/Text/0",
            "block_type": "Text",
            "html": "<p>x</p>",
            "bbox": [0, 0, 9, 9],
        }
    ]
    blocks += [
        {"id": f"/page/{index}/Table/{i + 1}", "block_type": "Table", "html": html, "bbox": bbox}
        for i, (html, bbox) in enumerate(tables)
    ]
    return {
        "id": f"/page/{index}/Page/7",
        "block_type": "Page",
        "bbox": [0, 0, 612, 792],
        "children": blocks,
    }


def test_MK1_marker_tables_on_their_page() -> None:
    rendered = {
        "block_type": "Document",
        "children": [
            marker_page(0, []),
            marker_page(
                1,
                [
                    (HTML, [100, 92, 300, 192]),
                    ("<table><tr><td>x</td></tr></table>", [10, 20, 30, 40]),
                ],
            ),
        ],
    }
    first, second = marker_tables(rendered, UPRIGHT * 2)
    assert first == NTable(page=2, bbox=(100.0, 92.0, 300.0, 192.0), cells=CELLS)
    assert (second.page, second.bbox, second.cells) == (
        2,
        (10.0, 20.0, 30.0, 40.0),
        (NCell(0, 0, 1, 1, "x"),),
    )


def test_MK2_a_marker_box_on_a_turned_page_is_turned_back() -> None:
    rendered = {
        "block_type": "Document",
        "children": [marker_page(0, [(HTML, [66, 84, 546, 304])])],
    }
    (table,) = marker_tables(rendered, TURNED)
    assert table.bbox == TURNED_BACK


def unstructured_table(points: list[list[float]], width: int, height: int) -> dict[str, Any]:
    return {
        "type": "Table",
        "metadata": {
            "coordinates": {
                "points": points,
                "system": "PixelSpace",
                "layout_width": width,
                "layout_height": height,
            },
            "text_as_html": HTML,
            "page_number": 1,
        },
    }


def test_US1_an_unstructured_box_is_scaled_from_pixels_to_points() -> None:
    page = (NPage(box=(0.0, 0.0, 595.0, 842.0), rotation=0),)
    points = [[200.0, 400.0], [200.0, 800.0], [600.0, 800.0], [600.0, 400.0]]
    other = {"type": "NarrativeText", "metadata": {"page_number": 1}}
    bare = unstructured_table(points, 1190, 1684)
    del bare["metadata"]["text_as_html"]  # its structure was not inferred: no cells, no table
    (table,) = unstructured_tables([other, bare, unstructured_table(points, 1190, 1684)], page)
    assert table == NTable(page=1, bbox=(100.0, 200.0, 300.0, 400.0), cells=CELLS)


def test_US2_an_unstructured_box_on_a_turned_page_is_scaled_then_turned_back() -> None:
    points = [[132.0, 168.0], [132.0, 608.0], [1092.0, 608.0], [1092.0, 168.0]]
    (table,) = unstructured_tables([unstructured_table(points, 1584, 1224)], TURNED)
    assert table.bbox == TURNED_BACK
