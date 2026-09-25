"""Assembly: text, keys, regions, ledger, and the proved `Document` (docs/specs/04 section 6).

The text rule is exactly two transforms (design section 8.4): words join with one space, and a
line-final hyphenated fragment closes up with a lower-case continuation, recorded as a hyphen join.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from inkgrid.core.furniture import FoundFurniture, FurnitureLine
from inkgrid.core.lines import Line
from inkgrid.core.prose import ProtoBlock
from inkgrid.errors import InvariantError
from inkgrid.model.canonical import assign_keys
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.document import (
    Block,
    Document,
    Footnote,
    Furniture,
    Heading,
    Lattice,
    Ledger,
    ListItem,
    Paragraph,
    Producer,
    Region,
)
from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.geometry import Rect
from inkgrid.model.page import PageInfo, PageModel, Reading, Word

WordPair = tuple[int, int]


def _joins(prev: Word, word: Word) -> bool:
    return prev.text.endswith("-") and len(prev.text) > 1 and word.text[:1].islower()


def block_text(lines: Sequence[Line]) -> tuple[str, tuple[WordPair, ...]]:
    """The block's text and its hyphen joins, from its lines in reading order."""
    text = ""
    joins: list[WordPair] = []
    prev: Word | None = None
    for line in lines:
        for index, word in enumerate(line.words):
            if prev is None:
                text = word.text
            elif index == 0 and _joins(prev, word):
                text = text[:-1] + word.text
                joins.append((prev.id, word.id))
            else:
                text += " " + word.text
            prev = word
    return text, tuple(joins)


def _level(size: float, sizes: Sequence[float]) -> int:
    return 1 + sum(1 for s in sizes if s > round(size * 2) / 2)


def _regions(words: Sequence[Word]) -> tuple[Region, ...]:
    pages = sorted({w.page for w in words})
    return tuple(
        Region(page=p, bbox=Rect.union_all(w.bbox for w in words if w.page == p)) for p in pages
    )


def _page_info(page: PageModel) -> PageInfo:
    return PageInfo(
        number=page.number,
        width=page.width,
        height=page.height,
        rotation=page.rotation,
        text_layer=page.text_layer,
        invisible_chars=page.invisible_chars,
        clipped_chars=page.clipped_chars,
        unmapped_chars=page.unmapped_chars,
        hidden_chars=page.hidden_chars,
        image_area_ratio=page.image_area_ratio,
    )


def _ordered(
    reading: Reading, pages: Sequence[Sequence[ProtoBlock]], furniture: FoundFurniture
) -> list[ProtoBlock | FurnitureLine]:
    """Per page: header furniture, content in reading order, then footer and page numbers."""
    out: list[ProtoBlock | FurnitureLine] = []
    for page, blocks in zip(reading.pages, pages, strict=True):
        edge = sorted(
            (f for f in furniture.lines if f.page == page.number), key=lambda f: f.line.top
        )
        out += [f for f in edge if f.role == "header"]
        out += blocks
        out += [f for f in edge if f.role != "header"]
    return out


@dataclass(frozen=True, slots=True)
class _Parts:
    """What a block is made of, before its id and key exist."""

    item: ProtoBlock | FurnitureLine
    kind: str
    words: tuple[Word, ...]
    text: str
    joins: tuple[WordPair, ...]


def _parts(item: ProtoBlock | FurnitureLine) -> _Parts:
    lines = (item.line,) if isinstance(item, FurnitureLine) else item.lines
    text, joins = block_text(lines)
    kind = "furniture" if isinstance(item, FurnitureLine) else item.kind
    return _Parts(item, kind, tuple(w for line in lines for w in line.words), text, joins)


def _block(parts: _Parts, block_id: str, key: str, sizes: Sequence[float]) -> Block:
    common = {
        "id": block_id,
        "key": key,
        "regions": _regions(parts.words),
        "word_ids": tuple(w.id for w in parts.words),
        "text": parts.text,
        "markers": tuple(w.text for w in parts.words if w.superscript),
        "hyphen_joins": parts.joins,
    }
    item = parts.item
    if isinstance(item, FurnitureLine):
        return Furniture.model_validate({**common, "role": item.role})
    match item.kind:
        case "heading":
            level = _level(item.size, sizes)
            return Heading.model_validate({**common, "level": level, "number": item.number})
        case "list_item":
            return ListItem.model_validate({**common, "label": item.label})
        case "footnote":
            return Footnote.model_validate({**common, "label": item.label})
        case "paragraph":
            return Paragraph.model_validate(common)


def assemble(
    reading: Reading,
    pages: Sequence[Sequence[ProtoBlock]],
    furniture: FoundFurniture,
    *,
    lexicon: Lexicon,
    profile: Profile,
    lattice: Lattice,
) -> Document:
    """Build the `Document`. A failed invariant is a bug in inkgrid: `InvariantError`."""
    items = _ordered(reading, pages, furniture)
    sizes = sorted(
        {round(b.size * 2) / 2 for b in items if isinstance(b, ProtoBlock) and b.kind == "heading"}
    )
    parts = [_parts(item) for item in items]
    keys = assign_keys([(p.kind, p.text) for p in parts])
    words = tuple(w for page in reading.pages for w in page.words)
    findings = list(reading.findings)
    if len(reading.pages) > profile.long_document_pages and not furniture.word_ids:
        detail = f"{len(reading.pages)} pages and no running header, footer, or page number"
        findings.append(Finding.of(FindingCode.NO_FURNITURE_LONG_DOCUMENT, detail))
    furniture_chars = sum(len(w.text) for w in words if w.id in furniture.word_ids)
    try:
        return Document(
            source=reading.source,
            producer=Producer(
                inkgrid=reading.reader.inkgrid,
                pymupdf=reading.reader.pymupdf,
                mupdf=reading.reader.mupdf,
                camelot=None,
                pypdfium2=None,
                lexicon=lexicon.id,
                profile=profile.id,
                lattice=lattice,
            ),
            pages=tuple(_page_info(page) for page in reading.pages),
            words=words,
            blocks=tuple(
                _block(p, f"b{index}", key, sizes)
                for index, (p, key) in enumerate(zip(parts, keys, strict=True), 1)
            ),
            findings=tuple(findings),
            ledger=Ledger(
                content_chars=sum(len(w.text) for w in words) - furniture_chars,
                furniture_chars=furniture_chars,
                invisible_chars=sum(p.invisible_chars for p in reading.pages),
                clipped_chars=sum(p.clipped_chars for p in reading.pages),
            ),
        )
    except ValueError as exc:  # pydantic's ValidationError: the core never imports pydantic
        raise InvariantError(str(exc)) from exc
