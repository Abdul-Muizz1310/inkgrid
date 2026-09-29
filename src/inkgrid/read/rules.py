"""Extract drawn rules from vector paths (pure). Rules R1-R4 of `docs/specs/02-reader.md` section 5.

The thresholds are fixed and documented, not configurable. The verifier reads rules with different
thresholds on purpose, so agreement between the two is evidence rather than restatement.
"""

from collections.abc import Sequence
from typing import Literal, assert_never

from inkgrid.model.geometry import Rect, quantize
from inkgrid.model.page import Rule
from inkgrid.read.raw import Box, CurveItem, LineItem, Point, QuadItem, RawPath, RectItem

SLANT_MAX = 0.5
MIN_LENGTH = 2.0
# A fill this thin is a rule: the thickest word-free fill measured is 3.24 pt, the thinnest fill
# holding a word 4.08 pt (spec 14 section 1; the verifier keeps 3.0 on purpose).
THIN_MAX = 3.5
QUAD_AXIS_TOL = 0.5

type Axis = Literal["h", "v"]
type RuleKey = tuple[Axis, float, float, float]


def _stroke_visible(path: RawPath) -> bool:
    opacity = 1.0 if path.stroke_opacity is None else path.stroke_opacity
    return "s" in path.kind and path.color is not None and opacity > 0


def _fill_visible(path: RawPath) -> bool:
    opacity = 1.0 if path.fill_opacity is None else path.fill_opacity
    return "f" in path.kind and path.fill is not None and opacity > 0


def _axis_box(corners: tuple[Point, Point, Point, Point]) -> Box | None:
    """The rectangle a quad spans, when its corners sit on two x and two y values."""
    xs = [x for x, _ in corners]
    ys = [y for _, y in corners]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    for x, y in corners:
        on_x = abs(x - x0) <= QUAD_AXIS_TOL or abs(x - x1) <= QUAD_AXIS_TOL
        on_y = abs(y - y0) <= QUAD_AXIS_TOL or abs(y - y1) <= QUAD_AXIS_TOL
        if not (on_x and on_y):
            return None
    return (x0, y0, x1, y1)


class _Collector:
    """Rules keyed by `(axis, at, start, end)`; a duplicate keeps the greatest thickness."""

    def __init__(self) -> None:
        self.found: dict[RuleKey, float] = {}

    def emit(self, axis: Axis, at: float, start: float, end: float, thickness: float) -> None:
        key: RuleKey = (axis, quantize(at), quantize(start), quantize(end))
        if key[2] >= key[3]:
            return
        self.found[key] = max(self.found.get(key, 0.0), quantize(thickness))

    def line(self, item: LineItem, width: float) -> None:
        (px, py), (qx, qy) = item.p, item.q
        dx, dy = abs(qx - px), abs(qy - py)
        if dy <= SLANT_MAX and dx >= MIN_LENGTH:
            self.emit("h", (py + qy) / 2, min(px, qx), max(px, qx), width)
        elif dx <= SLANT_MAX and dy >= MIN_LENGTH:
            self.emit("v", (px + qx) / 2, min(py, qy), max(py, qy), width)

    def rect(self, box: Box, width: float, *, stroke: bool) -> None:
        x0, x1 = sorted((box[0], box[2]))
        y0, y1 = sorted((box[1], box[3]))
        w, h = x1 - x0, y1 - y0
        thin, long = min(w, h), max(w, h)
        if thin <= THIN_MAX and long >= MIN_LENGTH:
            thickness = thin + (width if stroke else 0.0)
            if w >= h:
                self.emit("h", (y0 + y1) / 2, x0, x1, thickness)
            else:
                self.emit("v", (x0 + x1) / 2, y0, y1, thickness)
        elif stroke and w >= MIN_LENGTH and h >= MIN_LENGTH:
            self.emit("h", y0, x0, x1, width)
            self.emit("h", y1, x0, x1, width)
            self.emit("v", x0, y0, y1, width)
            self.emit("v", x1, y0, y1, width)


def extract_fills(paths: Sequence[RawPath]) -> tuple[Rect, ...]:
    """The visible filled rectangles thicker than a rule on both sides, sorted (spec 14 s. 6)."""
    out: set[Rect] = set()
    for path in paths:
        if not _fill_visible(path):
            continue
        for item in path.items:
            match item:
                case RectItem():
                    box: Box | None = item.rect
                case QuadItem():
                    box = _axis_box(item.corners)
                case _:
                    box = None
            if box is None:
                continue
            x0, x1 = sorted((box[0], box[2]))
            y0, y1 = sorted((box[1], box[3]))
            if x1 - x0 > THIN_MAX and y1 - y0 > THIN_MAX:
                out.add(Rect(quantize(x0), quantize(y0), quantize(x1), quantize(y1)))
    return tuple(sorted(out, key=lambda r: (r.y0, r.x0, r.y1, r.x1)))


def extract_rules(paths: Sequence[RawPath], page: int) -> tuple[Rule, ...]:
    """The rules a page's paths draw, de-duplicated and sorted by `(axis, at, start, end)`."""
    out = _Collector()
    for path in paths:
        stroke, fill = _stroke_visible(path), _fill_visible(path)
        if not (stroke or fill):
            continue
        width = path.width or 0.0
        for item in path.items:
            match item:
                case LineItem():
                    if stroke:
                        out.line(item, width)
                case RectItem():
                    out.rect(item.rect, width, stroke=stroke)
                case QuadItem():
                    box = _axis_box(item.corners)
                    if box is not None:
                        out.rect(box, width, stroke=stroke)
                case CurveItem():
                    pass
                case _:
                    assert_never(item)
    return tuple(
        Rule(page=page, axis=axis, at=at, start=start, end=end, thickness=thickness)
        for (axis, at, start, end), thickness in sorted(out.found.items())
    )
