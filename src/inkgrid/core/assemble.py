"""Assembly: keys, regions, ledger, and the proved `Document` (docs/specs/04 section 6)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from inkgrid.core.furniture import FoundFurniture, FurnitureLine
from inkgrid.core.order import heading_level, heading_sizes, reading_order
from inkgrid.core.prose import ProtoBlock
from inkgrid.core.tables.grid import table_parts
from inkgrid.core.tables.proto import ProtoTable
from inkgrid.core.text import WordPair, block_text
from inkgrid.errors import InvariantError
from inkgrid.model.canonical import assign_keys
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.document import (
    Block,
    Definition,
    Document,
    Footnote,
    Furniture,
    Grid,
    Heading,
    Lattice,
    Ledger,
    ListItem,
    Paragraph,
    Producer,
    Region,
    Table,
)
from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.geometry import Rect
from inkgrid.model.page import PageInfo, PageModel, Reading, Word


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


Item = ProtoBlock | FurnitureLine | ProtoTable


def _ordered(
    reading: Reading,
    pages: Sequence[Sequence[ProtoBlock]],
    tables: Sequence[Sequence[ProtoTable]],
    furniture: FoundFurniture,
) -> list[Item]:
    """Per page: header furniture, content with its tables, then footer and page numbers."""
    out: list[Item] = []
    for page, blocks, page_tables in zip(reading.pages, pages, tables, strict=True):
        edge = sorted(
            (f for f in furniture.lines if f.page == page.number), key=lambda f: f.line.top
        )
        out += [f for f in edge if f.role == "header"]
        out += reading_order(blocks, page_tables)
        out += [f for f in edge if f.role != "header"]
    return out


@dataclass(frozen=True, slots=True)
class _Parts:
    """What a block is made of, before its id and key exist."""

    item: Item
    kind: str
    words: tuple[Word, ...]
    text: str
    joins: tuple[WordPair, ...]
    regions: tuple[Region, ...]
    grid: Grid | None = None
    term: str = ""  # a definition's: its text is the term, a space, then the body
    body: str = ""


def _parts(item: Item, words: Sequence[Word], pages: Sequence[PageInfo]) -> _Parts:
    """The block's parts, with each word as the reading has it (layout may have turned it)."""
    if isinstance(item, ProtoTable):
        table = table_parts(item, words, pages[item.page - 1])
        return _Parts(
            item, "table", table.words, table.text, table.joins, (table.region,), table.grid
        )
    lines = (item.line,) if isinstance(item, FurnitureLine) else item.lines
    kind = "furniture" if isinstance(item, FurnitureLine) else item.kind
    own = tuple(words[w.id] for line in lines for w in line.words)
    if isinstance(item, ProtoBlock) and item.kind == "definition":
        # The term and the body render apart, so the text is exactly `term + " " + body` (8c).
        term, term_joins = block_text(item.term)
        body, body_joins = block_text(lines[len(item.term) :])
        text = f"{term} {body}"
        return _Parts(
            item, kind, own, text, term_joins + body_joins, _regions(own), term=term, body=body
        )
    text, joins = block_text(lines)
    return _Parts(item, kind, own, text, joins, _regions(own))


def _block(parts: _Parts, block_id: str, key: str, sizes: Sequence[float]) -> Block:
    common = {
        "id": block_id,
        "key": key,
        "regions": parts.regions,
        "word_ids": tuple(w.id for w in parts.words),
        "text": parts.text,
        "markers": tuple(w.text for w in parts.words if w.superscript),
        "hyphen_joins": parts.joins,
    }
    item = parts.item
    if isinstance(item, ProtoTable):
        # table_parts built the grid once; rebuilding it here would double the cost.
        return Table.model_validate({**common, "grid": parts.grid})
    if isinstance(item, FurnitureLine):
        return Furniture.model_validate({**common, "role": item.role})
    return _prose_block(item, parts, common, sizes)


def _prose_block(
    item: ProtoBlock, parts: _Parts, common: Mapping[str, object], sizes: Sequence[float]
) -> Block:
    match item.kind:
        case "heading":
            level = heading_level(item.size, sizes)
            return Heading.model_validate({**common, "level": level, "number": item.number})
        case "list_item":
            return ListItem.model_validate({**common, "label": item.label})
        case "footnote":
            return Footnote.model_validate({**common, "label": item.label})
        case "paragraph":
            return Paragraph.model_validate(common)
        case "definition":
            return Definition.model_validate({**common, "term": parts.term, "body": parts.body})


def assemble(
    reading: Reading,
    pages: Sequence[Sequence[ProtoBlock]],
    furniture: FoundFurniture,
    *,
    lexicon: Lexicon,
    profile: Profile,
    lattice: Lattice,
    tables: Sequence[Sequence[ProtoTable]] | None = None,
    findings: Sequence[Finding] = (),
    camelot: str | None = None,
) -> Document:
    """Build the `Document`. A failed invariant is a bug in inkgrid: `InvariantError`.

    `tables` holds each page's proto tables, `findings` what the table stage found, and `camelot`
    the Camelot version when it read any page.
    """
    per_page = tables if tables is not None else [() for _ in reading.pages]
    items = _ordered(reading, pages, per_page, furniture)
    infos = tuple(_page_info(page) for page in reading.pages)
    sizes = heading_sizes(items)
    words = tuple(w for page in reading.pages for w in page.words)
    parts = [_parts(item, words, infos) for item in items]
    keys = assign_keys([(p.kind, p.text) for p in parts])
    found = [*reading.findings, *findings]
    if len(reading.pages) > profile.long_document_pages and not furniture.word_ids:
        detail = f"{len(reading.pages)} pages and no running header, footer, or page number"
        found.append(Finding.of(FindingCode.NO_FURNITURE_LONG_DOCUMENT, detail))
    furniture_chars = sum(len(w.text) for w in words if w.id in furniture.word_ids)
    try:
        return Document(
            source=reading.source,
            producer=Producer(
                inkgrid=reading.reader.inkgrid,
                pymupdf=reading.reader.pymupdf,
                mupdf=reading.reader.mupdf,
                camelot=camelot,
                pypdfium2=None,
                lexicon=lexicon.id,
                profile=profile.id,
                lattice=lattice,
            ),
            pages=infos,
            words=words,
            blocks=tuple(
                _block(p, f"b{index}", key, sizes)
                for index, (p, key) in enumerate(zip(parts, keys, strict=True), 1)
            ),
            findings=tuple(found),
            ledger=Ledger(
                content_chars=sum(len(w.text) for w in words) - furniture_chars,
                furniture_chars=furniture_chars,
                invisible_chars=sum(p.invisible_chars for p in reading.pages),
                clipped_chars=sum(p.clipped_chars for p in reading.pages),
            ),
        )
    except ValueError as exc:  # pydantic's ValidationError: the core never imports pydantic
        raise InvariantError(str(exc)) from exc
