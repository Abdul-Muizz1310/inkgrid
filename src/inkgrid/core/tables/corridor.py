"""Unruled tables from whitespace corridors (docs/specs/07-unruled-tables.md).

Columns come from the whitespace between the value rows' pieces, which stays put however a column is
aligned; every row votes on where each boundary sits; and two values never share a cell (L2, L11).
"""

from collections.abc import Sequence

from inkgrid.core.lexicon import is_strong_value, is_value
from inkgrid.model.page import Word

MAX_QUALIFIED_TOKENS = 4  # `$5,000 per month`: a value and a few words qualifying it


def _tokens(words: Sequence[Word]) -> list[str]:
    """The piece's tokens without its note marks (superscript words)."""
    return [w.text for w in words if not w.superscript]


def is_value_piece(words: Sequence[Word]) -> bool:
    """True for a piece that holds a value cell: it is a strong value, or opens with one."""
    tokens = _tokens(words)
    if not tokens:
        return False
    if is_value(" ".join(tokens)) and any(is_strong_value(t) for t in tokens):
        return True
    return len(tokens) <= MAX_QUALIFIED_TOKENS and is_strong_value(tokens[0])


def is_value_like(words: Sequence[Word]) -> bool:
    """True for a piece that reads as a value at all, weak values included (`62`, `1 - 150`)."""
    tokens = _tokens(words)
    return bool(tokens) and is_value(" ".join(tokens))
