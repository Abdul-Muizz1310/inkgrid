"""The ICDAR-2013 structure ground truth read as if it were a tool: a check on the pipeline.

Scored like a tool, the ground truth must come out at or near 1.0 on its own metrics; anything less
is the renderers, the scorers, or the metric itself (binding's ceiling). Each region becomes a
table, its rows and columns counted from the region's first; a region whose cells do not tile a
grid is left out, and said so on stderr.
"""

import sys
from pathlib import Path

from inkgrid_bench import icdar_gt, pages
from inkgrid_bench.adapters._cli import main
from inkgrid_bench.tables import NCell, NTable


def read(pdf: Path) -> list[NTable]:
    """Every region of the PDF's `-str.xml` ground truth as a table."""
    xml = pdf.with_name(pdf.stem + "-str.xml").read_text(encoding="utf-8")
    frames = pages.frames(pdf)
    out = []
    for n, regions in enumerate(icdar_gt.parse(xml), start=1):
        for region in regions:
            box = region.bbox(frames[region.page - 1])
            if box is None or not region.cells:
                continue
            row0 = min(c.row for c in region.cells)
            col0 = min(c.col for c in region.cells)
            cells = [
                NCell(
                    c.row - row0,
                    c.col - col0,
                    rows=c.end_row - c.row + 1,
                    cols=c.end_col - c.col + 1,
                    text=c.text,
                )
                for c in region.cells
            ]
            try:
                out.append(NTable.filled(page=region.page, bbox=box, cells=cells))
            except ValueError as exc:
                sys.stderr.write(f"{pdf.name}: table {n}, page {region.page}: {exc}\n")
    return out


if __name__ == "__main__":
    raise SystemExit(main(read))
