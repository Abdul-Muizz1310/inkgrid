"""The held-out fee set: selection, ground truth, access paths, the glyph sample (spec 16).

Pure: nothing here reads a PDF. The ground truth is parsed field by field and validated, so a
malformed file is refused with its reason, and no number is computed from an unverified one.
"""

import json
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from inkgrid_bench.scores.binding import AccessPath
from inkgrid_bench.tables import Box, NCell, NTable

BOX_TOL = 1.0  # pt a cell's box may reach past its table's
SCORED = 3  # pages scored per document (spec 16 section 1)


@dataclass(frozen=True, slots=True)
class Candidate:
    """A candidate fee schedule: its id, its exchange group, where it is, and its SHA-256."""

    id: str
    group: str
    url: str
    sha256: str


def select(
    candidates: Sequence[Candidate],
    numeric: Mapping[str, Sequence[int]],
    pages: Mapping[str, int],
) -> list[Candidate]:
    """One candidate per group: the most numeric pages, then the most pages, then the first id."""
    out = []
    for group in sorted({c.group for c in candidates}):
        mine = [c for c in candidates if c.group == group]
        out.append(min(mine, key=lambda c: (-len(numeric[c.id]), -pages[c.id], c.id)))
    return out


def scored_pages(doc_id: str, numeric: Sequence[int], *, seed: str, k: int = SCORED) -> list[int]:
    """The document's scored pages: a seeded sample of its numeric pages, sorted."""
    pool = sorted(numeric)
    rng = random.Random(f"{seed}:{doc_id}")  # noqa: S311 - a seeded sample, not a secret
    return sorted(rng.sample(pool, k=min(k, len(pool))))


@dataclass(frozen=True, slots=True)
class TruthCell:
    """A ground-truth cell: its anchor, span, text, and box (points, the page's top-left frame)."""

    row: int
    col: int
    rows: int
    cols: int
    text: str
    box: Box


@dataclass(frozen=True, slots=True)
class TruthTable:
    """A ground-truth table on a scored page, with its header rows and stub columns."""

    page: int
    bbox: Box
    header_rows: int
    stub_cols: int
    cells: tuple[TruthCell, ...]

    def table(self) -> NTable:
        """The table as spec 12 normalizes it: a cell in the header rows is a header cell."""
        cells = tuple(
            NCell(c.row, c.col, c.rows, c.cols, c.text, header=c.row < self.header_rows)
            for c in self.cells
        )
        return NTable(page=self.page, bbox=self.bbox, cells=cells)


@dataclass(frozen=True, slots=True)
class Verified:
    """Who verified the document's ground truth, when, and how many tables they corrected."""

    by: str
    date: str
    corrected: int


@dataclass(frozen=True, slots=True)
class Truth:
    """One held-out document's ground truth."""

    id: str
    pages: tuple[int, ...]
    tables: tuple[TruthTable, ...]
    verified: Verified | None


def _int(data: Mapping[str, Any], key: str) -> int:
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key!r} is not an integer: {value!r}"
        raise TypeError(msg)
    return value


def _box(value: object, what: str) -> Box:
    if not isinstance(value, list) or len(value) != 4:  # noqa: PLR2004 - a box is four numbers
        msg = f"{what} is not a box of four numbers: {value!r}"
        raise TypeError(msg)
    x0, y0, x1, y1 = (float(v) for v in value)
    if not (x0 < x1 and y0 < y1):
        msg = f"{what} is empty or inverted: {value!r}"
        raise ValueError(msg)
    return (x0, y0, x1, y1)


def _inside(inner: Box, outer: Box) -> bool:
    return (
        inner[0] >= outer[0] - BOX_TOL
        and inner[1] >= outer[1] - BOX_TOL
        and inner[2] <= outer[2] + BOX_TOL
        and inner[3] <= outer[3] + BOX_TOL
    )


def _table(data: Mapping[str, Any], pages: Sequence[int]) -> TruthTable:
    page = _int(data, "page")
    if page not in pages:
        msg = f"a table on unscored page {page}"
        raise ValueError(msg)
    bbox = _box(data["bbox"], "a table's bbox")
    header_rows, stub_cols = _int(data, "header_rows"), _int(data, "stub_cols")
    cells = []
    for raw in data["cells"]:
        text = raw["text"]
        if not isinstance(text, str):
            msg = f"a cell's text is not text: {text!r}"
            raise TypeError(msg)
        c = TruthCell(
            _int(raw, "row"),
            _int(raw, "col"),
            _int(raw, "rows"),
            _int(raw, "cols"),
            text,
            _box(raw["box"], f"cell ({raw['row']}, {raw['col']})'s box"),
        )
        if c.row < header_rows < c.row + c.rows:
            msg = f"cell ({c.row}, {c.col}) runs from the header rows into the body"
            raise ValueError(msg)
        if not _inside(c.box, bbox):
            msg = f"cell ({c.row}, {c.col})'s box lies outside its table"
            raise ValueError(msg)
        cells.append(c)
    table = TruthTable(page, bbox, header_rows, stub_cols, tuple(cells))
    table.table()  # the cells tile the table, or this raises
    return table


def load_truth(text: str) -> Truth:
    """A ground-truth file, validated (spec 16 section 2)."""
    data = json.loads(text)
    pages = tuple(int(p) for p in data["pages"])
    tables = tuple(_table(t, pages) for t in data["tables"])
    v = data["verified"]
    verified = None if v is None else Verified(str(v["by"]), str(v["date"]), _int(v, "corrected"))
    return Truth(str(data["id"]), pages, tables, verified)


def require_verified(truth: Truth) -> Truth:
    """The truth, if the user has verified it; no held-out number comes from one they have not."""
    if truth.verified is None:
        msg = f"the ground truth of {truth.id} is not verified"
        raise ValueError(msg)
    return truth


def access_paths(table: TruthTable) -> list[AccessPath]:
    """Each value's labels, outer to leaf: stub cells along its row, header cells up its column."""
    out = []
    for value in table.cells:
        if value.row < table.header_rows or value.col < table.stub_cols or not value.text:
            continue
        rows = tuple(
            c.text
            for c in sorted(table.cells, key=lambda c: c.col)
            if c.col < table.stub_cols
            and c.row >= table.header_rows
            and c.row <= value.row < c.row + c.rows
            and c.text
        )
        cols = tuple(
            c.text
            for c in sorted(table.cells, key=lambda c: c.row)
            if c.row < table.header_rows and c.col <= value.col < c.col + c.cols and c.text
        )
        dimensions = tuple(d for d in (rows, cols) if d)
        if dimensions:
            out.append(AccessPath(value.text, dimensions))
    return out


def glyph_sample(truths: Sequence[Truth], *, k: int, seed: str) -> list[tuple[str, int, int]]:
    """The glyph-verified sample: (document, table, cell) of `k` non-empty cells, seeded."""
    pool = [
        (truth.id, t, c)
        for truth in sorted(truths, key=lambda truth: truth.id)
        for t, table in enumerate(truth.tables)
        for c, cell in enumerate(table.cells)
        if cell.text
    ]
    rng = random.Random(f"{seed}:cer")  # noqa: S311 - a seeded sample, not a secret
    return rng.sample(pool, k=min(k, len(pool)))
