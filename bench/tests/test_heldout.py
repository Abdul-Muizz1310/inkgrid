import json
from typing import Any

import pytest

from inkgrid_bench.heldout import (
    Candidate,
    GlyphCell,
    access_paths,
    cer_counts,
    distance,
    glyph_sample,
    load_truth,
    require_verified,
    scored_pages,
    select,
)
from inkgrid_bench.scores.binding import AccessPath
from inkgrid_bench.tables import NCell, NTable


def candidate(doc_id: str, group: str) -> Candidate:
    return Candidate(id=doc_id, group=group, url=f"https://x/{doc_id}.pdf", sha256="0" * 64)


def test_SL1_one_document_per_group_by_numeric_pages_then_pages_then_name() -> None:
    cands = [
        candidate(n, g) for n, g in [("b", "A"), ("a", "A"), ("c", "A"), ("d", "B"), ("e", "B")]
    ]
    numeric = {"a": [1, 2], "b": [1, 2], "c": [1], "d": [1], "e": [2, 3, 4]}
    pages = {"a": 5, "b": 9, "c": 30, "d": 1, "e": 4}
    assert [c.id for c in select(cands, numeric, pages)] == ["b", "e"]


def test_SL2_scored_pages_are_seeded_sorted_and_at_most_three() -> None:
    first = scored_pages("x", [3, 5, 9, 12], seed="20261001")
    assert first == scored_pages("x", [12, 9, 5, 3], seed="20261001")
    assert len(first) == 3
    assert first == sorted(first)
    assert set(first) <= {3, 5, 9, 12}
    assert scored_pages("x", [7], seed="20261001") == [7]


def cell(
    row: int, col: int, text: str, box: list[float], *, rows: int = 1, cols: int = 1
) -> dict[str, Any]:
    return {"row": row, "col": col, "rows": rows, "cols": cols, "text": text, "box": box}


def fee_table() -> dict[str, Any]:
    """Two header rows (a group label over two columns), one stub column, two body rows."""
    return {
        "page": 2,
        "bbox": [0, 0, 300, 80],
        "header_rows": 2,
        "stub_cols": 1,
        "cells": [
            cell(0, 0, "Service", [0, 0, 100, 40], rows=2),
            cell(0, 1, "Fees (AUD)", [100, 0, 300, 20], cols=2),
            cell(1, 1, "Monthly", [100, 20, 200, 40]),
            cell(1, 2, "", [200, 20, 300, 40]),
            cell(2, 0, "Orders", [0, 40, 100, 60]),
            cell(2, 1, "4,715", [100, 40, 200, 60]),
            cell(2, 2, "0.31", [200, 40, 300, 60]),
            cell(3, 0, "", [0, 60, 100, 80]),
            cell(3, 1, "50", [100, 60, 200, 80]),
            cell(3, 2, "", [200, 60, 300, 80]),
        ],
    }


def truth_json(
    tables: list[dict[str, Any]],
    *,
    verified: bool = True,
    pages: list[int] | None = None,
    doc_id: str = "x",
) -> str:
    return json.dumps({
        "id": doc_id,
        "pages": pages or [2],
        "tables": tables,
        "drafted": {"by": "claude", "date": "2026-10-01"},
        "verified": {"by": "user", "date": "2026-10-02", "corrected": 0} if verified else None,
    })  # fmt: skip


def test_GT1_a_malformed_or_unverified_truth_is_refused() -> None:
    good = load_truth(truth_json([fee_table()]))
    assert good.tables[0].table().cells[1] == NCell(0, 1, 1, 2, "Fees (AUD)", header=True)
    overlap = fee_table()
    overlap["cells"][2]["cols"] = 2  # (1, 1) now also covers (1, 2)
    with pytest.raises(ValueError, match="covered twice"):
        load_truth(truth_json([overlap]))
    deep = fee_table()
    deep["header_rows"] = 1  # "Service" spans rows 0-1, from the header into the body
    with pytest.raises(ValueError, match="header rows into the body"):
        load_truth(truth_json([deep]))
    outside = fee_table()
    outside["cells"][6]["box"] = [200, 40, 320, 60]
    with pytest.raises(ValueError, match="outside its table"):
        load_truth(truth_json([outside]))
    with pytest.raises(ValueError, match="unscored page 2"):
        load_truth(truth_json([fee_table()], pages=[3]))
    with pytest.raises(ValueError, match="not verified"):
        require_verified(load_truth(truth_json([fee_table()], verified=False)))


