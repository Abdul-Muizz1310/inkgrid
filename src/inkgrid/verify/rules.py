"""Drawn rules from path geometry, with the verifier's own thresholds (spec 10 section 1.4).

The reader's thresholds (`read/rules.py`) are 0.5, 2.0 and 2.5; these differ on purpose, so the two
engines agreeing on a rule is evidence rather than restatement.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import pairwise

from inkgrid.verify.ink import Axis, InkRule, Point

SLANT_MAX = 1.0
MIN_LENGTH = 3.0
THIN_MAX = 3.0
MERGE_AT = 0.5
MERGE_GAP = 1.0
FILL_MIN_POINTS = 4  # a filled subpath needs four corners to be a thin box
AXES: tuple[Axis, Axis] = ("h", "v")


@dataclass(frozen=True, slots=True)
class InkSubpath:
    """One subpath's points in the frame; `None` stands where a Bezier segment breaks the run."""

    points: tuple[Point | None, ...]
    closed: bool


@dataclass(frozen=True, slots=True)
class InkPath:
    """A path object in the frame: whether it visibly strokes or fills, and its subpaths."""

    stroke: bool
    fill: bool
    subpaths: tuple[InkSubpath, ...]


def _segment(p: Point, q: Point) -> InkRule | None:
    dx, dy = abs(q[0] - p[0]), abs(q[1] - p[1])
    if dy <= SLANT_MAX and dx >= MIN_LENGTH:
        return InkRule("h", (p[1] + q[1]) / 2, min(p[0], q[0]), max(p[0], q[0]))
    if dx <= SLANT_MAX and dy >= MIN_LENGTH:
        return InkRule("v", (p[0] + q[0]) / 2, min(p[1], q[1]), max(p[1], q[1]))
    return None


def _stroked(sub: InkSubpath) -> Iterable[InkRule]:
    points = list(sub.points)
    if sub.closed and points and points[0] is not None:
        points.append(points[0])
    for p, q in pairwise(points):
        if p is not None and q is not None and (rule := _segment(p, q)) is not None:
            yield rule


def _filled(sub: InkSubpath) -> InkRule | None:
    points = [p for p in sub.points if p is not None]
    if len(points) < FILL_MIN_POINTS:
        return None
    xs, ys = [x for x, _ in points], [y for _, y in points]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    width, height = x1 - x0, y1 - y0
    if min(width, height) > THIN_MAX or max(width, height) < MIN_LENGTH:
        return None  # shading, or a speck
    if width >= height:
        return InkRule("h", (y0 + y1) / 2, x0, x1)
    return InkRule("v", (x0 + x1) / 2, y0, y1)


def extract_rules(paths: Iterable[InkPath]) -> tuple[InkRule, ...]:
    """The rules the paths draw, merged, sorted by axis, position, and start."""
    found: list[InkRule] = []
    for path in paths:
        for sub in path.subpaths:
            if path.stroke:
                found.extend(_stroked(sub))
            if path.fill and (rule := _filled(sub)) is not None:
                found.append(rule)
    return merge_rules(found)


def _merge_group(axis: Axis, group: Sequence[InkRule]) -> list[InkRule]:
    spans = sorted((r.start, r.end) for r in group)
    merged = [spans[0]]
    for start, end in spans[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + MERGE_GAP:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return [InkRule(axis, group[0].at, start, end) for start, end in merged]


def merge_rules(rules: Iterable[InkRule]) -> tuple[InkRule, ...]:
    """Collinear rules (`at` within MERGE_AT of their group's first) joined across small gaps."""
    given = list(rules)
    out: list[InkRule] = []
    for axis in AXES:
        group: list[InkRule] = []
        for rule in sorted((r for r in given if r.axis == axis), key=lambda r: (r.at, r.start)):
            if group and rule.at - group[0].at > MERGE_AT:
                out.extend(_merge_group(axis, group))
                group = []
            group.append(rule)
        if group:
            out.extend(_merge_group(axis, group))
    return tuple(sorted(out, key=lambda r: (r.axis, r.at, r.start)))
