"""Glossary entries and note lists (docs/specs/08-notes-and-glossaries.md).

A glossary entry is a term and its body. In prose, the term opens a paragraph: in quotation marks,
in bold, or in a column of its own (a hanging indent). Outside a definitions section only a quoted
term with a defining verb is taken; the other forms need the section as evidence of a glossary.
"""

from collections.abc import Callable, Sequence

from inkgrid.core.lexicon import (
    DEFINING_VERBS,
    DEFINITION_PHRASES,
    DEFINITION_WORDS,
    is_strong_value,
    is_value,
    note_label,
    section_number,
)
from inkgrid.core.lines import Line, fragments
from inkgrid.core.order import heading_level, heading_sizes, reading_order
from inkgrid.core.prose import ProtoBlock
from inkgrid.core.tables.proto import ProtoCell, ProtoTable
from inkgrid.model.config import Profile
from inkgrid.model.invariants import strip_label
from inkgrid.model.page import Word

OPENING = "\u201c\"\u2018'"
CLOSING = "\u201d\"\u2019'"
TRAILING = ".,:;"
ALTERNATES = ("or", "and", "/")
MAX_QUOTED_WORDS = 12  # a quoted phrase closes within this many words, or it is not a term
MAX_PAREN_WORDS = 6  # `(cross-connect)`, `("MEI")`: a parenthetical that belongs to the term
MAX_LEAD_WORDS = 12  # a bold or italic lead-in term
MAX_HANGING_WORDS = 8
HANGING_GAP_EM = 2.0  # the gap between a hanging term and its body, in ems of the line's size
HANGING_X_TOL = 2.0  # pt: how far a later line may start from the body's column
TERM_AND_BODY = 2  # fragments: a hanging term, then the body
MAX_TITLE_WORDS = 8  # a definitions heading, without its section number
TITLE_PUNCTUATION = "():,;."
GLOSSARY_COLUMNS = 2
MAX_TERM_CELL_WORDS = 8
MIN_PROSE_WORDS = 3


def _quoted_run(words: Sequence[Word], start: int) -> int:
    """The index after a quoted phrase opening at `start`, or 0 when none opens and closes there."""
    if start >= len(words) or words[start].text[:1] not in OPENING:
        return 0
    for i in range(start, min(len(words), start + MAX_QUOTED_WORDS)):
        text = words[i].text.rstrip(TRAILING)
        if text.endswith(tuple(CLOSING)) and (i > start or len(text) > 1):
            return i + 1
    return 0


def quoted_term(words: Sequence[Word]) -> int:
    """How many leading words form a quoted term (spec 08 section 2 form 1), or 0.

    The term is a quoted phrase, any alternates (`or "EEM"`), and one short parenthetical. Words
    must follow it: a quoted phrase alone is not a definition.
    """
    end = _quoted_run(words, 0)
    if not end:
        return 0
    while end + 1 < len(words) and words[end].text in ALTERNATES:
        more = _quoted_run(words, end + 1)
        if not more:
            break
        end = more
    if end < len(words) and words[end].text.startswith("("):
        for j in range(end, min(len(words), end + MAX_PAREN_WORDS)):
            if words[j].text.rstrip(TRAILING).endswith(")"):
                end = j + 1
                break
    return end if end < len(words) else 0


def defines(words: Sequence[Word]) -> bool:
    """True when the words open with a defining verb (`means`, `shall mean`, `refers to`, ...)."""
    tokens = [w.text.rstrip(TRAILING).lower() for w in words[:4]]
    return any(tuple(tokens[: len(verb)]) == verb for verb in DEFINING_VERBS)


def lead_term(line: Line) -> int:
    """How many leading words form a term set apart by its type: bold, or italic, words first.

    A word that is not follows them (`Available for Distribution:`, an italic `Distributor.`).
    """

    def run(set_apart: Callable[[Word], bool]) -> int:
        count = 0
        for word in line.words:
            if not set_apart(word):
                break
            count += 1
        return count if 0 < count < len(line.words) and count <= MAX_LEAD_WORDS else 0

    return run(lambda w: w.bold) or run(lambda w: w.italic)


