"""Place words on a page by position, for the core's unit tests.

A word is `0.5 * size` points wide per character and `size` points high, with `y` its top.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from inkgrid.model.geometry import Rect
from inkgrid.model.page import Word

CHAR_EM = 0.5


@dataclass(frozen=True)
class P:
    """A word to place: its text, top-left corner, size, and flags."""

    text: str
    x: float
    y: float
    size: float = 10.0
    bold: bool = False
    superscript: bool = False
    horizontal: bool = True
    hidden: bool = False

    @property
    def width(self) -> float:
        return CHAR_EM * self.size * len(self.text)


def place(ps: Sequence[P], *, page: int = 1, first_id: int = 0) -> tuple[Word, ...]:
    """Words for the placements, with ids from `first_id` in the given order."""
    return tuple(
        Word(
            id=first_id + i,
            page=page,
            bbox=Rect(p.x, p.y, p.x + p.width, p.y + p.size),
            text=p.text,
            size=p.size,
            font="Helvetica-Bold" if p.bold else "Helvetica",
            bold=p.bold,
            italic=False,
            superscript=p.superscript,
            hidden=p.hidden,
            horizontal=p.horizontal,
        )
        for i, p in enumerate(ps)
    )


def text_line(
    texts: Sequence[str],
    *,
    x: float,
    y: float,
    size: float = 10.0,
    bold: bool = False,
    gap_em: float = 0.3,
) -> list[P]:
    """Words laid out left to right on one line, `gap_em` apart."""
    out = []
    for text in texts:
        p = P(text, x, y, size, bold)
        out.append(p)
        x += p.width + gap_em * size
    return out
