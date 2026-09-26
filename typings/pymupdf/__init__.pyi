"""Local type stub: only the parts of PyMuPDF 1.28 that `inkgrid.read.pymupdf_reader` calls.

PyMuPDF ships `py.typed`, but `get_text`, `get_drawings` and friends are untyped and return `Any`.
The shapes below were measured on PyMuPDF 1.28.2 (docs/specs/02-reader.md). A stub on `mypy_path`
replaces the package's inline hints, so anything the reader uses must be declared here.
"""

from collections.abc import Iterator
from typing import Literal, NotRequired, TypedDict, overload

from pymupdf import mupdf as mupdf

VersionBind: str
VersionFitz: str
TEXT_PRESERVE_WHITESPACE: int
TEXT_CLIP: int
PDF_ENCRYPT_NONE: int

class FileDataError(RuntimeError): ...
class EmptyFileError(FileDataError): ...

class Point:
    x: float
    y: float

class Rect:
    x0: float
    y0: float
    x1: float
    y1: float
    def __init__(self, x0: float, y0: float, x1: float, y1: float) -> None: ...
    @property
    def width(self) -> float: ...
    @property
    def height(self) -> float: ...

class Quad:
    ul: Point
    ur: Point
    ll: Point
    lr: Point

type Box = tuple[float, float, float, float]

class RawCharDict(TypedDict):
    c: str
    bbox: Box
    origin: tuple[float, float]
    synthetic: bool

class RawSpanDict(TypedDict):
    font: str
    size: float
    flags: int
    char_flags: int
    alpha: int
    bbox: Box
    chars: list[RawCharDict]

class RawLineDict(TypedDict):
    dir: tuple[float, float]
    wmode: int
    bbox: Box
    spans: list[RawSpanDict]

class RawBlockDict(TypedDict):
    type: int
    bbox: Box
    number: int
    lines: NotRequired[list[RawLineDict]]

class RawDict(TypedDict):
    width: float
    height: float
    blocks: list[RawBlockDict]

type DrawItem = (
    tuple[Literal["l"], Point, Point]
    | tuple[Literal["re"], Rect, int]
    | tuple[Literal["qu"], Quad]
    | tuple[Literal["c"], Point, Point, Point, Point]
)

class DrawingDict(TypedDict):
    type: str
    items: list[DrawItem]
    width: float | None
    color: tuple[float, ...] | None
    fill: tuple[float, ...] | None
    fill_opacity: float | None
    stroke_opacity: float | None

class ImageInfo(TypedDict):
    bbox: Box
    number: int

# (xref, extension, type, basefont, name, encoding); type is e.g. "Type1", "TrueType", "Type3".
type FontEntry = tuple[int, str, str, str, str, str]

class Pixmap:
    width: int
    height: int
    def tobytes(self, output: str = "png") -> bytes: ...

class Page:
    rotation: int
    cropbox: Rect
    mediabox: Rect
    @overload
    def get_text(
        self, option: Literal["rawdict"], *, flags: int = ..., clip: Rect | None = ...
    ) -> RawDict: ...
    @overload
    def get_text(
        self, option: Literal["text"], *, flags: int = ..., clip: Rect | None = ...
    ) -> str: ...
    def get_drawings(self) -> list[DrawingDict]: ...
    def get_image_info(self) -> list[ImageInfo]: ...
    def get_fonts(self) -> list[FontEntry]: ...
    def set_rotation(self, rotation: int) -> None: ...
    def set_mediabox(self, rect: Rect) -> None: ...
    def get_pixmap(self, *, dpi: int) -> Pixmap: ...

class Document:
    page_count: int
    needs_pass: int
    def authenticate(self, password: str) -> int: ...
    def load_page(self, page_id: int) -> Page: ...
    def close(self) -> None: ...
    def __iter__(self) -> Iterator[Page]: ...
    def tobytes(self, *, encryption: int = ...) -> bytes: ...

class _Tools:
    def mupdf_display_errors(self, on: bool | None = None) -> bool: ...
    def mupdf_display_warnings(self, on: bool | None = None) -> bool: ...
    def reset_mupdf_warnings(self) -> None: ...
    def mupdf_warnings(self, reset: bool = True) -> str: ...

TOOLS: _Tools

def open(*, stream: bytes, filetype: str) -> Document: ...
def INFINITE_RECT() -> Rect: ...
