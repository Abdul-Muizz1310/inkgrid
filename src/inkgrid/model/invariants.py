"""Cross-object invariants of the output contract (`docs/specs/01-model.md` section 5).

`check_document` raises `ValueError` naming the first violation it finds. The checks run in a fixed
order, so the reported violation is the most basic one: the page and word structure first, then the
partition, then links, text, regions, and cells, and the ledger last.
"""

from collections import Counter
from collections.abc import Sequence
from typing import TYPE_CHECKING, NoReturn

from inkgrid.model.canonical import assign_keys
from inkgrid.model.page import expected_text_layer

if TYPE_CHECKING:
    from inkgrid.model.document import Block, Document, Table
    from inkgrid.model.page import Word

TEXT_SPACE = " "
TEXT_BREAK = "\n"


def check_text_shape(text: str, where: str) -> None:
    """Reject whitespace other than single spaces and newlines between characters."""
    if text != text.strip(TEXT_SPACE + TEXT_BREAK):
        msg = f"{where}: text has leading or trailing whitespace"
        raise ValueError(msg)
    previous_blank = False
    for ch in text:
        if ch.isspace():
            if ch not in (TEXT_SPACE, TEXT_BREAK):
                msg = f"{where}: text holds whitespace U+{ord(ch):04X}; only space and newline"
                raise ValueError(msg)
            if previous_blank:
                msg = f"{where}: text holds two whitespace characters in a row"
                raise ValueError(msg)
            previous_blank = True
        else:
            previous_blank = False


def spelled(word_texts: Sequence[str], joined: Sequence[bool]) -> str:
    """The words' characters in order, with each joined word's final hyphen removed."""
    return "".join(t[:-1] if j else t for t, j in zip(word_texts, joined, strict=True))


def text_matches_words(text: str, word_texts: Sequence[str], joined: Sequence[bool]) -> bool:
    """True when the non-whitespace characters of `text`, in order, spell the words.

    `joined[i]` marks word i as the first half of a hyphen join, whose final hyphen is dropped.
    Ordered, not a multiset: words `12` and `34` can never read as `13 24` (invariant 7).
    """
    return spelled(word_texts, joined) == "".join(
        ch for ch in text if ch not in (TEXT_SPACE, TEXT_BREAK)
    )


def strip_label(text: str) -> str:
    """A footnote label as the page prints it, without its brackets and full stop."""
    return text.strip("().")


def _fail(msg: str) -> NoReturn:
    raise ValueError(msg)


def _check_pages_and_words(doc: "Document") -> None:
    n_pages = len(doc.pages)
    if n_pages != doc.source.pages:
        _fail(f"source says {doc.source.pages} pages but {n_pages} are present")
    for index, page in enumerate(doc.pages, start=1):
        if page.number != index:
            _fail(f"page number {page.number} at position {index}")
    last_page = 1
    per_page: Counter[int] = Counter()
    for expected, word in enumerate(doc.words):
        if word.id != expected:
            _fail(f"word id {word.id} where {expected} was expected")
        if word.page > n_pages:
            _fail(f"word {word.id} is on page {word.page} of {n_pages}")
        if word.page < last_page:
            _fail(f"word {word.id} is on page {word.page} after a word on page {last_page}")
        last_page = word.page
        per_page[word.page] += 1
    for page in doc.pages:
        want = expected_text_layer(per_page[page.number], page.unmapped_chars)
        if page.text_layer != want:
            _fail(f"page {page.number}: text_layer is {page.text_layer!r}, counts require {want!r}")


def _check_partition(doc: "Document") -> None:
    n_words = len(doc.words)
    owner: dict[int, str] = {}
    for block in doc.blocks:
        for word in block.word_ids:
            if word >= n_words:
                _fail(f"block {block.id} names word {word}, which does not exist")
            if word in owner:
                _fail(f"word {word} is in blocks {owner[word]} and {block.id}")
            owner[word] = block.id
    if len(owner) != n_words:
        missing = min(set(range(n_words)) - owner.keys())
        _fail(f"word {missing} is in no block")


