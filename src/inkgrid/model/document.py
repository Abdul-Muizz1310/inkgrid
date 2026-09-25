"""The output contract, `inkgrid.document/1`.

A `Document` that exists satisfies every invariant of `docs/specs/01-model.md` section 5:

- local invariants are validators on the type that owns them (a grid tiles, a table's cells
  partition its words);
- cross-object invariants (the word partition, text against words, links, the ledger) live in
  `inkgrid.model.invariants`, which `Document`'s validator calls.
"""

from itertools import pairwise
from typing import Annotated, Final, Literal, Self

from pydantic import Field, NonNegativeInt, PositiveInt, model_validator

from inkgrid.model.base import Frozen
from inkgrid.model.findings import BLOCK_ID, Finding, Severity
from inkgrid.model.geometry import Interval, Rect
from inkgrid.model.invariants import check_document, check_text_shape
from inkgrid.model.page import PageInfo, Source, Word

DocumentSchema = Literal["inkgrid.document/1"]
DOCUMENT_SCHEMA: Final[DocumentSchema] = "inkgrid.document/1"

BlockId = Annotated[str, Field(pattern=BLOCK_ID)]
BlockKey = Annotated[str, Field(pattern=r"^k[0-9a-f]{16}(?::(?:[2-9]|[1-9][0-9]+))?$")]
NonEmpty = Annotated[str, Field(min_length=1)]
Anchor = tuple[NonNegativeInt, NonNegativeInt]
"""A `(row, col)` cell anchor."""
WordPair = tuple[NonNegativeInt, NonNegativeInt]
"""A hyphen join `(a, b)`: word a's final hyphen is dropped and b follows it with no space."""


Lattice = Literal["combined", "raster"]
"""How Camelot reads ruled tables (used from M2; recorded in `Producer.lattice`)."""


class Region(Frozen):
    """The box a block occupies on one page."""

    page: PositiveInt
    bbox: Rect


class Cell(Frozen):
    """One cell of a grid, anchored at `(row, col)`, spanning `row_span` x `col_span` positions.

    A blank cell (no words, text "") is part of a table's shape. A `carried` cell is a header copied
    onto a continuation page: it owns no words there, and `source` names the parent-table cells it
    copies.
    """

    row: NonNegativeInt
    col: NonNegativeInt
    row_span: PositiveInt = 1
    col_span: PositiveInt = 1
    text: str
    word_ids: tuple[NonNegativeInt, ...] = ()
    carried: bool = False
    source: tuple[Anchor, ...] = ()
    markers: tuple[NonEmpty, ...] = ()

    @model_validator(mode="after")
    def _ownership(self) -> Self:
        where = f"cell ({self.row}, {self.col})"
        if self.carried:
            if self.word_ids:
                msg = f"{where}: a carried cell owns no words"
                raise ValueError(msg)
            if not self.text:
                msg = f"{where}: a carried cell must have text"
                raise ValueError(msg)
            if not self.source:
                msg = f"{where}: a carried cell must name its source cells"
                raise ValueError(msg)
        else:
            if self.source:
                msg = f"{where}: only a carried cell has a source"
                raise ValueError(msg)
            if not self.word_ids and self.text:
                msg = f"{where}: a cell with no words has no text"
                raise ValueError(msg)
        if len(set(self.word_ids)) != len(self.word_ids):
            msg = f"{where}: lists a word twice"
            raise ValueError(msg)
        check_text_shape(self.text, where)
        return self


