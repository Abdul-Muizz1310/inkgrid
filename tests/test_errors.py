import importlib.metadata

import pytest

import inkgrid
from inkgrid import errors

ERROR_CLASSES = [
    errors.PdfOpenError,
    errors.PasswordRequired,
    errors.WrongPassword,
    errors.InvariantError,
    errors.StrictModeError,
]


@pytest.mark.parametrize("cls", ERROR_CLASSES, ids=lambda c: c.__name__)
def test_A3_every_error_subclasses_inkgrid_error(cls: type[Exception]) -> None:
    assert issubclass(cls, errors.InkgridError)
    assert not issubclass(cls, (ValueError, OSError))


def test_A3_inkgrid_error_is_an_exception() -> None:
    assert issubclass(errors.InkgridError, Exception)


def test_A4_version_matches_metadata() -> None:
    assert inkgrid.__version__ == importlib.metadata.version("inkgrid") == "0.1.0.dev0"