def _check_identity(doc: "Document") -> None:
    keys: set[str] = set()
    for index, block in enumerate(doc.blocks, start=1):
        if block.id != f"b{index}":
            _fail(f"block id {block.id} at position {index}, expected b{index}")
        if block.key in keys:
            _fail(f"block key {block.key} is used twice")
        keys.add(block.key)


def _check_keys(doc: "Document") -> None:
    """Keys are derived from content, so they are checked after the content itself (8a)."""
    expected = assign_keys([(block.kind, block.text) for block in doc.blocks])
    for block, key in zip(doc.blocks, expected, strict=True):
        if block.key != key:
            _fail(f"block {block.id} has key {block.key}, but its content key is {key}")


def _check_links(doc: "Document", by_id: dict[str, "Block"]) -> None:
    order = {block.id: index for index, block in enumerate(doc.blocks)}
    for link in doc.links:
        source = by_id.get(link.from_.block)
        if source is None:
            _fail(f"link from {link.from_.block}: no such block")
        if link.from_.cell is not None:
            if source.kind != "table":
                _fail(f"link names a cell, but block {source.id} is not a table")
            anchors = {(c.row, c.col) for c in source.grid.cells}
            if tuple(link.from_.cell) not in anchors:
                _fail(f"link cell {link.from_.cell} is not a cell anchor of table {source.id}")
        target = by_id.get(link.to) if link.to is not None else None
        if link.to is not None and target is None:
            _fail(f"link to {link.to}: no such block")
        if link.kind == "footnote_call":
            if target is not None and target.kind != "footnote":
                _fail(
                    f"a resolved footnote_call must point at a footnote block; "
                    f"{target.id} is a {target.kind}"
                )
        elif target is not None:
            if source.kind != "table" or target.kind != "table":
                _fail("a continuation links two tables")
            if order[target.id] >= order[source.id]:
                _fail("a continuation must point at an earlier table")


def _check_text(doc: "Document", words: Sequence["Word"]) -> None:
    for block in doc.blocks:
        for a, b in block.hyphen_joins:
            if not (words[a].text.endswith("-") and len(words[a].text) > 1):
                _fail(f"hyphen join ({a}, {b}): word {a} does not end in a hyphen")
            if not words[b].text[:1].islower():
                _fail(f"hyphen join ({a}, {b}): word {b} does not start with a lower-case letter")
        firsts = {a for a, _ in block.hyphen_joins}
        texts = [words[w].text for w in block.word_ids]
        if not text_matches_words(block.text, texts, [w in firsts for w in block.word_ids]):
            _fail(
                f"text of block {block.id} does not spell exactly the characters of its words, "
                "in order"
            )
        _check_kind_fields(block, words[block.word_ids[0]].text)


def _check_kind_fields(block: "Block", first: str) -> None:
    """Labels and numbers are the block's own first word, never a guess (invariant 8b)."""
    if block.kind == "list_item" and block.label != first:
        _fail(f"list item {block.id} has label {block.label!r}, but its first word is {first!r}")
    if block.kind == "footnote" and block.label != strip_label(first):
        _fail(f"footnote {block.id} has label {block.label!r}, but its first word is {first!r}")
    if block.kind == "heading" and block.number is not None and block.number != first:
        _fail(f"heading {block.id} has number {block.number!r}, but its first word is {first!r}")


def _check_regions(doc: "Document", words: Sequence["Word"]) -> None:
    for block in doc.blocks:
        regions = {region.page: region for region in block.regions}
        word_pages = {words[w].page for w in block.word_ids}
        for page in regions:
            if page not in word_pages:
                _fail(f"block {block.id} has a region on page {page} holding none of its words")
        for w in block.word_ids:
            region = regions.get(words[w].page)
            if region is None:
                _fail(f"word {w} of block {block.id} has no region on page {words[w].page}")
            if not region.bbox.contains_rect(words[w].bbox):
                _fail(f"word {w} lies outside block {block.id}'s region on page {region.page}")