class Grid(Frozen):
    """A table's cell grid: row and column bands and the cells that tile them."""

    n_rows: PositiveInt
    n_cols: PositiveInt
    row_bands: tuple[Interval, ...]
    col_bands: tuple[Interval, ...]
    header_rows: NonNegativeInt
    banner_rows: tuple[NonNegativeInt, ...] = ()
    source: Literal["lattice", "corridor"]
    cells: tuple[Cell, ...]

    @model_validator(mode="after")
    def _shape(self) -> Self:
        self._check_bands()
        self._check_row_roles()
        self._check_tiling()
        return self

    def _check_bands(self) -> None:
        for name, bands, count in (
            ("row_bands", self.row_bands, self.n_rows),
            ("col_bands", self.col_bands, self.n_cols),
        ):
            if len(bands) != count:
                msg = f"{name} has {len(bands)} bands for {count} positions"
                raise ValueError(msg)
            for a, b in pairwise(bands):
                if b.start < a.start:
                    msg = f"{name} must be sorted"
                    raise ValueError(msg)
                if a.end > b.start:
                    msg = f"{name} overlap at [{a.start}, {a.end}) and [{b.start}, {b.end})"
                    raise ValueError(msg)

    def _check_row_roles(self) -> None:
        if self.header_rows > self.n_rows:
            msg = f"header_rows {self.header_rows} exceeds n_rows {self.n_rows}"
            raise ValueError(msg)
        rows = self.banner_rows
        if list(rows) != sorted(set(rows)) or any(r >= self.n_rows for r in rows):
            msg = "banner_rows must be sorted, unique, and inside the grid"
            raise ValueError(msg)

    def _check_tiling(self) -> None:
        """Every position is covered by exactly one cell; checked per row over column intervals."""
        anchors = [(c.row, c.col) for c in self.cells]
        if anchors != sorted(set(anchors)):
            msg = "cells must be sorted by (row, col) with unique anchors"
            raise ValueError(msg)
        rows: list[list[tuple[int, int]]] = [[] for _ in range(self.n_rows)]
        for cell in self.cells:
            if cell.row + cell.row_span > self.n_rows or cell.col + cell.col_span > self.n_cols:
                msg = f"cell ({cell.row}, {cell.col}) runs past the grid bounds"
                raise ValueError(msg)
            for r in range(cell.row, cell.row + cell.row_span):
                rows[r].append((cell.col, cell.col + cell.col_span))
        for r, spans in enumerate(rows):
            at = 0
            for start, end in sorted(spans):
                if start < at:
                    msg = f"position ({r}, {start}) is covered twice"
                    raise ValueError(msg)
                if start > at:
                    msg = f"position ({r}, {at}) is covered by no cell"
                    raise ValueError(msg)
                at = end
            if at < self.n_cols:
                msg = f"position ({r}, {at}) is covered by no cell"
                raise ValueError(msg)

    def cell_rect(self, cell: Cell) -> Rect:
        """The rectangle a cell covers, from its first to its last band."""
        return Rect(
            self.col_bands[cell.col].start,
            self.row_bands[cell.row].start,
            self.col_bands[cell.col + cell.col_span - 1].end,
            self.row_bands[cell.row + cell.row_span - 1].end,
        )


class BlockBase(Frozen):
    """Fields every block kind shares. `word_ids` are in reading order."""

    kind: str
    id: BlockId
    key: BlockKey
    regions: Annotated[tuple[Region, ...], Field(min_length=1)]
    word_ids: Annotated[tuple[NonNegativeInt, ...], Field(min_length=1)]
    text: str
    markers: tuple[NonEmpty, ...] = ()
    hyphen_joins: tuple[WordPair, ...] = ()

    @model_validator(mode="after")
    def _block_shape(self) -> Self:
        if len(set(self.word_ids)) != len(self.word_ids):
            msg = f"block {self.id} lists a word twice (duplicate word id)"
            raise ValueError(msg)
        check_text_shape(self.text, f"block {self.id}")
        position = {word: index for index, word in enumerate(self.word_ids)}
        if len(set(self.hyphen_joins)) != len(self.hyphen_joins):
            msg = f"block {self.id}: a hyphen join is listed twice"
            raise ValueError(msg)
        for a, b in self.hyphen_joins:
            if a == b:
                msg = f"block {self.id}: a hyphen join needs two different words, got ({a}, {b})"
                raise ValueError(msg)
            if a not in position or b not in position:
                msg = f"block {self.id}: hyphen join ({a}, {b}) names a word outside the block"
                raise ValueError(msg)
            if position[b] != position[a] + 1:
                msg = f"block {self.id}: in hyphen join ({a}, {b}), word {b} must follow word {a}"
                raise ValueError(msg)
        pages = [r.page for r in self.regions]
        if any(q <= p for p, q in pairwise(pages)):
            msg = f"block {self.id}: region pages must be strictly increasing, got {pages}"
            raise ValueError(msg)
        return self


class Heading(BlockBase):
    """A title line. `level` 1 is the document's largest heading size."""

    kind: Literal["heading"] = "heading"
    level: PositiveInt
    number: NonEmpty | None = None


class Paragraph(BlockBase):
    """Running prose."""

    kind: Literal["paragraph"] = "paragraph"


class ListItem(BlockBase):
    """A bulleted or enumerated item; `label` is the bullet or enumerator as printed."""

    kind: Literal["list_item"] = "list_item"
    label: NonEmpty


class Footnote(BlockBase):
    """A note definition; `label` is its printed number or symbol."""

    kind: Literal["footnote"] = "footnote"
    label: NonEmpty


class Definition(BlockBase):
    """One glossary entry, split into its term and body."""

    kind: Literal["definition"] = "definition"
    term: NonEmpty
    body: NonEmpty

    @model_validator(mode="after")
    def _text_is_term_and_body(self) -> Self:
        if self.text != f"{self.term} {self.body}":
            msg = f"definition {self.id}: text must be the term, a space, then the body"
            raise ValueError(msg)
        return self


