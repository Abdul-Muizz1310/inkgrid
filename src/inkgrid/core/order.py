"""A page's blocks and tables in reading order, and heading levels (docs/specs/04 section 6).

Assembly and the glossary pass both need them, so they live apart from either.
"""

from collections.abc import Iterable, Sequence

from inkgrid.core.prose import ProtoBlock
from inkgrid.core.tables.proto import ProtoTable


def heading_sizes(items: Iterable[object]) -> list[float]:
    """The distinct heading sizes among the items, to the half point, smallest first."""
    return sorted(
        {round(b.size * 2) / 2 for b in items if isinstance(b, ProtoBlock) and b.kind == "heading"}
    )


def heading_level(size: float, sizes: Sequence[float]) -> int:
    """1 plus the count of distinct heading sizes larger than this one."""
    return 1 + sum(1 for s in sizes if s > round(size * 2) / 2)


def _overlaps(block: ProtoBlock, table: ProtoTable) -> bool:
    """True when the block and the table share some horizontal extent."""
    x0 = min(line.x0 for line in block.lines)
    x1 = max(line.x1 for line in block.lines)
    return x0 < table.bbox.x1 and x1 > table.bbox.x0


def _slot(blocks: Sequence[ProtoBlock], table: ProtoTable) -> int:
    """Where a table goes among a page's blocks: within the column it shares with them."""
    beside = [i for i, b in enumerate(blocks) if _overlaps(b, table)]
    below = [i for i in beside if blocks[i].lines[0].top >= table.bbox.y0]
    if below:
        return below[0]
    return beside[-1] + 1 if beside else len(blocks)


def reading_order(
    blocks: Sequence[ProtoBlock], tables: Sequence[ProtoTable]
) -> list[ProtoBlock | ProtoTable]:
    """Content in reading order, each table before the first block below it in its column."""
    before: dict[int, list[ProtoTable]] = {}
    for table in sorted(tables, key=lambda t: t.bbox.y0):
        before.setdefault(_slot(blocks, table), []).append(table)
    out: list[ProtoBlock | ProtoTable] = []
    for index, block in enumerate(blocks):
        out += before.get(index, [])
        out.append(block)
    out += before.get(len(blocks), [])
    return out
