import io
import os
import sys
from pathlib import Path

import pytest

from inkgrid.errors import PdfOpenError
from inkgrid.read.source import load_source

PDF = b"%PDF-1.7 not really, but bytes are bytes"


class Pipe(io.RawIOBase):
    """A non-seekable stream serving its data in 7-byte chunks."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return False

    def readinto(self, buffer: memoryview) -> int:  # type: ignore[override]
        chunk, self._data = self._data[:7], self._data[7:]
        buffer[: len(chunk)] = chunk
        return len(chunk)


def test_S1_path_gives_bytes_and_base_name(tmp_path: Path) -> None:
    path = tmp_path / "fees.pdf"
    path.write_bytes(PDF)
    for source in (path, str(path)):
        loaded = load_source(source)
        assert (loaded.data, loaded.file_name) == (PDF, "fees.pdf")


@pytest.mark.parametrize(
    "source",
    [PDF, bytearray(PDF), memoryview(PDF), io.BytesIO(PDF)],
    ids=["bytes", "bytearray", "memoryview", "BytesIO"],
)
def test_S2_in_memory_sources(source: object) -> None:
    loaded = load_source(source)  # type: ignore[arg-type]
    assert (loaded.data, loaded.file_name) == (PDF, None)
    assert type(loaded.data) is bytes


def test_S3_missing_path_and_directory(tmp_path: Path) -> None:
    with pytest.raises(PdfOpenError, match="cannot read") as missing:
        load_source(tmp_path / "absent.pdf")
    assert isinstance(missing.value.__cause__, OSError)
    with pytest.raises(PdfOpenError, match="cannot read"):
        load_source(tmp_path)


def test_S4_text_mode_file_object(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="bytes"):
        load_source(io.StringIO("text"))  # type: ignore[arg-type]


@pytest.mark.parametrize("source", [None, 42, 3.5], ids=["none", "int", "float"])
def test_S5_unsupported_types(source: object) -> None:
    with pytest.raises(TypeError, match="cannot read a PDF from"):
        load_source(source)  # type: ignore[arg-type]


@pytest.mark.parametrize("kind", ["bytes", "path", "stream"])
def test_S6_empty_input(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "empty.pdf"
    path.write_bytes(b"")
    source = {"bytes": b"", "path": path, "stream": io.BytesIO(b"")}[kind]
    with pytest.raises(PdfOpenError, match="empty input"):
        load_source(source)  # type: ignore[arg-type]


def test_load_source_nonseekable_stream() -> None:
    loaded = load_source(io.BufferedReader(Pipe(PDF)))
    assert loaded.data == PDF


def test_load_source_unicode_path(tmp_path: Path) -> None:
    path = tmp_path / "fee schedule Z\u00fcrich.pdf"
    path.write_bytes(PDF)
    assert load_source(path).file_name == "fee schedule Z\u00fcrich.pdf"


@pytest.mark.skipif(
    sys.platform in {"win32", "darwin"},
    reason="Windows and macOS (APFS) file names are always valid Unicode",
)
def test_S7_undecodable_file_name_is_made_valid_unicode(tmp_path: Path) -> None:
    path = tmp_path / os.fsdecode(b"Z\xfcrich.pdf")
    path.write_bytes(PDF)
    loaded = load_source(path)
    assert loaded.file_name == "Z\ufffdrich.pdf"
    loaded.file_name.encode("utf-8")
