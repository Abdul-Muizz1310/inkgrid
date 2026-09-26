"""Local type stub: only the parts of Camelot 2.0 that `inkgrid.read.camelot_reader` calls.

Camelot ships no type hints. The shapes below were measured on Camelot 2.0.0
(docs/specs/06-ruled-tables.md section 0 and knowledge RR-0015).
"""

from collections.abc import Iterator

__version__: str

class Cell:
    # (x1, y1) is the bottom-left corner and (x2, y2) the top-right, PDF y-up.
    x1: float
    y1: float
    x2: float
    y2: float
    left: bool
    right: bool
    top: bool
    bottom: bool

class Table:
    cells: list[list[Cell]]
    pdf_size: tuple[float, float]
    shape: tuple[int, int]

class TableList:
    n: int
    def __iter__(self) -> Iterator[Table]: ...
    def __len__(self) -> int: ...

def read_pdf(
    filepath: bytes,
    pages: str = ...,
    password: str | None = ...,
    flavor: str = ...,
    suppress_stdout: bool = ...,
    *,
    engine: str = ...,
) -> TableList: ...
