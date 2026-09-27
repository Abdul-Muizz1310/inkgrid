"""The pipeline, in order: furniture, tables, layout, prose blocks, assembly (docs/specs/04, 06)."""

from collections import defaultdict

from inkgrid.core.assemble import assemble
from inkgrid.core.furniture import find_furniture
from inkgrid.core.glossary import glossary
from inkgrid.core.layout import Region, layout
from inkgrid.core.lines import body_size
from inkgrid.core.prose import ProtoBlock, line_gaps, page_blocks
from inkgrid.core.tables.corridor import corridor_tables
from inkgrid.core.tables.lattice import lattice_tables
from inkgrid.core.tables.proto import ProtoTable, missing_header
from inkgrid.core.view import upright
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.document import Document, Lattice
from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.geometry import Rect, turn_rect
from inkgrid.model.lattice import LatticeReading
from inkgrid.model.page import Reading


def build_document(
    reading: Reading,
    *,
    lexicon: Lexicon,
    profile: Profile,
    lattice: Lattice,
    grids: LatticeReading | None = None,
) -> Document:
    """Turn a reading, and the lattice grids read from its ruled pages, into a proved `Document`."""
    # Layout reads each page in the frame its reader sees; assembly keeps the reading's boxes.
    views = tuple(upright(page) for page in reading.pages)
    furniture = find_furniture(views, profile)
    content = [w for w in reading.words() if w.id not in furniture.word_ids]
    body = body_size(content) if content else 0.0
    by_page: defaultdict[int, list[list[Rect]]] = defaultdict(list)
    for grid in grids.grids if grids is not None else ():
        by_page[grid.page].append(list(grid.cells))
    # Pages Camelot read without failing: a failed page already carries lattice_failed.
    failed = (
        {f.page for f in grids.findings if f.code is FindingCode.LATTICE_FAILED} if grids else set()
    )
    lattice_read = set(grids.pages) - failed if grids is not None else set()
    found: list[Finding] = list(grids.findings) if grids is not None else []
    regions: list[tuple[Region, ...]] = []
    tables: list[tuple[ProtoTable, ...]] = []
    for page, view in zip(reading.pages, views, strict=True):
        words = [w for w in view.words if w.id not in furniture.word_ids]
        frame = page.rotation if view is not page else 0
        turned = [
            [turn_rect(cell, frame, page.width, page.height) for cell in cells]
            for cells in by_page[page.number]
        ]
        stage = lattice_tables(
            view, turned, words, profile, frame=frame, read=page.number in lattice_read
        )
        found += stage.findings
        rest = [w for w in words if w.id not in stage.claimed]
        # Unruled tables come from runs of stacked regions; the other lines go back to prose.
        unruled = corridor_tables(
            layout(rest, profile, body) if rest else (),
            profile,
            page=page.number,
            frame=frame,
            rules=view.rules,
        )
        found += unruled.findings
        tables.append((*stage.tables, *unruled.tables))
        regions.append(unruled.regions)
    # Line gaps over the document: a page of one-line paragraphs has none of its own.
    gaps = line_gaps([region for page in regions for region in page])
    pages: list[tuple[ProtoBlock, ...]] = [
        page_blocks(page, lexicon, profile, body, gaps) for page in regions
    ]
    # Glossaries and note lists, document-wide: a definitions section runs across pages.
    marks = frozenset(w.text for w in reading.words() if w.superscript)
    pages, tables = glossary(pages, tables, marks=marks, profile=profile)
    # After continuation (M3), so a child whose header is carried raises none.
    found += [f for page_tables in tables for t in page_tables for f in missing_header(t)]
    return assemble(
        reading,
        pages,
        furniture,
        lexicon=lexicon,
        profile=profile,
        lattice=lattice,
        tables=tables,
        findings=found,
        camelot=grids.camelot if grids is not None else None,
    )
