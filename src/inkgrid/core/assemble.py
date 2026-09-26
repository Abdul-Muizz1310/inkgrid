"""Assembly: keys, regions, ledger, and the proved `Document` (docs/specs/04 section 6)."""

from collections.abc import Sequence
from dataclasses import dataclass

from inkgrid.core.furniture import FoundFurniture, FurnitureLine
from inkgrid.core.prose import ProtoBlock
from inkgrid.core.tables.grid import table_parts
from inkgrid.core.tables.lattice import ProtoTable
from inkgrid.core.text import WordPair, block_text
from inkgrid.errors import InvariantError
from inkgrid.model.canonical import assign_keys
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.document import (
    Block,
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


Item = ProtoBlock | FurnitureLine | ProtoTable


def _overlaps(block: ProtoBlock, table: ProtoTable) -> bool:
    """True when the block and the table share some horizontal extent."""
    x0 = min(line.x0 for line in block.lines)
    x1 = max(line.x1 for line in block.lines)
    return x0 < table.bbox.x1 and x1 > table.bbox.x0


def _slot(blocks: Sequence[ProtoBlock], table: ProtoTable) -> int:
    """Where a table goes among a page's blocks: within the column it shares with them."""
    beside = [i for i, b in enumerate(blocks) if _overlaps(b, table)]
    below = [i for i in beside if blocks[i].lines[0].top >= table.bbox.y0]
    if below:
        return below[0]
    return beside[-1] + 1 if beside else len(blocks)


def _with_tables(blocks: Sequence[ProtoBlock], tables: Sequence[ProtoTable]) -> list[Item]:
    """Content in reading order, each table before the first block below it in its column."""
    before: dict[int, list[ProtoTable]] = {}
    for table in sorted(tables, key=lambda t: t.bbox.y0):
        before.setdefault(_slot(blocks, table), []).append(table)
    out: list[Item] = []
    for index, block in enumerate(blocks):
        out += before.get(index, [])
        out.append(block)
    out += before.get(len(blocks), [])
    return out


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
        out += _with_tables(blocks, page_tables)
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


def _parts(item: Item, words: Sequence[Word], pages: Sequence[PageInfo]) -> _Parts:
    """The block's parts, with each word as the reading has it (layout may have turned it)."""
    if isinstance(item, ProtoTable):
        table = table_parts(item, words, pages[item.page - 1])
        return _Parts(
            item, "table", table.words, table.text, table.joins, (table.region,), table.grid
        )
    lines = (item.line,) if isinstance(item, FurnitureLine) else item.lines
    text, joins = block_text(lines)
    kind = "furniture" if isinstance(item, FurnitureLine) else item.kind
    own = tuple(words[w.id] for line in lines for w in line.words)
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
    sizes = sorted(
        {round(b.size * 2) / 2 for b in items if isinstance(b, ProtoBlock) and b.kind == "heading"}
    )
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
