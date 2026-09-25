"""Pure Markdown formatting of block text (docs/specs/05-read-and-inspector.md section 2).

This module imports nothing from `document.py`, so `Document.to_markdown()` adds no import cycle:
the document dispatches over its block kinds and calls these formatters.
"""

import re
from collections.abc import Iterable

MAX_HEADING_LEVEL = 6
STRUCTURE_OPENERS = ("#", ">", "-", "+", "*")
ORDINAL = re.compile(r"\d+(?=[.)])")


def heading(level: int, text: str) -> str:
    """`#` x min(level, 6), a space, then the text."""
    return "#" * min(level, MAX_HEADING_LEVEL) + " " + text


def paragraph(text: str) -> str:
    """The text, escaped so Markdown never reads printed text as structure."""
    if text.startswith(STRUCTURE_OPENERS):
        return "\\" + text
    ordinal = ORDINAL.match(text)
    if ordinal is not None:
        return text[: ordinal.end()] + "\\" + text[ordinal.end() :]
    return text


def _after_first_word(text: str) -> str:
    return text.partition(" ")[2]


def list_item(text: str, *, bullet: bool) -> str:
    """A bullet item as `- ` and its text; an enumerated item as printed."""
    if not bullet:
        return text
    rest = _after_first_word(text)
    return f"- {rest}" if rest else "-"


def footnote(label: str, text: str) -> str:
    """`[^label]:`, then the note's text without its printed label."""
    rest = _after_first_word(text)
    return f"[^{label}]: {rest}" if rest else f"[^{label}]:"


def definition(term: str, body: str) -> str:
    """The term in bold, then the body."""
    return f"**{term}** {body}"


def join(parts: Iterable[str]) -> str:
    """Blocks separated by one blank line, ending with one newline; nothing renders as `""`."""
    blocks = list(parts)
    return "\n\n".join(blocks) + "\n" if blocks else ""
