"""Local type stub: only the parts of pypdfium2 5.13 that `inkgrid.verify.pdfium_reader` calls,
and the page rendering the benchmark's ablation calls (docs/specs/15-heavy-competitors.md s. 4).

pypdfium2 ships no type hints. The shapes below were measured on pypdfium2 5.13.0 with PDFium
153.0.7999.0 (docs/specs/10-verify.md section 0).
"""

from PIL.Image import Image
from pypdfium2 import raw as raw
from pypdfium2 import version as version
from pypdfium2.raw import FPDF_PAGE, FPDF_TEXTPAGE

class PdfiumError(RuntimeError):
    # PDFium's FPDF_GetLastError code when a document fails to load; FPDF_ERR_PASSWORD is 4.
    err_code: int | None

class PdfTextPage:
    raw: FPDF_TEXTPAGE
    def close(self) -> None: ...

class PdfBitmap:
    def to_pil(self) -> Image: ...

class PdfPage:
    raw: FPDF_PAGE
    # Renders the page as it displays: /Rotate applied, `rotation` turns it further.
    def render(self, scale: float = 1, rotation: int = 0) -> PdfBitmap: ...
    def get_textpage(self) -> PdfTextPage: ...
    def get_rotation(self) -> int: ...
    def get_mediabox(self) -> tuple[float, float, float, float]: ...
    def get_size(self) -> tuple[float, float]: ...  # as the page displays
    def close(self) -> None: ...

class PdfDocument:
    def __init__(self, input: bytes, password: str | None = None) -> None: ...
    def __len__(self) -> int: ...
    # Raises PdfiumError("Failed to load page.") for a page PDFium cannot load.
    def __getitem__(self, index: int) -> PdfPage: ...
    def close(self) -> None: ...
