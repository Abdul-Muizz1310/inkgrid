"""inkgrid's tables: every `Table` block of `inkgrid.read` (spec 12 section 2)."""

from pathlib import Path

import inkgrid
from inkgrid_bench.adapters._cli import main
from inkgrid_bench.tables import NCell, NTable


def read(pdf: Path) -> list[NTable]:
    """The document's tables, header rows marked; a carried header cell is empty on its page."""
    doc = inkgrid.read(pdf)
    out = []
    for table in doc.tables():
        grid = table.grid
        cells = tuple(
            NCell(
                c.row,
                c.col,
                rows=c.row_span,
                cols=c.col_span,
                text="" if c.carried else c.text,
                header=c.row < grid.header_rows,
            )
            for c in grid.cells
        )
        (region,) = table.regions
        box = region.bbox
        out.append(NTable(page=region.page, bbox=(box.x0, box.y0, box.x1, box.y1), cells=cells))
    return out


if __name__ == "__main__":
    raise SystemExit(main(read))
