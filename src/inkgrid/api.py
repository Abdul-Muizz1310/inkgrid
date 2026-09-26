"""The public entry points: the only module where the shell meets the core."""

from inkgrid.core.pipeline import build_document
from inkgrid.core.tables.pages import lattice_pages
from inkgrid.errors import StrictModeError
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.document import Document, Lattice
from inkgrid.model.findings import Severity, summarize
from inkgrid.model.page import Reading
from inkgrid.read.camelot_reader import read_lattice
from inkgrid.read.pymupdf_reader import lattice_copy, page_frames, read_pdf
from inkgrid.read.source import SourceLike, load_source


def read_pages(source: SourceLike, *, password: str | None = None) -> Reading:
    """Read a PDF's text layer and drawings into the raw page model.

    This is the debugging view of a reading: words, rules and page measurements, before any layout
    decision. `read()` builds blocks on top of it.

    Args:
        source: a path, bytes-like object, or binary stream holding a PDF.
        password: the user password, for an encrypted PDF.

    Raises:
        TypeError: `source` is not a supported input type.
        PdfOpenError: the input is missing, empty, or not a readable PDF.
        PasswordRequired: the PDF needs a password and none was given.
        WrongPassword: the password does not open the PDF.
    """
    loaded = load_source(source)
    return read_pdf(loaded.data, file_name=loaded.file_name, password=password)


def _lattice(value: str) -> Lattice:
    match value:
        case "combined":
            return "combined"
        case "vector":
            return "vector"
        case "raster":
            return "raster"
        case _:
            msg = f"lattice must be 'combined', 'vector', or 'raster', not {value!r}"
            raise ValueError(msg)


def _profile(value: object) -> Profile:
    """The profile to run, revalidated: callers without type checking can pass anything."""
    if value is None:
        return Profile.default()
    if not isinstance(value, Profile):
        msg = f"profile must be an inkgrid.Profile, not {type(value).__name__}"
        raise TypeError(msg)
    return Profile.model_validate(value)


def _lexicon(value: object) -> Lexicon:
    """The lexicon to run, revalidated: callers without type checking can pass anything."""
    if value is None:
        return Lexicon.default()
    if not isinstance(value, Lexicon):
        msg = f"lexicon must be an inkgrid.Lexicon, not {type(value).__name__}"
        raise TypeError(msg)
    return Lexicon.model_validate(value)


def read(
    source: SourceLike,
    *,
    password: str | None = None,
    lexicon: Lexicon | None = None,
    profile: Profile | None = None,
    lattice: str = "combined",
    strict: bool = False,
) -> Document:
    """Read a PDF into a validated `Document`: every word in exactly one block, in reading order.

    Args:
        source: a path, bytes-like object, or binary stream holding a PDF.
        password: the user password, for an encrypted PDF.
        lexicon: token classes; `Lexicon.default()` when omitted.
        profile: geometry tolerances; `Profile.default()` when omitted.
        lattice: Camelot's lattice engine for ruled tables: `combined`, `vector`, or `raster`.
        strict: raise instead of returning a document that carries an error-severity finding.

    Raises:
        TypeError: `source`, `lexicon`, or `profile` is of the wrong type.
        ValueError: `lattice` is unknown, or a configuration fails revalidation.
        PdfOpenError, PasswordRequired, WrongPassword: as for `read_pages`.
        StrictModeError: `strict` is set and the document carries an error-severity finding.
        InvariantError: a guarantee failed to hold, which is a bug in inkgrid.
    """
    checked_lexicon = _lexicon(lexicon)
    checked_profile = _profile(profile)
    checked_lattice = _lattice(lattice)
    loaded = load_source(source)
    reading = read_pdf(loaded.data, file_name=loaded.file_name, password=password)
    # Camelot renders every page it reads at 300 DPI, so it reads only pages ruled both ways.
    pages = lattice_pages(reading)
    grids = (
        read_lattice(
            lattice_copy(loaded.data, password),
            page_frames(loaded.data, password),
            pages,
            engine=checked_lattice,
            password=None,
        )
        if pages
        else None
    )
    doc = build_document(
        reading,
        lexicon=checked_lexicon,
        profile=checked_profile,
        lattice=checked_lattice,
        grids=grids,
    )
    if strict and not doc.complete:
        errors = [f for f in doc.findings if f.severity is Severity.ERROR]
        msg = f"strict mode: the document carries error findings: {summarize(errors)}"
        raise StrictModeError(msg)
    return doc
