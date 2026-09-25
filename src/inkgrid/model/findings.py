"""Findings: typed notices that something was degraded, missing, or suspicious (guarantee G4).

Every code's severity is fixed in one total mapping, so no producer can mislabel one.
"""

from collections.abc import Iterable
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Self

from pydantic import Field, model_validator

from inkgrid.model.base import Frozen

BLOCK_ID = r"^b[1-9][0-9]*$"


class Severity(StrEnum):
    """How much a finding matters to a consumer."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class FindingCode(StrEnum):
    """The closed set of finding codes. It grows only in a versioned, documented way."""

    NO_TEXT_LAYER = "no_text_layer"
    BLANK_PAGE = "blank_page"
    PARTIAL_TEXT_LAYER = "partial_text_layer"
    OCR_TEXT_LAYER = "ocr_text_layer"
    HIDDEN_TEXT = "hidden_text"
    TYPE3_FONT = "type3_font"
    CLIPPED_TEXT = "clipped_text"
    PDF_ENGINE_WARNING = "pdf_engine_warning"
    UNREADABLE_PAGE = "unreadable_page"
    LATTICE_FAILED = "lattice_failed"
    LATTICE_DISAGREES = "lattice_disagrees"
    WORD_CROSSES_RULE = "word_crosses_rule"
    HEADER_NOT_FOUND = "header_not_found"
    CALL_UNRESOLVED = "call_unresolved"
    NO_FURNITURE_LONG_DOCUMENT = "no_furniture_long_document"


SEVERITY: Final = MappingProxyType(
    {
        FindingCode.NO_TEXT_LAYER: Severity.ERROR,
        FindingCode.BLANK_PAGE: Severity.INFO,
        FindingCode.PARTIAL_TEXT_LAYER: Severity.WARNING,
        FindingCode.OCR_TEXT_LAYER: Severity.WARNING,
        FindingCode.HIDDEN_TEXT: Severity.WARNING,
        FindingCode.TYPE3_FONT: Severity.WARNING,
        FindingCode.CLIPPED_TEXT: Severity.INFO,
        FindingCode.PDF_ENGINE_WARNING: Severity.INFO,
        FindingCode.UNREADABLE_PAGE: Severity.ERROR,
        FindingCode.LATTICE_FAILED: Severity.WARNING,
        FindingCode.LATTICE_DISAGREES: Severity.WARNING,
        FindingCode.WORD_CROSSES_RULE: Severity.WARNING,
        FindingCode.HEADER_NOT_FOUND: Severity.INFO,
        FindingCode.CALL_UNRESOLVED: Severity.WARNING,
        FindingCode.NO_FURNITURE_LONG_DOCUMENT: Severity.INFO,
    }
)


class Finding(Frozen):
    """One notice, optionally pinned to a page (1-based) and a block id."""

    code: FindingCode
    severity: Severity
    page: int | None = Field(default=None, ge=1)
    block: str | None = Field(default=None, pattern=BLOCK_ID)
    detail: str

    @model_validator(mode="after")
    def _severity_matches_code(self) -> Self:
        if self.severity is not SEVERITY[self.code]:
            msg = f"severity of {self.code} is {SEVERITY[self.code]}, not {self.severity}"
            raise ValueError(msg)
        return self

    @classmethod
    def of(
        cls,
        code: FindingCode,
        detail: str,
        *,
        page: int | None = None,
        block: str | None = None,
    ) -> Self:
        """Build a finding with the severity its code fixes."""
        return cls(code=code, severity=SEVERITY[code], page=page, block=block, detail=detail)


def summarize(findings: Iterable[Finding]) -> str:
    """The findings as `code on page N`, comma-separated, for one-line messages."""
    return ", ".join(
        f"{f.code.value} on page {f.page}" if f.page is not None else f.code.value for f in findings
    )
