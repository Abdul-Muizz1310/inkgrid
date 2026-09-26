"""Glossary entries and note lists (docs/specs/08-notes-and-glossaries.md).

A glossary entry is a term and its body. In prose, the term opens a paragraph: in quotation marks,
in bold, or in a column of its own (a hanging indent). Outside a definitions section only a quoted
term with a defining verb is taken; the other forms need the section as evidence of a glossary.
"""

from collections.abc import Sequence

from inkgrid.core.lexicon import DEFINING_VERBS, note_label
from inkgrid.core.lines import Line, fragments
from inkgrid.core.prose import ProtoBlock
from inkgrid.model.config import Profile
from inkgrid.model.page import Word

OPENING = "\u201c\"\u2018'"
CLOSING = "\u201d\"\u2019'"
TRAILING = ".,:;"
ALTERNATES = ("or", "and", "/")
MAX_QUOTED_WORDS = 12  # a quoted phrase closes within this many words, or it is not a term
MAX_PAREN_WORDS = 6  # `(cross-connect)`, `("MEI")`: a parenthetical that belongs to the term
MAX_BOLD_WORDS = 12
MAX_HANGING_WORDS = 8
HANGING_GAP_EM = 2.0  # the gap between a hanging term and its body, in ems of the line's size
HANGING_X_TOL = 2.0  # pt: how far a later line may start from the body's column
TERM_AND_BODY = 2  # fragments: a hanging term, then the body


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


def bold_term(line: Line) -> int:
    """How many leading bold words form a term: some bold words, then a word that is not bold."""
    count = 0
    for word in line.words:
        if not word.bold:
            break
        count += 1
    return count if 0 < count < len(line.words) and count <= MAX_BOLD_WORDS else 0


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
    bold = bold_term(block.lines[0])
    if bold:
        return bold
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
