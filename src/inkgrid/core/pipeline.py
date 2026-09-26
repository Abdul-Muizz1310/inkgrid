"""The text pipeline, in order: furniture, layout, prose blocks, assembly (docs/specs/04)."""

from inkgrid.core.assemble import assemble
from inkgrid.core.furniture import find_furniture
from inkgrid.core.layout import Region, layout
from inkgrid.core.lines import body_size
from inkgrid.core.prose import ProtoBlock, line_gaps, page_blocks
from inkgrid.core.view import upright
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.document import Document, Lattice
from inkgrid.model.page import Reading


def build_document(
    reading: Reading, *, lexicon: Lexicon, profile: Profile, lattice: Lattice
) -> Document:
    """Turn a reading into a proved `Document`."""
    # Layout reads each page in the frame its reader sees; assembly keeps the reading's boxes.
    views = tuple(upright(page) for page in reading.pages)
    furniture = find_furniture(views, profile)
    content = [w for w in reading.words() if w.id not in furniture.word_ids]
    body = body_size(content) if content else 0.0
    regions: list[tuple[Region, ...]] = []
    for page in views:
        words = [w for w in page.words if w.id not in furniture.word_ids]
        regions.append(layout(words, profile, body) if words else ())
    # Line gaps over the document: a page of one-line paragraphs has none of its own.
    gaps = line_gaps([region for page in regions for region in page])
    pages: list[tuple[ProtoBlock, ...]] = [
        page_blocks(page, lexicon, profile, body, gaps) for page in regions
    ]
    return assemble(reading, pages, furniture, lexicon=lexicon, profile=profile, lattice=lattice)