def test_GT2_access_paths_take_labels_outer_to_leaf() -> None:
    (table,) = load_truth(truth_json([fee_table()])).tables
    assert access_paths(table) == [
        AccessPath("4,715", (("Orders",), ("Fees (AUD)", "Monthly"))),
        AccessPath("0.31", (("Orders",), ("Fees (AUD)",))),  # the empty header cell is skipped
        AccessPath("50", (("Fees (AUD)", "Monthly"),)),  # an empty stub cell: no row dimension
    ]


def test_GT3_a_value_without_labels_or_a_table_of_headers_has_no_path() -> None:
    one = [cell(0, 0, "1", [0, 0, 100, 20]), cell(0, 1, "2", [100, 0, 200, 20])]
    two = [cell(0, 0, "Fee", [0, 0, 100, 20]), cell(0, 1, "Cap", [100, 0, 200, 20])]
    bare = {"page": 2, "bbox": [0, 0, 200, 20], "header_rows": 0, "stub_cols": 0, "cells": one}
    heads = {"page": 2, "bbox": [0, 0, 200, 20], "header_rows": 1, "stub_cols": 0, "cells": two}
    truth = load_truth(truth_json([bare, heads]))
    assert [access_paths(t) for t in truth.tables] == [[], []]


def test_GS1_the_glyph_sample_is_seeded_and_takes_every_cell_when_fewer() -> None:
    truths = [load_truth(truth_json([fee_table()], doc_id=d)) for d in ("x", "y")]
    every = glyph_sample(truths, k=200, seed="20261001")
    assert len(every) == 2 * 7  # seven non-empty cells per table
    assert all(truths[0].tables[0].cells[c].text for _, _, c in every)
    some = glyph_sample(truths, k=5, seed="20261001")
    assert some == glyph_sample(truths, k=5, seed="20261001")
    assert len(set(some)) == 5


def tool_table(page: int, bbox: tuple[float, float, float, float], texts: list[str]) -> NTable:
    return NTable(
        page=page, bbox=bbox, cells=tuple(NCell(0, i, text=t) for i, t in enumerate(texts))
    )


def test_CE1_a_cells_error_is_its_distance_to_the_closest_cell_with_spaces_removed() -> None:
    assert distance("0.10%", "0.1O%") == 1
    assert distance("Removing10", "Removing 10") == 0  # whitespace is no glyph
    assert distance("abc", "") == 3
    truth = load_truth(truth_json([fee_table()]))
    cell = GlyphCell(doc="x", table=0, cell=6, text="0.10%")  # (2, 2), whose draft reads 0.31
    found = tool_table(2, (0, 0, 300, 80), ["0.1O%", "0.10 %", "fee"])
    other = tool_table(2, (400, 400, 500, 500), ["0.10%"])  # elsewhere on the page: not matched
    counts = cer_counts([cell], {"x": truth}, {"x": [found, other]})
    assert counts == {"x": {"chars": 5, "errors": 0}}
    worse = tool_table(2, (0, 0, 300, 80), ["0.1O%", "fee"])
    assert cer_counts([cell], {"x": truth}, {"x": [worse]}) == {"x": {"chars": 5, "errors": 1}}


def test_CE2_no_table_costs_every_glyph_and_a_long_cell_is_capped() -> None:
    truth = load_truth(truth_json([fee_table()]))
    cell = GlyphCell(doc="x", table=0, cell=5, text="4,715")
    assert cer_counts([cell], {"x": truth}, {"x": []}) == {"x": {"chars": 5, "errors": 5}}
    long = tool_table(2, (0, 0, 300, 80), ["a much longer cell that shares nothing with it"])
    assert cer_counts([cell], {"x": truth}, {"x": [long]}) == {"x": {"chars": 5, "errors": 5}}
    away = tool_table(2, (400, 400, 500, 500), ["4,716"])  # no overlap: the page's tables count
    assert cer_counts([cell], {"x": truth}, {"x": [away]}) == {"x": {"chars": 5, "errors": 1}}
