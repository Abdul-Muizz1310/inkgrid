"""Binding on the ICDAR-2013 practice set: are values filed under their labels (spec 12 4.4)?

The practice set's `-fnc.csv` lists access paths: a value and its labels along each of the table's
dimensions. A path is scored on the tool's table matched to its ground-truth table, needing no
header flag from the tool: a label binds when its cell lies above the value cell in a column it
covers or left of it in a row it covers, and each higher label binds to the leaf's cell or to a
cell already bound for a later label of the same dimension.
"""

import csv
import io
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass

from inkgrid_bench.tables import Box, NCell, NPage, NTable

KEYS = ("paths", "value", "leaf", "bound")


def norm(text: str) -> str:
    """Text as compared: NFKC, casefolded, all whitespace removed."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text).casefold())


@dataclass(frozen=True, slots=True)
class AccessPath:
    """A value and, per dimension, its labels from the outermost to the leaf."""

    value: str
    dimensions: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class Binding:
    """Whether a path's value was found, every dimension's leaf bound, and every label bound."""

    value: bool
    leaf: bool
    strict: bool


@dataclass(frozen=True, slots=True)
class GtTable:
    """A ground-truth table: its regions (page, box in the top-left frame) and its cells' texts."""

    regions: tuple[tuple[int, Box], ...]
    texts: frozenset[str]


def parse_fnc(text: str) -> list[list[AccessPath]]:
    """The access paths of each table, in order; a lone number starts the next table."""
    tables: list[list[AccessPath]] = []
    for record in csv.reader(io.StringIO(text)):
        fields = [f.strip() for f in record]
        while fields and not fields[-1]:
            fields.pop()
        if not fields:
            continue
        if len(fields) == 1 and fields[0].isdigit():
            tables.append([])
            continue
        if not tables:
            tables.append([])
        *labels, value = fields
        dims: list[tuple[str, ...]] = []
        run: list[str] = []
        for label in labels:
            if label:
                run.append(label)
            elif run:
                dims.append(tuple(run))
                run = []
        if run:
            dims.append(tuple(run))
        tables[-1].append(AccessPath(value=value, dimensions=tuple(dims)))
    return tables


def gt_tables(xml: str, pages: Sequence[NPage]) -> list[GtTable]:
    """The structure ground truth's tables; each region's box is the union of its cells' boxes."""
    root = ET.fromstring(xml.encode("utf-8"))  # noqa: S314 - pinned ground truth, hash-verified
    out = []
    for table in root.findall("table"):
        regions: list[tuple[int, Box]] = []
        texts: set[str] = set()
        for region in table.findall("region"):
            number = int(region.get("page", "0"))
            boxes = []
            for cell in region.findall("cell"):
                texts.add(norm(cell.findtext("content") or ""))
                bb = cell.find("bounding-box")
                if bb is not None:
                    boxes.append([float(bb.get(k, "nan")) for k in ("x1", "x2", "y1", "y2")])
            if not boxes:
                continue
            x0, _, _, top = pages[number - 1].box
            ux1, ux2 = min(b[0] for b in boxes), max(b[1] for b in boxes)
            uy1, uy2 = min(b[2] for b in boxes), max(b[3] for b in boxes)
            regions.append((number, (ux1 - x0, top - uy2, ux2 - x0, top - uy1)))
        out.append(GtTable(regions=tuple(regions), texts=frozenset(texts)))
    return out


def _overlap(a: Box, b: Box) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def match(tables: Sequence[NTable], page: int, region: Box) -> NTable | None:
    """The tool's table on `page` with the largest intersection with `region`, if any intersects."""
    best, best_area = None, 0.0
    for table in tables:
        area = _overlap(table.bbox, region) if table.page == page else 0.0
        if area > best_area:
            best, best_area = table, area
    return best


def _aligned(cell: NCell, anchor: NCell) -> bool:
    """`cell` lies above `anchor` in a column it covers, or left of it in a row it covers."""
    cols = cell.col < anchor.col + anchor.cols and anchor.col < cell.col + cell.cols
    rows = cell.row < anchor.row + anchor.rows and anchor.row < cell.row + cell.rows
    above = cell.row + cell.rows <= anchor.row and cols
    left = cell.col + cell.cols <= anchor.col and rows
    return above or left


def _dimension(table: NTable, value: NCell, labels: Sequence[str]) -> tuple[bool, bool]:
    """Whether a dimension is leaf-bound, and bound, at a value cell."""
    anchors = [c for c in table.cells if norm(c.text) == labels[-1] and _aligned(c, value)]
    if not anchors:
        return False, False
    for label in reversed(labels[:-1]):
        found = [
            c for c in table.cells if norm(c.text) == label and any(_aligned(c, a) for a in anchors)
        ]
        if not found:
            return True, False
        anchors += found
    return True, True


def binds(table: NTable, path: AccessPath) -> Binding:
    """How far a path binds in a table, at the best of its value cells."""
    wanted = norm(path.value)
    values = [c for c in table.cells if wanted and norm(c.text) == wanted]
    dims = [[norm(label) for label in dim] for dim in path.dimensions]
    leaf = strict = False
    for value in values:
        results = [_dimension(table, value, labels) for labels in dims]
        leaf = leaf or all(r[0] for r in results)
        strict = strict or all(r[1] for r in results)
    return Binding(value=bool(values), leaf=leaf, strict=strict)


def binding_counts(
    gt: Sequence[GtTable], paths: Sequence[Sequence[AccessPath]], tables: Sequence[NTable]
) -> dict[str, int]:
    """A document's evaluable paths and how many are found, leaf-bound, and bound.

    Paths map to ground-truth tables by order; a path is evaluable when its value is one of its
    table's cells. A table spanning pages is matched per region, and a path counts as bound when it
    binds in any of the matched tables.
    """
    counts = dict.fromkeys(KEYS, 0)
    for k, table_paths in enumerate(paths):
        if k >= len(gt):
            continue
        matched: list[NTable] = []
        for page, region in gt[k].regions:
            found = match(tables, page, region)
            if found is not None and all(found is not m for m in matched):
                matched.append(found)
        for path in table_paths:
            if norm(path.value) not in gt[k].texts:
                continue
            results = [binds(t, path) for t in matched]
            counts["paths"] += 1
            counts["value"] += any(r.value for r in results)
            counts["leaf"] += any(r.leaf for r in results)
            counts["bound"] += any(r.strict for r in results)
    return counts