class Table(BlockBase):
    """A table on one page; its non-carried cells partition its words."""

    kind: Literal["table"] = "table"
    grid: Grid

    @model_validator(mode="after")
    def _cells_partition_words(self) -> Self:
        if len(self.regions) != 1:
            msg = f"table {self.id} must have exactly one region, got {len(self.regions)}"
            raise ValueError(msg)
        members = set(self.word_ids)
        seen: dict[int, tuple[int, int]] = {}
        for cell in self.grid.cells:
            for word in cell.word_ids:
                if word not in members:
                    msg = (
                        f"cell ({cell.row}, {cell.col}) holds word {word}, "
                        f"which is not a word of table {self.id}"
                    )
                    raise ValueError(msg)
                if word in seen:
                    msg = f"word {word} of table {self.id} is in two cells"
                    raise ValueError(msg)
                seen[word] = (cell.row, cell.col)
        missing = sorted(members - seen.keys())
        if missing:
            msg = f"word {missing[0]} of table {self.id} is in no cell"
            raise ValueError(msg)
        in_cells = tuple(word for cell in self.grid.cells for word in cell.word_ids)
        if self.word_ids != in_cells:
            msg = f"table {self.id} must list its words cell by cell in (row, col) order"
            raise ValueError(msg)
        return self


class Furniture(BlockBase):
    """A running header, footer, or page number."""

    kind: Literal["furniture"] = "furniture"
    role: Literal["header", "footer", "page_number"]


Block = Annotated[
    Heading | Paragraph | ListItem | Footnote | Definition | Table | Furniture,
    Field(discriminator="kind"),
]


class LinkEnd(Frozen):
    """Where a link starts: a block, and optionally a cell anchor inside a table."""

    block: BlockId
    cell: Anchor | None = None


class Link(Frozen):
    """A relationship the page prints: a footnote call, or a table continuing across pages."""

    kind: Literal["footnote_call", "continuation"]
    from_: LinkEnd = Field(alias="from")
    to: BlockId | None = None
    label: NonEmpty | None = None
    method: Literal["superscript", "parenthetical", "named"] | None = None
    status: Literal["resolved", "unresolved", "rejected"]
    reason: NonEmpty | None = None

    @model_validator(mode="after")
    def _status(self) -> Self:
        if self.status == "resolved" and self.to is None:
            msg = "a resolved link needs a target (to)"
            raise ValueError(msg)
        if self.status != "resolved" and self.to is not None:
            msg = f"an {self.status} link cannot name a target"
            raise ValueError(msg)
        if self.status == "rejected" and self.reason is None:
            msg = "a rejected link needs a reason"
            raise ValueError(msg)
        if self.kind == "footnote_call":
            if self.label is None:
                msg = "a footnote_call needs a label"
                raise ValueError(msg)
            if self.method is None:
                msg = "a footnote_call needs a method"
                raise ValueError(msg)
        else:
            if self.method is not None:
                msg = "a continuation has no method"
                raise ValueError(msg)
            if self.status != "resolved":
                msg = "a continuation is always resolved"
                raise ValueError(msg)
        return self


class Ledger(Frozen):
    """Characters by disposition, and the proof that every word is owned exactly once."""

    content_chars: NonNegativeInt
    furniture_chars: NonNegativeInt
    invisible_chars: NonNegativeInt
    clipped_chars: NonNegativeInt
    partition: Literal["proved"] = "proved"


class Producer(Frozen):
    """The versions and settings that produced a document."""

    inkgrid: str
    pymupdf: str
    mupdf: str
    camelot: str | None
    pypdfium2: str | None
    lexicon: NonEmpty
    profile: NonEmpty
    lattice: Lattice


class Document(Frozen):
    """One PDF read into blocks, in reading order, with its links, findings and ledger."""

    schema_version: DocumentSchema = Field(default=DOCUMENT_SCHEMA, alias="schema")
    source: Source
    producer: Producer
    pages: Annotated[tuple[PageInfo, ...], Field(min_length=1)]
    words: tuple[Word, ...]
    blocks: tuple[Block, ...]
    links: tuple[Link, ...] = ()
    findings: tuple[Finding, ...] = ()
    ledger: Ledger

    @model_validator(mode="after")
    def _contract(self) -> Self:
        check_document(self)
        return self

    @property
    def complete(self) -> bool:
        """True when no finding has error severity."""
        return all(f.severity is not Severity.ERROR for f in self.findings)

    def tables(self) -> tuple[Table, ...]:
        """The table blocks, in reading order."""
        return tuple(b for b in self.blocks if isinstance(b, Table))
