"""Held-out ground truths for the bench tests: one fee table, and a truth file holding it."""

import json
from typing import Any


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
