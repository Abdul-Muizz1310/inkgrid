"""The verification report, `inkgrid.verification/1` (docs/specs/10-verify.md section 6).

A report grades a `Document` against its PDF as a second engine (PDFium) reads it. A report that
exists is internally consistent: every page accounts for all of its ink, and every defect sits where
its code allows.
"""

from collections import defaultdict
from enum import StrEnum
from typing import Annotated, Final, Literal, Self

from pydantic import Field, NonNegativeInt, PositiveInt, model_validator

from inkgrid.model.base import Frozen
from inkgrid.model.findings import BLOCK_ID
from inkgrid.model.geometry import Rect
from inkgrid.model.page import Source

VerificationSchema = Literal["inkgrid.verification/1"]
VERIFICATION_SCHEMA: Final[VerificationSchema] = "inkgrid.verification/1"

BlockId = Annotated[str, Field(pattern=BLOCK_ID)]
Anchor = tuple[NonNegativeInt, NonNegativeInt]
NonEmpty = Annotated[str, Field(min_length=1)]
PageStatus = Literal["verified", "declared", "unverified"]


class DefectCode(StrEnum):
    """The closed set of verification codes, in report order. ORDER is the only advisory."""

    LOST = "lost"
    DOUBLED = "doubled"
    INVENTED = "invented"
    VALUE = "value"
    ORPHAN = "orphan"
    DOUBLE = "double"
    TEXT = "text"
    VRULE = "vrule"
    HRULE = "hrule"
    UNVERIFIED = "unverified"
    ORDER = "order"


ADVISORY: Final = frozenset({DefectCode.ORDER})
TABLE_CODES: Final = frozenset(
    {
        DefectCode.ORPHAN,
        DefectCode.DOUBLE,
        DefectCode.TEXT,
        DefectCode.VRULE,
        DefectCode.HRULE,
        DefectCode.ORDER,
    }
)
CELL_CODES: Final = frozenset(
    {DefectCode.TEXT, DefectCode.VRULE, DefectCode.HRULE, DefectCode.ORDER}
)
CHARACTER_CODES: Final = frozenset({DefectCode.LOST, DefectCode.DOUBLED, DefectCode.INVENTED})


class Defect(Frozen):
    """One disagreement between the document and the page, pinned to where it is."""

    code: DefectCode
    page: PositiveInt
    block: BlockId | None = None
    cell: Anchor | None = None
    text: str = ""
    bbox: Rect | None = None
    detail: NonEmpty

    @model_validator(mode="after")
    def _where(self) -> Self:
        if self.code in TABLE_CODES and self.block is None:
            msg = f"a {self.code} defect names its table block"
            raise ValueError(msg)
        if self.code in CELL_CODES and self.cell is None:
            msg = f"a {self.code} defect names its cell"
            raise ValueError(msg)
        if self.code in CHARACTER_CODES and not self.text:
            msg = f"a {self.code} defect holds the characters concerned (text)"
            raise ValueError(msg)
        return self


class PageCheck(Frozen):
    """One page's status and where each of its ink characters went."""

    number: PositiveInt
    status: PageStatus
    ink_chars: NonNegativeInt
    owned_chars: NonNegativeInt = 0
    lost_chars: NonNegativeInt = 0
    outside_chars: NonNegativeInt = 0
    clipped_chars: NonNegativeInt = 0
    soft_hyphens: NonNegativeInt = 0
    unmapped_chars: NonNegativeInt = 0
    declared_chars: NonNegativeInt = 0
    overflow_chars: NonNegativeInt = 0
    rules: NonNegativeInt = 0

    @model_validator(mode="after")
    def _accounted(self) -> Self:
        where = f"page {self.number}"
        parts = (
            self.owned_chars
            + self.lost_chars
            + self.outside_chars
            + self.clipped_chars
            + self.soft_hyphens
        )
        match self.status:
            case "verified":
                if self.declared_chars:
                    msg = f"{where}: a verified page has no declared characters"
                    raise ValueError(msg)
                if self.ink_chars != parts:
                    msg = (
                        f"{where}: {self.ink_chars} ink characters, but owned, lost, outside, "
                        f"clipped and soft hyphens add up to {parts}"
                    )
                    raise ValueError(msg)
            case "declared":
                if parts or self.ink_chars != self.declared_chars:
                    msg = f"{where}: a declared page's ink is all declared, and nothing else"
                    raise ValueError(msg)
            case "unverified":
                counts = (self.ink_chars, parts, self.unmapped_chars, self.declared_chars)
                if any(counts) or self.overflow_chars or self.rules:
                    msg = f"{where}: an unverified page counts nothing"
                    raise ValueError(msg)
        return self


class Verifier(Frozen):
    """The versions that produced a report."""

    inkgrid: str
    pypdfium2: str
    pdfium: str


class VerificationReport(Frozen):
    """A document graded against its PDF: its pages, defects, and advisories."""

    schema_version: VerificationSchema = Field(default=VERIFICATION_SCHEMA, alias="schema")
    source: Source
    verifier: Verifier
    pages: Annotated[tuple[PageCheck, ...], Field(min_length=1)]
    defects: tuple[Defect, ...] = ()
    advisories: tuple[Defect, ...] = ()

    @property
    def ok(self) -> bool:
        """True when the report holds no defect (advisories do not count)."""
        return not self.defects

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        self._check_numbering()
        self._check_roles()
        self._check_pages()
        return self

    def _check_numbering(self) -> None:
        for index, check in enumerate(self.pages, start=1):
            if check.number != index:
                msg = f"page number {check.number} at position {index}"
                raise ValueError(msg)
        for defect in (*self.defects, *self.advisories):
            if defect.page > len(self.pages):
                msg = f"a {defect.code} defect names page {defect.page} of {len(self.pages)}"
                raise ValueError(msg)

    def _check_roles(self) -> None:
        for defect in self.defects:
            if defect.code in ADVISORY:
                msg = f"{defect.code} is an advisory, never a defect"
                raise ValueError(msg)
        for advisory in self.advisories:
            if advisory.code not in ADVISORY:
                msg = f"{advisory.code} is a defect, never an advisory"
                raise ValueError(msg)

    def _check_pages(self) -> None:
        lost: defaultdict[int, int] = defaultdict(int)
        for defect in self.defects:
            if defect.code is DefectCode.LOST:
                lost[defect.page] += len(defect.text)
        unverified = {d.page for d in self.defects if d.code is DefectCode.UNVERIFIED}
        for check in self.pages:
            if lost[check.number] != check.lost_chars:
                msg = (
                    f"page {check.number}: lost_chars is {check.lost_chars}, but its lost defects "
                    f"hold {lost[check.number]}"
                )
                raise ValueError(msg)
            if (check.status == "unverified") != (check.number in unverified):
                msg = f"page {check.number}: unverified defects go on unverified pages, one each"
                raise ValueError(msg)