def hanging_term(lines: Sequence[Line], profile: Profile) -> int:
    """How many words of the first line's first fragment are a hanging term, or 0.

    The body starts at least 2 em after the term, and every later line starts at the body's column.
    """
    first = lines[0]
    pieces = fragments(first, profile)
    if len(pieces) < TERM_AND_BODY or len(pieces[0].words) > MAX_HANGING_WORDS:
        return 0
    body_x = pieces[1].x0
    if body_x - pieces[0].x1 < HANGING_GAP_EM * first.size:
        return 0
    if any(abs(line.x0 - body_x) > HANGING_X_TOL for line in lines[1:]):
        return 0
    return len(pieces[0].words)


def _term_length(block: ProtoBlock, *, in_scope: bool, profile: Profile) -> int:
    words = [w for line in block.lines for w in line.words]
    quoted = quoted_term(words)
    if quoted and (in_scope or defines(words[quoted:])):
        return quoted
    if not in_scope:
        return 0
    lead = lead_term(block.lines[0])
    if lead:
        return lead
    hanging = hanging_term(block.lines, profile)
    # A lone note number in the term's column is a note, not a term (`1 | Trade activity ...`).
    if hanging == 1 and note_label(words[0].text) is not None:
        return 0
    return hanging


def as_definition(block: ProtoBlock, *, in_scope: bool, profile: Profile) -> ProtoBlock:
    """The paragraph as a definition when it opens with a term (spec 08 section 2), else unchanged.

    `in_scope` says whether the paragraph lies in a definitions section.
    """
    if block.kind != "paragraph":
        return block
    n = _term_length(block, in_scope=in_scope, profile=profile)
    first = block.lines[0]
    if not n or n > len(first.words):
        return block  # a term wrapping onto a second line is left as prose
    term = Line(first.words[:n])
    rest = (Line(first.words[n:]),) if n < len(first.words) else ()
    return ProtoBlock("definition", (term, *rest, *block.lines[1:]), block.size, term=(term,))


def _text(words: Sequence[Word]) -> str:
    return " ".join(w.text for w in words)


def is_definitions_title(text: str) -> bool:
    """True when a heading's text titles a glossary (spec 08 section 1).

    Its words, without a leading section number, number at most 8, hold a definitions word or
    phrase, and include no dot leader: `Definitions ......... 4` is a contents line.
    """
    words = text.split()
    if words and section_number(words[0]) is not None:
        words = words[1:]
    if not words or len(words) > MAX_TITLE_WORDS or ".." in text:
        return False
    tokens = [w.strip(TITLE_PUNCTUATION).lower() for w in words]
    if any(t in DEFINITION_WORDS for t in tokens):
        return True
    return any(
        tuple(tokens[i : i + len(phrase)]) == phrase
        for phrase in DEFINITION_PHRASES
        for i in range(len(tokens))
    )


def _prose(words: Sequence[Word]) -> bool:
    """At least 3 words, not a value, not opening with one: `$0.25 per contract` is a fee."""
    texts = [w.text for w in words if not w.superscript]
    return (
        len(texts) >= MIN_PROSE_WORDS
        and not is_value(" ".join(texts))
        and not is_strong_value(texts[0])
    )


def _holds_value(words: Sequence[Word]) -> bool:
    return is_value(_text(words)) or any(is_strong_value(w.text) for w in words)


def _banner(cell: ProtoCell, profile: Profile) -> ProtoBlock | None:
    """A full-width cell as a heading, when it holds no more words than a heading may."""
    if len(cell.words) > profile.heading_max_words:
        return None  # a full-width paragraph, not a banner
    lines = cell.lines
    return ProtoBlock(
        "heading", lines, lines[0].size, number=section_number(lines[0].words[0].text)
    )


def _pair(
    left: ProtoCell, right: ProtoCell, *, in_scope: bool, marks: frozenset[str]
) -> ProtoBlock | None:
    """A label or term beside prose as a note or a definition, or None."""
    if not _prose(right.words):
        return None
    lines = (*left.lines, *right.lines)
    label = left.words[0].text
    # A mark that is punctuation alone (`)`, `.`) strips to nothing: no label (8b).
    noted = note_label(label) is not None or label in marks
    if len(left.words) == 1 and strip_label(label) and noted:
        return ProtoBlock("footnote", lines, lines[0].size, label=strip_label(label))
    if in_scope and len(left.words) <= MAX_TERM_CELL_WORDS and not _holds_value(left.words):
        return ProtoBlock("definition", lines, lines[0].size, term=left.lines)
    return None


