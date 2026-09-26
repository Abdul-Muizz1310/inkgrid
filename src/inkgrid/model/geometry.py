"""Quantized geometry: every coordinate is PDF points rounded to 0.01 at construction.

Rectangles use PDF-point page space with the origin at the top-left and y growing downward.
Containment of a point is half-open, so a set of rectangles that tiles an area assigns every point
in it to exactly one rectangle.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


def quantize(value: float) -> float:
    """Round `value` to 0.01 pt, normalizing -0.0 to 0.0.

    Raises:
        ValueError: `value` is NaN or infinite.
    """
    if not math.isfinite(value):
        msg = f"coordinate must be finite, got {value!r}"
        raise ValueError(msg)
    return round(value, 2) + 0.0


def _array_schema(
    cls: type[Rect | Interval],
    size: int,
    dump: Callable[[Rect], list[float]] | Callable[[Interval], list[float]],
) -> CoreSchema:
    items = core_schema.tuple_schema([core_schema.float_schema(allow_inf_nan=False)] * size)
    build = core_schema.no_info_after_validator_function(lambda t: cls(*t), items)
    return core_schema.json_or_python_schema(
        json_schema=build,
        python_schema=core_schema.union_schema([core_schema.is_instance_schema(cls), build]),
        serialization=core_schema.plain_serializer_function_ser_schema(dump),
    )


@dataclass(frozen=True, slots=True)
class Rect:
    """An axis-aligned rectangle `[x0, x1] x [y0, y1]` with `x0 <= x1` and `y0 <= y1`."""

    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self) -> None:
        """Quantize, then reject an inverted rectangle."""
        for name in ("x0", "y0", "x1", "y1"):
            object.__setattr__(self, name, quantize(getattr(self, name)))
        if self.x0 > self.x1 or self.y0 > self.y1:
            msg = f"inverted rectangle ({self.x0}, {self.y0}, {self.x1}, {self.y1})"
            raise ValueError(msg)

    @property
    def width(self) -> float:
        """Horizontal extent."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """Vertical extent."""
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        """Width times height."""
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        """The midpoint, not quantized."""
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)

    def contains_point(self, x: float, y: float) -> bool:
        """Half-open containment: `x0 <= x < x1` and `y0 <= y < y1`."""
        return self.x0 <= x < self.x1 and self.y0 <= y < self.y1

    def contains_rect(self, other: Rect) -> bool:
        """Closed containment of `other` inside this rectangle."""
        return (
            self.x0 <= other.x0
            and self.y0 <= other.y0
            and other.x1 <= self.x1
            and other.y1 <= self.y1
        )

    def intersects(self, other: Rect) -> bool:
        """Overlap with positive area; touching edges do not intersect."""
        return min(self.x1, other.x1) > max(self.x0, other.x0) and min(self.y1, other.y1) > max(
            self.y0, other.y0
        )

    def union(self, other: Rect) -> Rect:
        """The smallest rectangle containing both."""
        return Rect(
            min(self.x0, other.x0),
            min(self.y0, other.y0),
            max(self.x1, other.x1),
            max(self.y1, other.y1),
        )

    @classmethod
    def union_all(cls, rects: Iterable[Rect]) -> Rect:
        """The smallest rectangle containing every rectangle in `rects`.

        Raises:
            ValueError: `rects` is empty.
        """
        items = list(rects)
        if not items:
            msg = "union_all of an empty collection"
            raise ValueError(msg)
        return Rect(
            min(r.x0 for r in items),
            min(r.y0 for r in items),
            max(r.x1 for r in items),
            max(r.y1 for r in items),
        )

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: object, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        """Validate from `[x0, y0, x1, y1]` (or an instance); serialize to that array."""
        return _array_schema(cls, 4, lambda r: [r.x0, r.y0, r.x1, r.y1])


@dataclass(frozen=True, slots=True)
class Interval:
    """A half-open band `[start, end)` of positive width."""

    start: float
    end: float

    def __post_init__(self) -> None:
        """Quantize, then reject an empty or inverted band."""
        object.__setattr__(self, "start", quantize(self.start))
        object.__setattr__(self, "end", quantize(self.end))
        if self.start >= self.end:
            msg = f"band must have positive width, got [{self.start}, {self.end})"
            raise ValueError(msg)

    @property
    def width(self) -> float:
        """`end - start`."""
        return self.end - self.start

    def contains(self, value: float) -> bool:
        """Half-open containment: `start <= value < end`."""
        return self.start <= value < self.end

    def overlaps(self, other: Interval) -> bool:
        """True when the two bands share a positive length."""
        return min(self.end, other.end) > max(self.start, other.start)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: object, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        """Validate from `[start, end]` (or an instance); serialize to that array."""
        return _array_schema(cls, 2, lambda i: [i.start, i.end])


Rotation = Literal[0, 90, 180, 270]


def turn_point(
    x: float, y: float, rotation: Rotation, width: float, height: float
) -> tuple[float, float]:
    """A point of the unrotated page (`width` x `height`), as a page turned by `rotation` shows it.

    The mapping is PyMuPDF's `rotation_matrix`, measured: 90 gives (h - y, x), 180 gives
    (w - x, h - y), and 270 gives (y, w - x).
    """
    match rotation:
        case 0:
            return x, y
        case 90:
            return height - y, x
        case 180:
            return width - x, height - y
        case 270:
            return y, width - x


def turn_rect(rect: Rect, rotation: Rotation, width: float, height: float) -> Rect:
    """A rectangle of the unrotated page, as the turned page shows it."""
    x0, y0 = turn_point(rect.x0, rect.y0, rotation, width, height)
    x1, y1 = turn_point(rect.x1, rect.y1, rotation, width, height)
    return Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
