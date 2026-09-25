"""Prose blocks and their kinds (docs/specs/04-text-pipeline.md section 5).

Stage 4 claims every word it receives. Rows regions follow the same rules: M2's table stage takes
the tables among them first, and what is left, such as hanging-indent lists, is prose.
"""

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from inkgrid.core.layout import Region
from inkgrid.core.lexicon import enumerator, is_bullet, note_label, section_number
from inkgrid.core.lines import Line
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.invariants import strip_label

ProseKind = Literal["heading", "paragraph", "list_item", "footnote"]
SENTENCE_END = (".", ";", ",")


@dataclass(frozen=True, slots=True)
class ProtoBlock:
    """A block before assembly: its kind, lines, size (its first line's), and kind fields."""

    kind: ProseKind
    lines: tuple[Line, ...]
    size: float
    label: str | None = None
    number: str | None = None


def _paragraph_gap(regions: Sequence[Region], profile: Profile) -> float:
    gaps = [
        cur.top - prev.bottom
        for region in regions
        for prev, cur in zip(region.lines, region.lines[1:], strict=False)
        if cur.top - prev.bottom > 0
    ]
    median = statistics.median(gaps) if gaps else 0.0
    return max(profile.paragraph_gap_ratio * median, profile.paragraph_gap_floor)


def _opens_item(line: Line, lexicon: Lexicon) -> bool:
    first = line.words[0].text
    return is_bullet(first, lexicon) or enumerator(first) is not None


def _breaks(prev: Line, cur: Line, threshold: float, lexicon: Lexicon, profile: Profile) -> bool:
    return (
        cur.top - prev.bottom > threshold
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
    regions: Sequence[Region], lexicon: Lexicon, profile: Profile, body_size: float
) -> tuple[ProtoBlock, ...]:
    """Split one page's regions into typed blocks, in reading order."""
    threshold = _paragraph_gap(regions, profile)
    out: list[ProtoBlock] = []
    for region in regions:
        current: list[Line] = []
        for line in region.lines:
            if current and _breaks(current[-1], line, threshold, lexicon, profile):
                out.append(_block(current, lexicon, profile, body_size))
                current = []
            current.append(line)
        if current:
            out.append(_block(current, lexicon, profile, body_size))
    return tuple(out)
