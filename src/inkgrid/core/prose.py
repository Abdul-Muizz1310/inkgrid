"""Prose blocks and their kinds (docs/specs/04-text-pipeline.md section 5).

Stage 4 claims every word it receives. Rows regions follow the same rules: M2's table stage takes
the tables among them first, and what is left, such as hanging-indent lists, is prose.
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from inkgrid.core.layout import Region
from inkgrid.core.lexicon import enumerator, is_bullet, note_label, section_number
from inkgrid.core.lines import Line
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.invariants import strip_label

ProseKind = Literal["heading", "paragraph", "list_item", "footnote"]
SENTENCE_END = (".", ";", ",")
TERMINAL = (".", ":", ";", "?", "!")
MIN_GAPS = (
    4  # fewer gaps than this cannot show a region's leading: use the page's, then the document's
)


@dataclass(frozen=True, slots=True)
class ProtoBlock:
    """A block before assembly: its kind, lines, size (its first line's), and kind fields."""

    kind: ProseKind
    lines: tuple[Line, ...]
    size: float
    label: str | None = None
    number: str | None = None


def _lower_quartile(values: Sequence[float]) -> float:
    ordered = sorted(values)
    return ordered[(len(ordered) - 1) // 4] if ordered else 0.0


def _size_class(line: Line) -> float:
    return round(line.size * 2) / 2


@dataclass(frozen=True, slots=True)
class LineGaps:
    """The typical gap between lines of a paragraph, per type size, over a whole document."""

    by_size: Mapping[float, float]
    default: float

    def of(self, line: Line) -> float:
        """The line gap for text set at this line's size."""
        return self.by_size.get(_size_class(line), self.default)


def line_gaps(regions: Sequence[Region]) -> LineGaps:
    """The lower quartile of the clamped gaps between consecutive lines, per size class.

    MuPDF's line boxes span the font's full ascent and descent, so lines at ordinary leading
    overlap: gaps are clamped at 0, not dropped. On a page of short paragraphs most gaps are the
    breaks themselves, so the lower quartile is taken, not the median. Each type size is set with
    its own leading, so small-type tables do not set the line gap of the body text beside them.
    """
    every: list[float] = []
    per_size: defaultdict[float, list[float]] = defaultdict(list)
    for region in regions:
        for prev, cur in zip(region.lines, region.lines[1:], strict=False):
            gap = max(0.0, cur.top - prev.bottom)
            every.append(gap)
            if _size_class(prev) == _size_class(cur):
                per_size[_size_class(prev)].append(gap)
    by_size = {
        size: _lower_quartile(gaps) for size, gaps in per_size.items() if len(gaps) >= MIN_GAPS
    }
    return LineGaps(MappingProxyType(by_size), _lower_quartile(every))


def _opens_item(line: Line, lexicon: Lexicon) -> bool:
    first = line.words[0].text
    return is_bullet(first, lexicon) or enumerator(first) is not None


def _runs_on(prev: Line, cur: Line) -> bool:
    """The sentence continues: no terminal punctuation, then a lower-case opening."""
    return not prev.words[-1].text.endswith(TERMINAL) and cur.words[0].text[:1].islower()


def _breaks(prev: Line, cur: Line, threshold: float, lexicon: Lexicon, profile: Profile) -> bool:
    return (
        (cur.top - prev.bottom > threshold and not _runs_on(prev, cur))
        or abs(cur.size - prev.size) > profile.size_change_ratio * prev.size
        or cur.bold != prev.bold
        or _opens_item(cur, lexicon)
    )


def _footnote_label(lines: Sequence[Line], profile: Profile, body_size: float) -> str | None:
    first = lines[0].words[0]
    if lines[0].size > profile.footnote_size_ratio * body_size:
        return None
    if note_label(first.text) is None and not first.superscript:
        return None
    return strip_label(first.text) or None


def _is_heading(
    lines: Sequence[Line], lexicon: Lexicon, profile: Profile, body_size: float
) -> bool:
    words = [w for line in lines for w in line.words]
    return (
        len(lines) <= profile.heading_max_lines
        and len(words) <= profile.heading_max_words
        and not is_bullet(words[0].text, lexicon)
        and not words[-1].text.endswith(SENTENCE_END)
        and (
            lines[0].size >= profile.heading_size_ratio * body_size
            or all(line.bold for line in lines)
        )
    )


def _block(
    lines: Sequence[Line], lexicon: Lexicon, profile: Profile, body_size: float
) -> ProtoBlock:
    chunk = tuple(lines)
    size = chunk[0].size
    first = chunk[0].words[0].text
    label = _footnote_label(chunk, profile, body_size)
    if label is not None:
        return ProtoBlock("footnote", chunk, size, label=label)
    if _is_heading(chunk, lexicon, profile, body_size):
        return ProtoBlock("heading", chunk, size, number=section_number(first))
    if _opens_item(chunk[0], lexicon):
        return ProtoBlock("list_item", chunk, size, label=first)
    return ProtoBlock("paragraph", chunk, size)


def page_blocks(
    regions: Sequence[Region],
    lexicon: Lexicon,
    profile: Profile,
    body_size: float,
    gaps: LineGaps,
) -> tuple[ProtoBlock, ...]:
    """Split one page's regions into typed blocks, in reading order; `gaps` is `line_gaps`'s."""
    out: list[ProtoBlock] = []
    for region in regions:
        current: list[Line] = []
        for line in region.lines:
            if current:
                prev = current[-1]
                limit = max(
                    profile.paragraph_gap_ratio * gaps.of(prev), profile.paragraph_gap_floor
                )
                if _breaks(prev, line, limit, lexicon, profile):
                    out.append(_block(current, lexicon, profile, body_size))
                    current = []
            current.append(line)
        if current:
            out.append(_block(current, lexicon, profile, body_size))
    return tuple(out)
