"""The public entry points: the only module where the shell meets the core."""

from inkgrid.model.page import Reading
from inkgrid.read.pymupdf_reader import read_pdf
from inkgrid.read.source import SourceLike, load_source


def read_pages(source: SourceLike, *, password: str | None = None) -> Reading:
    """Read a PDF's text layer and drawings into the raw page model.

    This is the debugging view of a reading: words, rules and page measurements, before any layout
    decision. `inkgrid.read()` (milestone M1) builds blocks and tables on top of it.

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
