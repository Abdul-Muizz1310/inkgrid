"""Notes printed in forms M1 does not type (docs/specs/09-notes-calls-and-continuation.md s. 1).

A note opens with its label: set smaller than its text (LSE's 6 pt `14` over 8 pt prose), or at the
text's size when a bare number or mark (MIAX's `^`, Cboe Europe's endnotes). Either way, a note
exists to be called: an opener no superscript of the document calls is a numbered paragraph (SIX's
clause numbers). Cboe prints its notes as ruled tables titled `Footnotes`.
"""

import statistics
from collections.abc import Iterable, Sequence

from inkgrid.core.lexicon import (
    NOTES_WORDS,
    call_parts,
    is_mark,
    is_value,
    note_label,
    section_number,
)
from inkgrid.core.order import reading_order
from inkgrid.core.prose import ProtoBlock
from inkgrid.core.tables.proto import ProtoCell, ProtoTable
from inkgrid.model.invariants import strip_label
from inkgrid.model.page import Word

SMALLER = 0.92  # a label at most this share of its text's size is set apart by size
NO_LARGER = 1.05  # a bare label or mark may match its text's size, give or take this
MIN_NOTE_WORDS = 3  # words after the label on its first line
MIN_NOTE_ROWS = 2
LABEL_AND_TEXT = 2  # filled cells in a note row
ENUMERATOR_ENDS = (".", ")")


def call_labels(words: Iterable[Word]) -> frozenset[str]:
    """Every label some superscript word calls (spec 09 section 2.1)."""
    return frozenset(label for w in words if w.superscript for label in call_parts(w.text))


def _bare(text: str) -> bool:
    """A bare number or a mark: a label that may match its text's size (not `1.`, `a)`, or `a`)."""
    return is_mark(text) or (note_label(text) is not None and not text.endswith(ENUMERATOR_ENDS))


def _label_ok(text: str) -> bool:
    return note_label(text) is not None or is_mark(text) or (len(text) == 1 and text.isalpha())


def as_note(block: ProtoBlock, *, called: frozenset[str], body: float) -> ProtoBlock:
    """The paragraph or list item as a footnote when a called label opens it (s. 1.1)."""
    if block.kind not in ("paragraph", "list_item"):
        return block
    first_line = block.lines[0]
    label, rest = first_line.words[0], first_line.words[1:]
    key = strip_label(label.text)
    if label.superscript or not key or key not in called or not _label_ok(label.text):
        return block
    if len(rest) < MIN_NOTE_WORDS:
        return block
    text_size = statistics.median(w.size for w in rest)
    smaller = label.size <= SMALLER * text_size
    if not (smaller or (_bare(label.text) and label.size <= NO_LARGER * text_size)):
        return block
    if text_size > NO_LARGER * body or 2 * sum(1 for w in rest if w.bold) > len(rest):
        return block  # a heading's number: large and bold
    return ProtoBlock("footnote", block.lines, block.size, label=key)


def _text(cells: Sequence[ProtoCell]) -> str:
    return " ".join(w.text for c in cells for w in c.words)


def note_grid(table: ProtoTable) -> tuple[ProtoBlock, ...] | None:
    """A table titled with a notes word, of label and text rows, as headings and notes (s. 1.2)."""
    n_rows = len(table.shape.row_edges) - 1
    rows: list[list[ProtoCell]] = [[] for _ in range(n_rows)]
    for cell in table.cells:
        if cell.words:
            rows[cell.cell.row].append(cell)
    head = [c for r in rows[: table.header_rows] for c in r]
    words = {w.strip(":").lower() for w in _text(head).split()}
    if not head or not words & NOTES_WORDS or is_value(_text(head)):
        return None
    body = [r for r in rows[table.header_rows :] if r]
    if len(body) < MIN_NOTE_ROWS:
        return None
    blocks: list[ProtoBlock] = []
    for row in rows[: table.header_rows]:
        if row:
            lines = tuple(line for c in sorted(row, key=lambda c: c.cell.col) for line in c.lines)
            first = lines[0].words[0].text
            blocks.append(ProtoBlock("heading", lines, lines[0].size, number=section_number(first)))
    for row in body:
        pair = sorted(row, key=lambda c: c.cell.col) if len(row) == LABEL_AND_TEXT else None
        label, text = pair if pair is not None else (None, None)
        if label is None or text is None or label.cell.col != 0 or text.cell.col != 1:
            return None
        if len(label.words) != 1 or note_label(label.words[0].text) is None:
            return None
        if is_value(_text([text])) or not strip_label(label.words[0].text):
            return None
        lines = (*label.lines, *text.lines)
        blocks.append(
            ProtoBlock("footnote", lines, lines[0].size, label=strip_label(label.words[0].text))
        )
    return tuple(blocks)


def notes(
    pages: Sequence[Sequence[ProtoBlock]],
    tables: Sequence[Sequence[ProtoTable]],
    *,
    called: frozenset[str],
    body: float,
) -> tuple[list[tuple[ProtoBlock, ...]], list[tuple[ProtoTable, ...]]]:
    """Each page's blocks and tables with note openers and titled note grids typed (s. 1)."""
    out_pages: list[tuple[ProtoBlock, ...]] = []
    out_tables: list[tuple[ProtoTable, ...]] = []
    for blocks, page_tables in zip(pages, tables, strict=True):
        kept: list[ProtoBlock] = []
        grids: list[ProtoTable] = []
        for item in reading_order(blocks, page_tables):
            if isinstance(item, ProtoTable):
                found = note_grid(item)
                if found is None:
                    grids.append(item)
                else:
                    kept.extend(found)
            else:
                kept.append(as_note(item, called=called, body=body))
        out_pages.append(tuple(kept))
        out_tables.append(tuple(grids))
    return out_pages, out_tables
