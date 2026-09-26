"""Build a Document with its ruled tables, through the pipeline, for tests below the API."""

from inkgrid.core.pipeline import build_document
from inkgrid.core.tables.pages import lattice_pages
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.document import Document, Lattice
from inkgrid.read.camelot_reader import read_lattice
from inkgrid.read.pymupdf_reader import lattice_copy, page_frames, read_pdf


def read_with_tables(data: bytes, engine: Lattice = "vector") -> Document:
    """The document `inkgrid.read` gives, with Camelot reading the ruled pages."""
    reading = read_pdf(data, file_name=None, password=None)
    grids = read_lattice(
        lattice_copy(data, None),
        page_frames(data, None),
        lattice_pages(reading),
        engine=engine,
        password=None,
    )
    return build_document(
        reading, lexicon=Lexicon(), profile=Profile(), lattice=engine, grids=grids
    )
