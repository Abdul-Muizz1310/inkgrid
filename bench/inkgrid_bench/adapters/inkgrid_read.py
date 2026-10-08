"""inkgrid's tables (spec 12 section 2) and its page Markdown (spec 18 section 3)."""

from pathlib import Path

import inkgrid
from inkgrid.model.document import Document
from inkgrid_bench.adapters._cli import main
from inkgrid_bench.page_markdown import inkgrid_markdown
from inkgrid_bench.tables import NCell, NTable, Output


def read(pdf: Path) -> Output:
    """The document's tables, header rows marked, and its Markdown with each table as HTML.

    A carried header cell is empty on its page.
    """
    doc = inkgrid.read(pdf)
    return Output(tuple(tables_of(doc)), inkgrid_markdown(doc))


def tables_of(doc: Document) -> list[NTable]:
    """A document's tables, normalized: the ablation's are normalized exactly as inkgrid's."""
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
