"""Typed raw values at the PyMuPDF boundary: what `rawdict` and `get_drawings` say, as dataclasses.

`pymupdf_reader` converts library dicts into these once; nothing past that point sees a dict.
Coordinates here are unquantized floats, so unions happen before rounding.
"""

from dataclasses import dataclass

Box = tuple[float, float, float, float]
"""`(x0, y0, x1, y1)` in PDF points, unrotated page, origin top-left, y down."""


@dataclass(frozen=True, slots=True)
class RawChar:
    """One character as MuPDF reports it: its codepoint(s) and glyph box."""

    c: str
    bbox: Box


@dataclass(frozen=True, slots=True)
class RawSpan:
    """A run of characters sharing font, size and flags. `alpha` is the fill opacity, 0-255."""

    font: str
    size: float
    flags: int
    char_flags: int
    alpha: int
    chars: tuple[RawChar, ...]


@dataclass(frozen=True, slots=True)
class RawLine:
    """One text line: its writing direction and spans."""

    direction: tuple[float, float]
    spans: tuple[RawSpan, ...]


Point = tuple[float, float]


@dataclass(frozen=True, slots=True)
class LineItem:
    """A straight segment from `p` to `q`."""

    p: Point
    q: Point


@dataclass(frozen=True, slots=True)
class RectItem:
    """An axis-aligned rectangle item (`re`)."""

    rect: Box


@dataclass(frozen=True, slots=True)
class QuadItem:
    """A quadrilateral item (`qu`); PyMuPDF returns closed four-segment paths this way."""

    corners: tuple[Point, Point, Point, Point]


@dataclass(frozen=True, slots=True)
class CurveItem:
    """A Bezier curve item (`c`). Never a rule; its presence marks drawn content."""


type PathItem = LineItem | RectItem | QuadItem | CurveItem


@dataclass(frozen=True, slots=True)
class RawPath:
    """One drawing path: how it is painted, and its items."""

    kind: str
    width: float | None
    color: tuple[float, ...] | None
    stroke_opacity: float | None
    fill: tuple[float, ...] | None
    fill_opacity: float | None
    items: tuple[PathItem, ...]
