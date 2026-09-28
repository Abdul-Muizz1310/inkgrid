"""Typed, frozen values shared by every inkgrid package. Imports only stdlib and pydantic."""

from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.document import (
    Block,
    Cell,
    Definition,
    Document,
    Footnote,
    Furniture,
    Grid,
    Heading,
    Ledger,
    Link,
    LinkEnd,
    ListItem,
    Paragraph,
    Producer,
    Region,
    Table,
)
from inkgrid.model.findings import SEVERITY, Finding, FindingCode, Severity
from inkgrid.model.geometry import Interval, Rect
from inkgrid.model.page import PageInfo, PageModel, ReaderInfo, Reading, Rule, Source, Word
from inkgrid.model.verification import Defect, DefectCode, PageCheck, VerificationReport, Verifier

__all__ = [
    "SEVERITY",
    "Block",
    "Cell",
    "Defect",
    "DefectCode",
    "Definition",
    "Document",
    "Finding",
    "FindingCode",
    "Footnote",
    "Furniture",
    "Grid",
    "Heading",
    "Interval",
    "Ledger",
    "Lexicon",
    "Link",
    "LinkEnd",
    "ListItem",
    "PageCheck",
    "PageInfo",
    "PageModel",
    "Paragraph",
    "Producer",
    "Profile",
    "ReaderInfo",
    "Reading",
    "Rect",
    "Region",
    "Rule",
    "Severity",
    "Source",
    "Table",
    "VerificationReport",
    "Verifier",
    "Word",
]
