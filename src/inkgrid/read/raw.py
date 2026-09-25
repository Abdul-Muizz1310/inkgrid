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
    """A run of characters sharing font, size and flags."""

    font: str
    size: float
    flags: int
    char_flags: int
    chars: tuple[RawChar, ...]


@dataclass(frozen=True, slots=True)
class RawLine:
    """One text line: its writing direction and spans."""

    direction: tuple[float, float]
    spans: tuple[RawSpan, ...]
