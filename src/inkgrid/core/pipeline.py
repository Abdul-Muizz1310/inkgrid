"""The pipeline, in order: furniture, tables, layout, prose blocks, assembly (docs/specs/04, 06)."""

from collections import defaultdict

from inkgrid.core.assemble import assemble
from inkgrid.core.furniture import find_furniture
from inkgrid.core.glossary import glossary
from inkgrid.core.joins import join_paragraphs, join_tables
from inkgrid.core.layout import Region, layout
from inkgrid.core.lines import body_size
from inkgrid.core.notes import call_labels, notes
from inkgrid.core.prose import ProtoBlock, line_gaps, page_blocks
from inkgrid.core.tables.corridor import corridor_tables
from inkgrid.core.tables.lattice import lattice_tables
from inkgrid.core.tables.proto import ProtoTable, missing_header
from inkgrid.core.view import upright
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.document import Document, Lattice
from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.geometry import turn_rect
from inkgrid.model.lattice import LatticeReading, RuledGrid
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
    by_page: defaultdict[int, list[RuledGrid]] = defaultdict(list)
    for grid in grids.grids if grids is not None else ():
        by_page[grid.page].append(grid)
    # Each page's grids in the frame its view has: furniture, then the lattice stage, read them.
    frames = {
        page.number: page.rotation if view is not page else 0
        for page, view in zip(reading.pages, views, strict=True)
    }
    turned = {
        page.number: [
            [turn_rect(cell, frames[page.number], page.width, page.height) for cell in grid.cells]
            for grid in by_page[page.number]
        ]
        for page in reading.pages
    }
    furniture = find_furniture(views, profile, grids=turned)
    content = [w for w in reading.words() if w.id not in furniture.word_ids]
    body = body_size(content) if content else 0.0
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
        frame = frames[page.number]
        cores = [
            None if grid.core is None else turn_rect(grid.core, frame, page.width, page.height)
            for grid in by_page[page.number]
        ]
        stage = lattice_tables(
            view,
            turned[page.number],
            words,
            profile,
            frame=frame,
            read=page.number in lattice_read,
            cores=cores,
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
            others=words,
            fills=view.fills,
            charts=stage.charts,
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
    # Notes in every printed form, then continuation (spec 09): each needs the page's final blocks.
    pages, tables = notes(pages, tables, called=call_labels(reading.words()), body=body)
    tables = join_tables(pages, tables, furniture=furniture.lines)
    pages = join_paragraphs(pages, tables)
    # After continuation, so a child whose header is carried raises none.
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
