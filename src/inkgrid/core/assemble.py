"""Assembly: keys, regions, ledger, and the proved `Document` (docs/specs/04 section 6)."""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from inkgrid.core.calls import CallSite, Note, calls_in, resolve
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
    Link,
    LinkEnd,
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


def _chain_end(table: ProtoTable, items: Sequence[Item]) -> int:
    """The page of the last part of the chain a table starts or belongs to (spec 09 section 3)."""
    child_of = {
        id(item.continues): item
        for item in items
        if isinstance(item, ProtoTable) and item.continues is not None
    }
    part = table
    while id(part) in child_of:
        part = child_of[id(part)]
    return part.page


def _sites(
    items: Sequence[Item], parts: Sequence[_Parts], register: frozenset[str]
) -> list[CallSite]:
    """Every call candidate of the content blocks: per cell in a table (spec 09 section 2)."""
    sites: list[CallSite] = []
    for order, (item, part) in enumerate(zip(items, parts, strict=True)):
        if isinstance(item, FurnitureLine):
            continue  # a running header cites nothing
        page = part.regions[0].page
        if isinstance(item, ProtoTable):
            through = _chain_end(item, items)  # a long table's notes follow its end
            by_id = {w.id: w for w in part.words}
            for cell in part.grid.cells if part.grid is not None else ():
                if cell.carried:
                    continue  # a carried header owns no words on this page
                cell_words = [by_id[w] for w in cell.word_ids]
                found = calls_in("table", cell_words, cell.text, register)
                anchor = (cell.row, cell.col)
                sites += [CallSite(order, c.page or page, anchor, c, through) for c in found]
            continue
        own = item.label if item.kind == "footnote" else None
        found = calls_in(item.kind, part.words, part.text, register, own_label=own)
        sites += [CallSite(order, c.page or page, None, c) for c in found]
    return sites


def _continuations(items: Sequence[Item]) -> list[Link]:
    """A `continuation` link from each table that continues another, to that table (s. 4)."""
    order_of = {id(item): order for order, item in enumerate(items)}
    links = []
    for order, item in enumerate(items):
        if isinstance(item, ProtoTable) and item.continues is not None:
            parent = order_of.get(id(item.continues))
            if parent is None:
                msg = f"table b{order + 1} continues a table that is not in the document"
                raise InvariantError(msg)
            link = {
                "kind": "continuation",
                "from": LinkEnd(block=f"b{order + 1}"),
                "to": f"b{parent + 1}",
                "status": "resolved",
            }
            links.append(Link.model_validate(link))
    return links


def _calls(items: Sequence[Item], parts: Sequence[_Parts]) -> tuple[list[Link], list[Finding]]:
    """Footnote-call links, and one `call_unresolved` per page with unresolved calls (s. 3)."""
    notes = [
        Note(order, part.regions[0].page, item.label)
        for order, (item, part) in enumerate(zip(items, parts, strict=True))
        if isinstance(item, ProtoBlock) and item.kind == "footnote" and item.label is not None
    ]
    sites = _sites(items, parts, frozenset(n.label for n in notes))
    links: list[Link] = []
    seen: set[tuple[object, ...]] = set()
    unresolved: defaultdict[int, list[str]] = defaultdict(list)
    for site, target in zip(sites, resolve(sites, notes), strict=True):
        call = site.candidate
        key = (site.order, site.cell, call.label, call.method, call.reason)
        if key in seen:
            continue  # one label called twice by one method in one block: one link
        seen.add(key)
        if call.reason is not None:
            status, to = "rejected", None
        elif target is None:
            status, to = "unresolved", None
            unresolved[site.page].append(call.label)
        else:
            status, to = "resolved", f"b{target + 1}"
        link = {
            "kind": "footnote_call",
            "from": LinkEnd(block=f"b{site.order + 1}", cell=site.cell),
            "to": to,
            "label": call.label,
            "method": call.method,
            "status": status,
            "reason": call.reason,
        }
        links.append(Link.model_validate(link))
    findings = []
    for page, labels in sorted(unresolved.items()):
        n = len(labels)
        calls = f"{n} footnote call{'s' if n > 1 else ''} resolve{'' if n > 1 else 's'}"
        detail = f"{calls} to no note: {', '.join(dict.fromkeys(labels))}"
        findings.append(Finding.of(FindingCode.CALL_UNRESOLVED, detail, page=page))
    return links, findings


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
    links, call_findings = _calls(items, parts)
    links = [*_continuations(items), *links]
    found = [*reading.findings, *findings, *call_findings]
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
            links=tuple(links),
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
