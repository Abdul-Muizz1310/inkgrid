"""The inkgrid exception hierarchy.

Bad input raises one of these at the boundary. Degradation is never an exception: it becomes a
`Finding` on the result. A broken invariant is a bug and raises `InvariantError`.
"""


class InkgridError(Exception):
    """Base class of every error inkgrid raises on purpose."""


class PdfOpenError(InkgridError):
    """The input is not a readable PDF (missing, empty, damaged beyond repair, or not a PDF)."""


class PasswordRequired(InkgridError):
    """The PDF is encrypted with a user password and none was given."""


class WrongPassword(InkgridError):
    """The PDF is encrypted and the given password does not open it."""


class SourceMismatch(InkgridError):
    """The PDF given is not the one the document was read from: its SHA-256 differs."""


class InvariantError(InkgridError):
    """A guarantee failed to hold: a bug in inkgrid, never an input problem."""


class StrictModeError(InkgridError):
    """Strict mode is on and the result carries an error-severity finding."""
