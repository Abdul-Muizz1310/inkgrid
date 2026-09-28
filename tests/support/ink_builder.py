"""Build the verifier's ink for tests below the PDF: ink that matches words, then broken on purpose.

`ink_of` lays each word's characters evenly across its box, in word-id order, with a generated
space after each word, so a test starts from ink the words own exactly and changes one thing.
"""

from collections.abc import Callable, Iterable, Sequence

from inkgrid.model.document import Document
from inkgrid.model.geometry import Rect
from inkgrid.model.page import Word
from inkgrid.verify.ink import CharKind, InkChar, InkPage

REPLACEMENT = "\ufffd"
CHAR_WIDTH = 5.0
CHAR_HEIGHT = 10.0


def word_chars(word: Word) -> list[InkChar]:
    """The word's characters laid evenly across its box (index 0; `page` renumbers)."""
    n = len(word.text)
    step = word.bbox.width / n
    box = word.bbox
    return [
        InkChar(
            0,
            ch,
            Rect(box.x0 + i * step, box.y0, box.x0 + (i + 1) * step, box.y1),
            "unmapped" if ch == REPLACEMENT else "ink",
        )
        for i, ch in enumerate(word.text)
    ]


def space_after(word: Word) -> InkChar:
    box = word.bbox
    return InkChar(0, " ", Rect(box.x1, box.y0, box.x1, box.y1), "generated")


def page(
    chars: Iterable[InkChar], *, number: int = 1, width: float = 612.0, height: float = 792.0
) -> InkPage:
    """An ink page holding `chars`, renumbered in order."""
    return InkPage(
        number,
        width,
        height,
        chars=tuple(InkChar(i, c.char, c.box, c.kind, c.clipped) for i, c in enumerate(chars)),
    )


def ink_words(words: Sequence[Word], *, number: int = 1) -> InkPage:
    """Ink that the words own exactly."""
    chars: list[InkChar] = []
    for word in sorted(words, key=lambda w: w.id):
        chars += [*word_chars(word), space_after(word)]
    return page(chars, number=number)


def ink_of(doc: Document, number: int = 1) -> InkPage:
    """Ink that the document's words on page `number` own exactly, in its page's frame."""
    info = doc.pages[number - 1]
    words = [w for w in doc.words if w.page == number]
    chars = ink_words(words, number=number).chars
    return page(chars, number=number, width=info.width, height=info.height)


def stray(
    text: str, x: float, y: float, *, kind: CharKind = "ink", clipped: bool = False
) -> list[InkChar]:
    """Characters `CHAR_WIDTH` wide from (x, y), as no word may hold them."""
    return [
        InkChar(
            0,
            ch,
            Rect(x + i * CHAR_WIDTH, y, x + (i + 1) * CHAR_WIDTH, y + CHAR_HEIGHT),
            kind,
            clipped,
        )
        for i, ch in enumerate(text)
    ]


def edited(ink: InkPage, change: Callable[[list[InkChar]], list[InkChar]]) -> InkPage:
    """The page with its characters passed through `change`, then renumbered."""
    return page(change(list(ink.chars)), number=ink.number, width=ink.width, height=ink.height)


def moved(ch: InkChar, dx: float, dy: float = 0.0) -> InkChar:
    b = ch.box
    return InkChar(
        ch.index, ch.char, Rect(b.x0 + dx, b.y0 + dy, b.x1 + dx, b.y1 + dy), ch.kind, ch.clipped
    )
