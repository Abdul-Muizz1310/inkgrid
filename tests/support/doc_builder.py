"""Build valid inkgrid Documents from short descriptions, for contract tests.

A failure test takes a valid document, dumps it with `as_json`, breaks one field, and parses it back
with `from_json`, so every check runs exactly as it does on real input.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from inkgrid.model.canonical import assign_keys
from inkgrid.model.document import (
    Cell,
    Definition,
    Document,
    Footnote,
    Furniture,
    Grid,
    Heading,
    Ledger,
    Link,
    ListItem,
    Paragraph,
    Producer,
    Region,
    Table,
)
from inkgrid.model.findings import Finding
from inkgrid.model.geometry import Interval, Rect
from inkgrid.model.page import PageInfo, Source, Word

CHAR_WIDTH = 5.0
WORD_HEIGHT = 10.0
PRODUCER = Producer(
    inkgrid="0.1.0.dev0",
    pymupdf="1.28.2",
    mupdf="1.28.2",
    camelot=None,
    pypdfium2=None,
    lexicon="generic/1",
    profile="default/1",
    lattice="combined",
)


@dataclass(frozen=True)
class W:
    """A word to place: its text, top-left corner, and page; `rect` overrides the laid-out box."""

    text: str
    x0: float
    y0: float
    page: int = 1
    superscript: bool = False
    rect: Rect | None = None

    @property
    def box(self) -> Rect:
        if self.rect is not None:
            return self.rect
        return Rect(self.x0, self.y0, self.x0 + CHAR_WIDTH * len(self.text), self.y0 + WORD_HEIGHT)


def line(texts: Sequence[str], *, page: int = 1, y: float = 100.0, x: float = 72.0) -> list[W]:
    """Words laid out left to right on one line, 5 pt apart."""
    out = []
    for text in texts:
        out.append(W(text, x, y, page))
        x += CHAR_WIDTH * len(text) + CHAR_WIDTH
    return out


@dataclass
class C:
    """A table cell: its anchor, span, and the table-local indexes of its words."""

    row: int
    col: int
    words: list[int] = field(default_factory=list)
    row_span: int = 1
    col_span: int = 1
    carried_text: str | None = None
    source: tuple[tuple[int, int], ...] = ()


@dataclass
class B:
    """A block to build. `fields` carries the kind's own fields (level, label, term, ...)."""

    kind: str
    words: list[W]
    fields: dict[str, Any] = field(default_factory=dict)
    text: str | None = None
    joins: list[tuple[int, int]] = field(default_factory=list)
    row_bands: list[tuple[float, float]] = field(default_factory=list)
    col_bands: list[tuple[float, float]] = field(default_factory=list)
    cells: list[C] = field(default_factory=list)
    header_rows: int = 0
    banner_rows: tuple[int, ...] = ()
    grid_source: str = "corridor"
    frame: int = 0


def joined_text(texts: Sequence[str], joins: Sequence[tuple[int, int]]) -> str:
    """Words joined by single spaces; a join `(i, i+1)` drops word i's hyphen and the space."""
    glue = {a for a, b in joins if b == a + 1}
    out = ""
    for i, text in enumerate(texts):
        if i > 0 and i - 1 not in glue:
            out += " "
        out += text[:-1] if i in glue else text
    return out


def _table_text(cells: Sequence[Cell]) -> str:
    rows: dict[int, list[str]] = {}
    for cell in sorted(cells, key=lambda c: (c.row, c.col)):
        if not cell.carried and cell.text:
            rows.setdefault(cell.row, []).append(cell.text)
    return "\n".join(" ".join(parts) for _, parts in sorted(rows.items()))


def _regions(words: Sequence[W]) -> tuple[Region, ...]:
    pages = sorted({w.page for w in words})
    return tuple(
        Region(page=p, bbox=Rect.union_all(w.box for w in words if w.page == p)) for p in pages
    )


