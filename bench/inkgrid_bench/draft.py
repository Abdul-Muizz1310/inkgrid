"""Drafting the held-out ground truth from a stated grid, and the images it is checked on.

Spec 16 section 3: Claude states each table's grid (row and column boundaries in points, merges,
header rows, stub columns) from a rendering with a ruler; a cell's text is the PDF's words whose
centres lie in its box. inkgrid's reading is never consulted. The renderings are the drafter's
ruler, the reviewer's overlay, and the glyph sample's crops.
"""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium
from PIL import Image, ImageDraw

from inkgrid_bench.heldout import TruthCell, TruthTable
from inkgrid_bench.tables import Box

type PageWord = tuple[float, float, float, float, str, int, int, int]
"""A PyMuPDF word: its box, its text, and its block, line, and word numbers (reading order)."""
type Merge = tuple[int, int, int, int]
"""A merged cell: its anchor (row, col) and its span (rows, cols) on the stated grid."""


def cell_text(words: Sequence[PageWord], box: Box) -> str:
    """The words whose centres lie in the box (half-open), in reading order, one space apart."""
    x0, y0, x1, y1 = box
    inside = [w for w in words if x0 <= (w[0] + w[2]) / 2 < x1 and y0 <= (w[1] + w[3]) / 2 < y1]
    return " ".join(w[4] for w in sorted(inside, key=lambda w: (w[5], w[6], w[7])))


def draft_table(
    words: Sequence[PageWord],
    *,
    page: int,
    rows: Sequence[float],
    cols: Sequence[float],
    merges: Sequence[Merge],
    header_rows: int,
    stub_cols: int,
) -> TruthTable:
    """The table on the stated grid: each merge one cell, every other position its own cell."""
    n_rows, n_cols = len(rows) - 1, len(cols) - 1
    taken: dict[tuple[int, int], Merge] = {}
    for merge in merges:
        r, c, rs, cs = merge
        if r < 0 or c < 0 or rs < 1 or cs < 1 or r + rs > n_rows or c + cs > n_cols:
            msg = f"the merge {merge} runs past the grid of {n_rows} x {n_cols}"
            raise ValueError(msg)
        for pos in ((i, j) for i in range(r, r + rs) for j in range(c, c + cs)):
            if pos in taken:
                msg = f"position {pos} is covered twice, by {taken[pos]} and {merge}"
                raise ValueError(msg)
            taken[pos] = merge
    anchors = list(merges) + [
        (i, j, 1, 1) for i in range(n_rows) for j in range(n_cols) if (i, j) not in taken
    ]
    cells = []
    for r, c, rs, cs in sorted(anchors):
        box = (float(cols[c]), float(rows[r]), float(cols[c + cs]), float(rows[r + rs]))
        cells.append(TruthCell(r, c, rs, cs, cell_text(words, box), box))
    bbox = (float(cols[0]), float(rows[0]), float(cols[-1]), float(rows[-1]))
    table = TruthTable(page, bbox, header_rows, stub_cols, tuple(cells))
    table.table()  # the cells tile the grid, or this raises
    return table


def build_truth(
    grids: Mapping[str, Any], words: Mapping[int, Sequence[PageWord]], *, drafted: str
) -> str:
    """A document's ground truth as JSON, drafted from its stated grids and its pages' words.

    A grid's `text` maps `"row,col"` to a correction of that cell's drafted text (spec 16 section
    4). The result is unverified: the user's review sets `verified`.
    """
    tables = []
    for g in grids["tables"]:
        t = draft_table(
            words[g["page"]],
            page=g["page"],
            rows=g["rows"],
            cols=g["cols"],
            merges=[(m[0], m[1], m[2], m[3]) for m in g["merges"]],
            header_rows=g["header_rows"],
            stub_cols=g["stub_cols"],
        )
        fixes: Mapping[str, str] = g.get("text", {})
        cells = [
            {
                "row": c.row,
                "col": c.col,
                "rows": c.rows,
                "cols": c.cols,
                "text": fixes.get(f"{c.row},{c.col}", c.text),
                "box": [round(v, 2) for v in c.box],
            }
            for c in t.cells
        ]
        tables.append({
            "page": t.page,
            "bbox": [round(v, 2) for v in t.bbox],
            "header_rows": t.header_rows,
            "stub_cols": t.stub_cols,
            "cells": cells,
        })  # fmt: skip
    data = {
        "id": grids["id"],
        "pages": list(grids["pages"]),
        "tables": tables,
        "drafted": {"by": "claude", "date": drafted, "grids": f"grids/{grids['id']}.json"},
        "verified": None,
    }
    return json.dumps(data, ensure_ascii=True, indent=1) + "\n"


def _render(pdf: Path, page: int, dpi: int) -> Image.Image:
    doc = pdfium.PdfDocument(pdf.read_bytes())
    try:
        return doc[page - 1].render(scale=dpi / 72).to_pil().convert("RGB")
    finally:
        doc.close()


def ruler(pdf: Path, page: int, out: Path, *, dpi: int = 150) -> Path:
    """The page with a ruler in points: a faint line every 10 pt, a labelled one every 50 pt."""
    image = _render(pdf, page, dpi)
    draw = ImageDraw.Draw(image)
    scale = dpi / 72
    width, height = image.size
    for pt in range(0, int(max(width, height) / scale) + 1, 10):
        strong = pt % 50 == 0
        colour = (230, 80, 80) if strong else (250, 200, 200)
        x = y = round(pt * scale)
        if x < width:
            draw.line([(x, 0), (x, height)], fill=colour, width=1)
            if strong:
                draw.text((x + 2, 2), str(pt), fill=(200, 0, 0))
        if y < height:
            draw.line([(0, y), (width, y)], fill=colour, width=1)
            if strong:
                draw.text((2, y + 2), str(pt), fill=(200, 0, 0))
    image.save(out)
    return out


def overlay(
    pdf: Path, page: int, tables: Sequence[TruthTable], out: Path, *, dpi: int = 150
) -> Path:
    """The page with each drafted cell's box drawn over it, header and stub cells tinted."""
    image = _render(pdf, page, dpi).convert("RGBA")
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    scale = dpi / 72
    for table in tables:
        for c in table.cells:
            box = tuple(round(v * scale) for v in c.box)
            if c.row < table.header_rows:
                tint = (40, 120, 255, 45)
            elif c.col < table.stub_cols:
                tint = (40, 200, 90, 45)
            else:
                tint = (0, 0, 0, 0)
            draw.rectangle(box, fill=tint, outline=(230, 40, 40, 255), width=2)
        x0, y0, x1, y1 = (round(v * scale) for v in table.bbox)
        draw.rectangle((x0 - 3, y0 - 3, x1 + 3, y1 + 3), outline=(255, 140, 0, 255), width=3)
    Image.alpha_composite(image, layer).convert("RGB").save(out)
    return out


def crop(pdf: Path, page: int, box: Box, out: Path, *, dpi: int = 400, pad: float = 3.0) -> Path:
    """The box's part of the page at `dpi`, padded by `pad` points on every side."""
    image = _render(pdf, page, dpi)
    scale = dpi / 72
    x0, y0, x1, y1 = box
    area = (
        max(0, round((x0 - pad) * scale)),
        max(0, round((y0 - pad) * scale)),
        min(image.width, round((x1 + pad) * scale)),
        min(image.height, round((y1 + pad) * scale)),
    )
    image.crop(area).save(out)
    return out
