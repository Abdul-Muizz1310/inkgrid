"""The ICDAR-2013 structure ground truth (`-str.xml`): tables, their regions, and their cells.

A region is a table's part on one page. A cell names its first row and column and, when it spans,
its last; its bounding box is in PDF user space (origin at the bottom left), `x1 x2 y1 y2`.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass

from inkgrid_bench.tables import Box, NPage


@dataclass(frozen=True, slots=True)
class GtCell:
    """A ground-truth cell: its first and last row and column, its text, its box in user space."""

    row: int
    col: int
    end_row: int
    end_col: int
    text: str
    box: Box | None


@dataclass(frozen=True, slots=True)
class GtRegion:
    """A table's cells on one page."""

    page: int
    cells: tuple[GtCell, ...]

    def bbox(self, page: NPage) -> Box | None:
        """The union of the cells' boxes, in the page's top-left frame."""
        boxes = [c.box for c in self.cells if c.box is not None]
        if not boxes:
            return None
        x0, _, _, top = page.box
        ux0, uy0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
        ux1, uy1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
        return (ux0 - x0, top - uy1, ux1 - x0, top - uy0)


def _int(element: ET.Element, name: str, default: int | None = None) -> int:
    value = element.get(name)
    if value is None:
        if default is None:
            msg = f"a <{element.tag}> without {name}"
            raise ValueError(msg)
        return default
    return int(value)


def parse(xml: str) -> list[list[GtRegion]]:
    """Every table's regions, in the file's order."""
    root = ET.fromstring(xml.encode("utf-8"))  # noqa: S314 - pinned ground truth, hash-verified
    tables = []
    for table in root.findall("table"):
        regions = []
        for region in table.findall("region"):
            cells = []
            for cell in region.findall("cell"):
                row, col = _int(cell, "start-row"), _int(cell, "start-col")
                bb = cell.find("bounding-box")
                box = None
                if bb is not None:
                    x1, x2, y1, y2 = (float(bb.get(k, "nan")) for k in ("x1", "x2", "y1", "y2"))
                    box = (x1, y1, x2, y2)
                cells.append(
                    GtCell(
                        row=row,
                        col=col,
                        end_row=_int(cell, "end-row", row),
                        end_col=_int(cell, "end-col", col),
                        text=cell.findtext("content") or "",
                        box=box,
                    )
                )
            regions.append(GtRegion(page=_int(region, "page"), cells=tuple(cells)))
        tables.append(regions)
    return tables
