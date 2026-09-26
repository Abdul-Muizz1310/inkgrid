"""Pure Markdown formatting of block text (docs/specs/05-read-and-inspector.md section 2).

This module imports nothing from `document.py`, so `Document.to_markdown()` adds no import cycle:
the document dispatches over its block kinds and calls these formatters.
"""

import re
from collections.abc import Iterable

MAX_HEADING_LEVEL = 6
STRUCTURE_OPENERS = ("#", ">", "-", "+", "*")
ORDINAL = re.compile(r"\d+(?=[.)])")
TAG_OPEN = re.compile(r"<(?=[A-Za-z/!?])")


def _tags(text: str) -> str:
    """A `<` that would open an HTML tag, escaped: printed text never becomes markup."""
    return TAG_OPEN.sub(r"\\<", text)


def _opening(text: str) -> str:
    """The text with a leading block marker escaped, so it is not read as structure."""
    if text.startswith(STRUCTURE_OPENERS):
        return "\\" + text
    ordinal = ORDINAL.match(text)
    if ordinal is not None:
        return text[: ordinal.end()] + "\\" + text[ordinal.end() :]
    return text


def heading(level: int, text: str) -> str:
    """`#` x min(level, 6), a space, then the text."""
    return "#" * min(level, MAX_HEADING_LEVEL) + " " + _tags(text)


def paragraph(text: str) -> str:
    """The text, escaped so Markdown never reads printed text as structure."""
    return _opening(_tags(text))


def _after_first_word(text: str) -> str:
    return text.partition(" ")[2]


def list_item(text: str, *, bullet: bool) -> str:
    """A bullet item as `- ` and its text; an enumerated item as printed."""
    if not bullet:
        return _tags(text)
    rest = _opening(_tags(_after_first_word(text)))
    return f"- {rest}" if rest else "-"


def footnote(label: str, text: str) -> str:
    """`[^label]:`, then the note's text without its printed label."""
    rest = _opening(_tags(_after_first_word(text)))
    return f"[^{label}]: {rest}" if rest else f"[^{label}]:"


def definition(term: str, body: str) -> str:
    """The term in bold, then the body."""
    return f"**{_tags(term)}** {_tags(body)}"


def table(text: str) -> str:
    """A table's text, one line per row, with tag openings escaped (grids arrive in M2)."""
    return _tags(text)


def join(parts: Iterable[str]) -> str:
    """Blocks separated by one blank line, ending with one newline; nothing renders as `""`."""
    blocks = list(parts)
    return "\n\n".join(blocks) + "\n" if blocks else ""
