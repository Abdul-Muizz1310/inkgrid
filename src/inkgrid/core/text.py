"""The text rule (design section 8.4, docs/specs/04 section 6).

Exactly two transforms exist: words join with one space, and a line-final hyphenated fragment closes
up with a lower-case continuation, recorded as a hyphen join so a consumer can undo it.
"""

from collections.abc import Sequence

from inkgrid.core.lines import Line
from inkgrid.model.page import Word

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