def _row_block(
    row: Sequence[ProtoCell], *, in_scope: bool, marks: frozenset[str], profile: Profile
) -> ProtoBlock | None:
    """One grid row as a banner heading, a note, or a definition (spec 08 section 3), or None."""
    filled = [c for c in row if c.words]
    if len(filled) == 1 and filled[0].cell.col_span == GLOSSARY_COLUMNS:
        return _banner(filled[0], profile)
    if len(filled) != GLOSSARY_COLUMNS or any(c.cell.col_span != 1 for c in filled):
        return None
    left, right = sorted(filled, key=lambda c: c.cell.col)
    return _pair(left, right, in_scope=in_scope, marks=marks)


def dissolve(
    table: ProtoTable, *, in_scope: bool, marks: frozenset[str], profile: Profile
) -> tuple[ProtoBlock, ...] | None:
    """A note list or glossary grid as blocks, row by row (spec 08 section 3), or None.

    `marks` holds the text of every superscript word of the document: a first cell one of them
    spells is a note's label. A banner in the first row that titles a glossary opens a scope over
    the grid itself.
    """
    n_rows = len(table.shape.row_edges) - 1
    n_cols = len(table.shape.col_edges) - 1
    if n_cols != GLOSSARY_COLUMNS or any(c.cell.row_span != 1 for c in table.cells):
        return None
    rows: list[list[ProtoCell]] = [[] for _ in range(n_rows)]
    for cell in table.cells:
        rows[cell.cell.row].append(cell)
    head = [c for c in rows[0] if c.words]
    if (
        len(head) == 1
        and head[0].cell.col_span == n_cols
        and is_definitions_title(_text(head[0].words))
    ):
        in_scope = True
    blocks: list[ProtoBlock] = []
    for row in rows:
        if not any(c.words for c in row):
            continue  # an empty row owns nothing
        block = _row_block(row, in_scope=in_scope, marks=marks, profile=profile)
        if block is None:
            return None
        blocks.append(block)
    return tuple(blocks) if any(b.kind != "heading" for b in blocks) else None


def glossary(
    pages: Sequence[Sequence[ProtoBlock]],
    tables: Sequence[Sequence[ProtoTable]],
    *,
    marks: frozenset[str],
    profile: Profile,
) -> tuple[list[tuple[ProtoBlock, ...]], list[tuple[ProtoTable, ...]]]:
    """Each page's blocks and tables, glossary entries and note lists typed (spec 08 section 5).

    The pass walks the document in reading order. A definitions heading opens a scope that runs,
    across pages, to the next heading of the same or a higher level; paragraphs inside it are tested
    for terms, and every table for a note list or a glossary grid, whose blocks take its place.
    """
    sizes = heading_sizes(b for blocks in pages for b in blocks)
    scope: int | None = None
    out_pages: list[tuple[ProtoBlock, ...]] = []
    out_tables: list[tuple[ProtoTable, ...]] = []
    for blocks, page_tables in zip(pages, tables, strict=True):
        kept: list[ProtoBlock] = []
        grids: list[ProtoTable] = []
        for item in reading_order(blocks, page_tables):
            if isinstance(item, ProtoTable):
                found = dissolve(item, in_scope=scope is not None, marks=marks, profile=profile)
                if found is None:
                    grids.append(item)
                else:
                    kept.extend(found)
                continue
            if item.kind == "heading":
                level = heading_level(item.size, sizes)
                if scope is not None and level <= scope:
                    scope = None
                if scope is None and is_definitions_title(
                    _text([w for ln in item.lines for w in ln.words])
                ):
                    scope = level
                kept.append(item)
                continue
            kept.append(as_definition(item, in_scope=scope is not None, profile=profile))
        out_pages.append(tuple(kept))
        out_tables.append(tuple(grids))
    return out_pages, out_tables