def build(
    blocks: Sequence[B],
    *,
    pages: int = 1,
    links: Sequence[Link] = (),
    findings: Sequence[Finding] = (),
) -> Document:
    """Assemble a valid Document: ids, keys, regions, text, pages and ledger are derived."""
    words: list[Word] = []
    furniture_ids: set[int] = set()
    specs: list[tuple[B, tuple[int, ...], str, Grid | None, int]] = []
    for spec in blocks:
        first = len(words)
        for w in spec.words:
            words.append(
                Word(
                    id=len(words),
                    page=w.page,
                    bbox=w.box,
                    text=w.text,
                    size=10.0,
                    font="Helvetica",
                    bold=False,
                    italic=False,
                    superscript=w.superscript,
                    hidden=False,
                    horizontal=True,
                )
            )
        ids = tuple(range(first, len(words)))
        if spec.kind == "furniture":
            furniture_ids.update(ids)
        grid = None
        if spec.kind == "table":
            cells = tuple(
                Cell(
                    row=c.row,
                    col=c.col,
                    row_span=c.row_span,
                    col_span=c.col_span,
                    text=c.carried_text
                    if c.carried_text is not None
                    else " ".join(spec.words[i].text for i in c.words),
                    word_ids=tuple(ids[i] for i in c.words),
                    carried=c.carried_text is not None,
                    source=c.source,
                )
                for c in spec.cells
            )
            # A table reads its words cell by cell in (row, col) order.
            ids = tuple(w for c in sorted(cells, key=lambda c: (c.row, c.col)) for w in c.word_ids)
            grid = Grid(
                n_rows=len(spec.row_bands),
                n_cols=len(spec.col_bands),
                row_bands=tuple(Interval(a, b) for a, b in spec.row_bands),
                col_bands=tuple(Interval(a, b) for a, b in spec.col_bands),
                header_rows=spec.header_rows,
                banner_rows=spec.banner_rows,
                source=spec.grid_source,
                frame=spec.frame,
                cells=cells,
            )
            text = spec.text if spec.text is not None else _table_text(cells)
        else:
            text = (
                spec.text
                if spec.text is not None
                else joined_text([w.text for w in spec.words], spec.joins)
            )
        specs.append((spec, ids, text, grid, first))

    keys = assign_keys([(spec.kind, text) for spec, _, text, _, _ in specs])
    built: list[Any] = []
    for index, ((spec, ids, text, grid, first), key) in enumerate(zip(specs, keys, strict=True), 1):
        common: dict[str, Any] = {
            "id": f"b{index}",
            "key": key,
            "regions": _regions(spec.words),
            "word_ids": ids,
            "text": text,
            "hyphen_joins": tuple((first + a, first + b) for a, b in spec.joins),
            "markers": tuple(words[i].text for i in ids if words[i].superscript),
        }
        kinds: dict[str, type[Any]] = {
            "heading": Heading,
            "paragraph": Paragraph,
            "list_item": ListItem,
            "footnote": Footnote,
            "definition": Definition,
            "furniture": Furniture,
        }
        if spec.kind == "table":
            built.append(Table(**common, grid=grid))
        else:
            built.append(kinds[spec.kind](**common, **spec.fields))

    on_page = {w.page for w in words}
    page_infos = tuple(
        PageInfo(
            number=n,
            width=612.0,
            height=792.0,
            rotation=0,
            text_layer="full" if n in on_page else "none",
            invisible_chars=0,
            clipped_chars=0,
            unmapped_chars=0,
            hidden_chars=0,
            image_area_ratio=0.0,
        )
        for n in range(1, pages + 1)
    )
    content = sum(len(w.text) for w in words if w.id not in furniture_ids)
    furniture = sum(len(w.text) for w in words if w.id in furniture_ids)
    return Document(
        source=Source(sha256="0" * 64, pages=pages, file_name=None),
        producer=PRODUCER,
        pages=page_infos,
        words=tuple(words),
        blocks=tuple(built),
        links=tuple(links),
        findings=tuple(findings),
        ledger=Ledger(
            content_chars=content, furniture_chars=furniture, invisible_chars=0, clipped_chars=0
        ),
    )


def as_json(doc: Document) -> dict[str, Any]:
    """The document as plain JSON data, ready to break one field."""
    return json.loads(doc.model_dump_json())


def from_json(data: dict[str, Any]) -> Document:
    """Parse JSON data back through every validator."""
    return Document.model_validate_json(json.dumps(data))


def without_last_paragraph(doc: Document) -> tuple[Document, str]:
    """The document with its last block, a paragraph holding the last words, removed.

    Returns the document and the removed words' characters, run together, as a verifier would see
    them lost.
    """
    data = as_json(doc)
    last = data["blocks"].pop()
    assert last["kind"] == "paragraph"
    ids = set(last["word_ids"])
    assert ids == set(range(len(data["words"]) - len(ids), len(data["words"])))
    removed = [w["text"] for w in data["words"] if w["id"] in ids]
    data["words"] = [w for w in data["words"] if w["id"] not in ids]
    data["ledger"]["content_chars"] -= sum(len(t) for t in removed)
    return from_json(data), "".join(removed)
