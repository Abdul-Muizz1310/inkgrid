"""What the lattice reader hands the core (docs/specs/06-ruled-tables.md section 2).

A ruled grid is only its cell rectangles in unrotated page coordinates, a merged cell as one
rectangle. The core derives bands, indices, and spans in the frame it reads the page in.
"""

from typing import Annotated, Self

from pydantic import Field, PositiveInt, model_validator

from inkgrid.model.base import Frozen
from inkgrid.model.document import Lattice
from inkgrid.model.findings import Finding
from inkgrid.model.geometry import Rect, Rotation


class PageFrame(Frozen):
    """A page's rotation and unrotated CropBox size: the frame Camelot's grids are placed in.

    Camelot reads the lattice copy, whose MediaBox is the CropBox, so no box offsets remain.
    """

    number: PositiveInt
    rotation: Rotation
    width: Annotated[float, Field(gt=0)]
    height: Annotated[float, Field(gt=0)]


class RuledGrid(Frozen):
    """One lattice grid: its cells as rectangles in unrotated page coordinates."""

    page: PositiveInt
    cells: Annotated[tuple[Rect, ...], Field(min_length=1)]
    # A frame's closed core, when the grid is a frame around a table (spec 14 section 4.2).
    core: Rect | None = None

    @model_validator(mode="after")
    def _cells_have_area(self) -> Self:
        for rect in self.cells:
            if rect.x1 <= rect.x0 or rect.y1 <= rect.y0:
                msg = f"a cell of the grid on page {self.page} has no positive size: {rect}"
                raise ValueError(msg)
        if self.core is not None:
            x0, y0 = min(r.x0 for r in self.cells), min(r.y0 for r in self.cells)
            x1, y1 = max(r.x1 for r in self.cells), max(r.y1 for r in self.cells)
            c = self.core
            if c.x0 < x0 or c.y0 < y0 or c.x1 > x1 or c.y1 > y1:
                msg = f"the core {c} of the grid on page {self.page} reaches past the grid"
                raise ValueError(msg)
        return self


class LatticeReading(Frozen):
    """Camelot's grids for the pages it read, and what went wrong on them."""

    engine: Lattice
    camelot: Annotated[str, Field(min_length=1)]
    pages: tuple[PositiveInt, ...]
    grids: tuple[RuledGrid, ...]
    findings: tuple[Finding, ...] = ()

    @model_validator(mode="after")
    def _only_pages_read(self) -> Self:
        read = set(self.pages)
        for grid in self.grids:
            if grid.page not in read:
                msg = f"a grid on page {grid.page}, which the lattice reader did not read"
                raise ValueError(msg)
        for finding in self.findings:
            if finding.page is not None and finding.page not in read:
                msg = f"a finding on page {finding.page}, which the lattice reader did not read"
                raise ValueError(msg)
        return self
