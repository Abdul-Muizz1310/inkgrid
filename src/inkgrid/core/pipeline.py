"""The text pipeline, in order: furniture, layout, prose blocks, assembly (docs/specs/04)."""

from inkgrid.core.assemble import assemble
from inkgrid.core.furniture import find_furniture
from inkgrid.core.layout import layout
from inkgrid.core.lines import body_size
from inkgrid.core.prose import ProtoBlock, page_blocks
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.document import Document, Lattice
from inkgrid.model.page import Reading


def build_document(
    reading: Reading, *, lexicon: Lexicon, profile: Profile, lattice: Lattice
) -> Document:
    """Turn a reading into a proved `Document`."""
    furniture = find_furniture(reading.pages, profile)
    content = [w for w in reading.words() if w.id not in furniture.word_ids]
    body = body_size(content) if content else 0.0
    pages: list[tuple[ProtoBlock, ...]] = []
    for page in reading.pages:
        words = [w for w in page.words if w.id not in furniture.word_ids]
        pages.append(
            page_blocks(layout(words, profile, body), lexicon, profile, body) if words else ()
        )
    return assemble(reading, pages, furniture, lexicon=lexicon, profile=profile, lattice=lattice)
