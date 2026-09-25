"""Normalize every accepted input into bytes and an optional file name.

A wrong *type* is a programming error and raises `TypeError`. A bad *file* is bad input and raises
`PdfOpenError`.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from inkgrid.errors import PdfOpenError

type SourceLike = str | os.PathLike[str] | bytes | bytearray | memoryview | BinaryIO


@dataclass(frozen=True, slots=True)
class Loaded:
    """The raw PDF bytes, and the base name when they came from a path."""

    data: bytes
    file_name: str | None


def _from_path(path: Path) -> Loaded:
    try:
        data = path.read_bytes()
    except OSError as exc:
        msg = f"cannot read {path}: {exc.strerror or exc}"
        raise PdfOpenError(msg) from exc
    return Loaded(data, path.name)


def _from_stream(stream: BinaryIO) -> Loaded:
    # Typed `object` on purpose: a text-mode stream passed as BinaryIO returns str at runtime.
    data: object = stream.read()
    if not isinstance(data, bytes):
        msg = f"stream.read() returned {type(data).__name__}; open the file in binary mode (bytes)"
        raise TypeError(msg)
    return Loaded(data, None)


def load_source(source: SourceLike) -> Loaded:
    """Read `source` fully.

    Raises:
        TypeError: `source` is not a path, bytes-like object, or binary stream.
        PdfOpenError: the path cannot be read, or the input is empty.
    """
    if isinstance(source, bytes | bytearray | memoryview):
        loaded = Loaded(bytes(source), None)
    elif isinstance(source, str | os.PathLike):
        loaded = _from_path(Path(source))
    elif hasattr(source, "read"):
        loaded = _from_stream(source)
    else:
        msg = f"cannot read a PDF from {type(source).__name__}"
        raise TypeError(msg)
    if not loaded.data:
        msg = "empty input"
        raise PdfOpenError(msg)
    return loaded
