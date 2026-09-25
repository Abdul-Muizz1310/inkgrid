"""inkgrid: exact tables and text from born-digital PDFs.

M0 exposes the raw page model through `read_pages`; the full `Document` contract is defined and
validated here and is produced by `read()` from milestone M1 on.
"""

import importlib.metadata

from inkgrid.api import read_pages
from inkgrid.errors import (
    InkgridError,
    InvariantError,
    PasswordRequired,
    PdfOpenError,
    StrictModeError,
    WrongPassword,
)
from inkgrid.model import (
    Block,
    Cell,
    Definition,
    Document,
    Finding,
    FindingCode,
    Footnote,
    Furniture,
    Grid,
    Heading,
    Interval,
    Ledger,
    Link,
    LinkEnd,
    ListItem,
    PageInfo,
    PageModel,
    Paragraph,
    Producer,
    Reading,
    Rect,
    Region,
    Rule,
    Severity,
    Table,
    Word,
)

__version__ = importlib.metadata.version("inkgrid")

__all__ = [
    "Block",
    "Cell",
    "Definition",
    "Document",
    "Finding",
    "FindingCode",
    "Footnote",
    "Furniture",
    "Grid",
    "Heading",
    "InkgridError",
    "Interval",
    "InvariantError",
    "Ledger",
    "Link",
    "LinkEnd",
    "ListItem",
    "PageInfo",
    "PageModel",
    "Paragraph",
    "PasswordRequired",
    "PdfOpenError",
    "Producer",
    "Reading",
    "Rect",
    "Region",
    "Rule",
    "Severity",
    "StrictModeError",
    "Table",
    "Word",
    "WrongPassword",
    "__version__",
    "read_pages",
]
