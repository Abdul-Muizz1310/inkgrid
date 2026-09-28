"""The verifier's page model: what PDFium reads, before any comparison (spec 10 section 1).

Every box is in the page's frame: the unrotated page box, y growing down, as a `Document`'s boxes
are.
"""

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from inkgrid.model.geometry import Rect

CharKind = Literal["ink", "hyphen", "unmapped", "space", "generated", "invisible"]
Axis = Literal["h", "v"]
Point = tuple[float, float]

INK_KINDS = frozenset({"ink", "hyphen", "unmapped"})
INVISIBLE_CATEGORIES = frozenset({"Cc", "Cf", "Co", "Cn"})
LINE_END_HYPHEN = 0x02  # PDFium's code point for a hyphen that ends a line
REPLACEMENT = "\ufffd"
UNICODE_END = 0x110000
POLYGON_MIN = 3  # points a polygon needs to enclose anything


def char_kind(code: int, *, generated: bool, hyphen: bool, map_error: bool) -> tuple[CharKind, str]:
    """A PDFium character's kind and text, decided in the order of spec 10 section 1.1."""
    if code >= UNICODE_END:
        return "unmapped", REPLACEMENT
    char = chr(code)
    category = unicodedata.category(char)
    rules: tuple[tuple[CharKind, bool], ...] = (
        ("generated", generated),
        ("hyphen", hyphen or code == LINE_END_HYPHEN),
        ("space", char.isspace()),
        ("invisible", category in INVISIBLE_CATEGORIES),
        ("unmapped", char == REPLACEMENT or category == "Cs" or map_error),
    )
    kind: CharKind = next((k for k, holds in rules if holds), "ink")
    return kind, "-" if kind == "hyphen" else char


@dataclass(frozen=True, slots=True)
class InkChar:
    """One PDFium character: its index, text, loose box, kind, and whether a clip path hides it."""

    index: int
    char: str
    box: Rect
    kind: CharKind
    clipped: bool = False

    @property
    def is_ink(self) -> bool:
        """True for a character a word could hold."""
        return self.kind in INK_KINDS

    @property
    def center(self) -> Point:
        """The loose box's centre, the point every containment test uses."""
        return self.box.center


@dataclass(frozen=True, slots=True)
class InkRule:
    """A drawn rule as the verifier reads it: axis, position across it, and extent along it."""

    axis: Axis
    at: float
    start: float
    end: float


@dataclass(frozen=True, slots=True)
class InkPage:
    """One page as PDFium reads it, or the error that kept it from loading."""

    number: int
    width: float
    height: float
    chars: tuple[InkChar, ...] = ()
    rules: tuple[InkRule, ...] = ()
    error: str | None = None

    def __post_init__(self) -> None:
        if self.error is not None and (self.chars or self.rules):
            msg = f"page {self.number} failed to load ({self.error}), so it holds no error-free ink"
            raise ValueError(msg)

    def outside(self, ch: InkChar) -> bool:
        """True when the character's centre lies outside the frame (half-open)."""
        x, y = ch.center
        return not (0 <= x < self.width and 0 <= y < self.height)


@dataclass(frozen=True, slots=True)
class Ink:
    """A whole PDF as PDFium reads it, with the versions that read it.

    `error` is set, and `pages` empty, when PDFium could not open the file at all.
    """

    pages: tuple[InkPage, ...]
    pypdfium2: str
    pdfium: str
    error: str | None = None


def in_polygon(points: Sequence[Point], x: float, y: float) -> bool:
    """The even-odd test: True when (x, y) lies inside the polygon through `points`.

    An edge's crossing counts from its lower end up to, not including, its upper end, so of two
    opposite edges exactly one contains a point on them.
    """
    if len(points) < POLYGON_MIN:
        return False
    inside = False
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside
