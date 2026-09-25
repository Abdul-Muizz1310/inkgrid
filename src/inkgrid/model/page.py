"""The page model: what the reader extracts from a PDF, before any layout decision.

`Reading` is the whole-document container `inkgrid words` prints. Word ids run densely from 0 across
pages in reading-agnostic content order; later stages refer to words only by id.
"""

import unicodedata
from collections.abc import Iterator
from typing import Annotated, Final, Literal, Self

from pydantic import Field, NonNegativeInt, PositiveInt, field_validator, model_validator

from inkgrid.model.base import Coord, Frozen
from inkgrid.model.findings import Finding
from inkgrid.model.geometry import Rect

ReadingSchema = Literal["inkgrid.reading/1"]
READING_SCHEMA: Final[ReadingSchema] = "inkgrid.reading/1"
INVISIBLE_CATEGORIES = frozenset({"Cc", "Cf", "Co", "Cn"})

PositiveCoord = Annotated[Coord, Field(gt=0)]
NonNegativeCoord = Annotated[Coord, Field(ge=0)]
TextLayer = Literal["full", "partial", "none"]


class Word(Frozen):
    """One word of the text layer: a run of characters with no whitespace inside."""

    id: NonNegativeInt
    page: PositiveInt
    bbox: Rect
    text: str
    size: NonNegativeCoord
    font: str
    bold: bool
    italic: bool
    superscript: bool
    hidden: bool
    horizontal: bool

    @field_validator("text")
    @classmethod
    def _text_is_a_word(cls, text: str) -> str:
        if not text:
            msg = "word text is empty"
            raise ValueError(msg)
        for ch in text:
            if ch.isspace() or unicodedata.category(ch) in INVISIBLE_CATEGORIES:
                msg = f"word text contains U+{ord(ch):04X}, which a word may not hold"
                raise ValueError(msg)
        return text


class Rule(Frozen):
    """A drawn horizontal (`h`) or vertical (`v`) rule on one page."""

    page: PositiveInt
    axis: Literal["h", "v"]
    at: Coord
    start: Coord
    end: Coord
    thickness: NonNegativeCoord

    @model_validator(mode="after")
    def _has_length(self) -> Self:
        if self.start >= self.end:
            msg = f"rule must run forward: start {self.start} >= end {self.end}"
            raise ValueError(msg)
        return self

    @property
    def length(self) -> float:
        """Extent along the rule's own direction."""
        return self.end - self.start

    @property
    def rect(self) -> Rect:
        """The rule's box, thickened to `thickness` around `at`."""
        half = self.thickness / 2
        if self.axis == "h":
            return Rect(self.start, self.at - half, self.end, self.at + half)
        return Rect(self.at - half, self.start, self.at + half, self.end)


class PageInfo(Frozen):
    """One page's geometry and text-layer measurements (1-based `number`, unrotated CropBox)."""

    number: PositiveInt
    width: PositiveCoord
    height: PositiveCoord
    rotation: Literal[0, 90, 180, 270]
    text_layer: TextLayer
    invisible_chars: NonNegativeInt
    clipped_chars: NonNegativeInt
    unmapped_chars: NonNegativeInt
    hidden_chars: NonNegativeInt
    image_area_ratio: Annotated[float, Field(ge=0, le=1)]


def expected_text_layer(word_count: int, unmapped_chars: int) -> TextLayer:
    """The text-layer status a page with these counts must report."""
    if word_count == 0:
        return "none"
    return "partial" if unmapped_chars > 0 else "full"


class PageModel(PageInfo):
    """A page with its words and drawn rules."""

    words: tuple[Word, ...]
    rules: tuple[Rule, ...]

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        for word in self.words:
            if word.page != self.number:
                msg = f"word {word.id} is on page {word.page}, not page {self.number}"
                raise ValueError(msg)
        for rule in self.rules:
            if rule.page != self.number:
                msg = f"a rule is on page {rule.page}, not page {self.number}"
                raise ValueError(msg)
        want = expected_text_layer(len(self.words), self.unmapped_chars)
        if self.text_layer != want:
            msg = f"text_layer is {self.text_layer!r} but the page's counts require {want!r}"
            raise ValueError(msg)
        return self


class Source(Frozen):
    """Which file was read: its SHA-256, page count, and base name when read from a path."""

    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    pages: PositiveInt
    file_name: Annotated[str, Field(min_length=1)] | None


class ReaderInfo(Frozen):
    """The versions that produced a reading."""

    inkgrid: str
    pymupdf: str
    mupdf: str


class Reading(Frozen):
    """Every page of one PDF as the text layer states it, with reader findings."""

    schema_version: ReadingSchema = Field(default=READING_SCHEMA, alias="schema")
    source: Source
    reader: ReaderInfo
    pages: Annotated[tuple[PageModel, ...], Field(min_length=1)]
    findings: tuple[Finding, ...]

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if len(self.pages) != self.source.pages:
            msg = f"source says {self.source.pages} pages but {len(self.pages)} are present"
            raise ValueError(msg)
        for index, page in enumerate(self.pages, start=1):
            if page.number != index:
                msg = f"page number {page.number} at position {index}"
                raise ValueError(msg)
        for expected, word in enumerate(self.words()):
            if word.id != expected:
                msg = f"word id {word.id} where {expected} was expected"
                raise ValueError(msg)
        for finding in self.findings:
            if finding.page is not None and finding.page > len(self.pages):
                msg = f"finding {finding.code} names page {finding.page} of {len(self.pages)}"
                raise ValueError(msg)
            if finding.block is not None:
                msg = f"finding {finding.code} names block {finding.block}; a reading has none"
                raise ValueError(msg)
        return self

    def words(self) -> Iterator[Word]:
        """Every word, page by page, in id order."""
        for page in self.pages:
            yield from page.words