def _check_cells(table: "Table", words: Sequence["Word"]) -> None:
    joins = table.hyphen_joins
    for cell in table.grid.cells:
        if cell.carried:
            continue
        rect = table.grid.cell_rect(cell)
        for w in cell.word_ids:
            x, y = words[w].bbox.center
            if not rect.contains_point(x, y):
                _fail(f"word {w} lies outside cell ({cell.row}, {cell.col}) of table {table.id}")
        members = set(cell.word_ids)
        firsts = {a for a, b in joins if a in members and b in members}
        texts = [words[w].text for w in cell.word_ids]
        if not text_matches_words(cell.text, texts, [w in firsts for w in cell.word_ids]):
            _fail(
                f"text of cell ({cell.row}, {cell.col}) in table {table.id} does not spell "
                "exactly the characters of its words, in order"
            )


def _check_carried(doc: "Document", by_id: dict[str, "Block"]) -> None:
    parents = {
        link.from_.block: link.to
        for link in doc.links
        if link.kind == "continuation" and link.status == "resolved" and link.to is not None
    }
    for table in doc.tables():
        carried = [cell for cell in table.grid.cells if cell.carried]
        if not carried:
            continue
        parent_id = parents.get(table.id)
        if parent_id is None:
            _fail(f"table {table.id} has carried cells but no resolved continuation link from it")
        parent = by_id[parent_id]
        if parent.kind != "table":
            _fail(f"table {table.id} continues {parent_id}, which is not a table")
        header = {
            (c.row, c.col): c.text for c in parent.grid.cells if c.row < parent.grid.header_rows
        }
        for cell in carried:
            where = f"carried cell ({cell.row}, {cell.col}) of table {table.id}"
            for anchor in cell.source:
                if anchor not in header:
                    _fail(f"{where} names {anchor}, not a header cell of table {parent_id}")
            copied = " ".join(header[anchor] for anchor in cell.source)
            if cell.text != copied:
                _fail(f"{where} reads {cell.text!r}, but its source prints {copied!r}")


def _check_findings(doc: "Document", by_id: dict[str, "Block"]) -> None:
    for finding in doc.findings:
        if finding.page is not None and finding.page > len(doc.pages):
            _fail(f"finding {finding.code} names page {finding.page} of {len(doc.pages)}")
        if finding.block is not None and finding.block not in by_id:
            _fail(f"finding {finding.code} names block {finding.block}, which does not exist")


def _check_ledger(doc: "Document", words: Sequence["Word"]) -> None:
    content = furniture = 0
    for block in doc.blocks:
        chars = sum(len(words[w].text) for w in block.word_ids)
        if block.kind == "furniture":
            furniture += chars
        else:
            content += chars
    expected = {
        "content_chars": content,
        "furniture_chars": furniture,
        "invisible_chars": sum(p.invisible_chars for p in doc.pages),
        "clipped_chars": sum(p.clipped_chars for p in doc.pages),
    }
    for name, want in expected.items():
        got = getattr(doc.ledger, name)
        if got != want:
            _fail(f"ledger {name} is {got}, but the document holds {want}")


def check_document(doc: "Document") -> None:
    """Raise `ValueError` for the first violated cross-object invariant."""
    _check_pages_and_words(doc)
    _check_partition(doc)
    _check_identity(doc)
    by_id = {block.id: block for block in doc.blocks}
    _check_links(doc, by_id)
    words = doc.words
    _check_text(doc, words)
    _check_regions(doc, words)
    for table in doc.tables():
        _check_cells(table, words)
    _check_carried(doc, by_id)
    _check_keys(doc)
    _check_findings(doc, by_id)
    _check_ledger(doc, words)
