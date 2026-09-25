"""Read a PDF's text layer and drawings with PyMuPDF. The only module that imports pymupdf.

PyMuPDF is not thread-safe, and neither is this module: parallelize across processes.
"""

import importlib.metadata
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final, Literal

import pymupdf

from inkgrid.errors import PasswordRequired, PdfOpenError, WrongPassword
from inkgrid.model.canonical import sha256_hex
from inkgrid.model.findings import Finding
from inkgrid.model.page import PageModel, ReaderInfo, Reading, Source, expected_text_layer
from inkgrid.read.page_findings import engine_warning_findings
from inkgrid.read.raw import (
    CurveItem,
    LineItem,
    PathItem,
    QuadItem,
    RawChar,
    RawLine,
    RawPath,
    RawSpan,
    RectItem,
)
from inkgrid.read.rules import extract_rules
from inkgrid.read.words import build_words

# CID fallback, ligatures and images are all off on purpose: see docs/specs/02-reader.md section 3.
TEXT_FLAGS = pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_CLIP
QUARTER_TURNS: Final[tuple[Literal[0, 90, 180, 270], ...]] = (0, 90, 180, 270)


def _rotation(value: int) -> Literal[0, 90, 180, 270]:
    """The page's /Rotate as a quarter turn; PDF allows only multiples of 90, so snap others."""
    return QUARTER_TURNS[round((value % 360) / 90) % 4]


@contextmanager
def _quiet() -> Iterator[list[str]]:
    """Silence MuPDF's console output and collect its warnings; restore settings afterwards."""
    tools = pymupdf.TOOLS
    show_errors = tools.mupdf_display_errors()
    show_warnings = tools.mupdf_display_warnings()
    tools.mupdf_display_errors(on=False)
    tools.mupdf_display_warnings(on=False)
    tools.reset_mupdf_warnings()
    collected: list[str] = []
    try:
        yield collected
    finally:
        collected.extend(tools.mupdf_warnings().splitlines())
        tools.reset_mupdf_warnings()
        tools.mupdf_display_errors(on=show_errors)
        tools.mupdf_display_warnings(on=show_warnings)


def _open(data: bytes, password: str | None) -> pymupdf.Document:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except pymupdf.FileDataError as exc:
        msg = f"not a readable PDF: {exc}"
        raise PdfOpenError(msg) from exc
    if doc.needs_pass:
        if password is None:
            doc.close()
            msg = "the PDF is encrypted; a password is required"
            raise PasswordRequired(msg)
        if not doc.authenticate(password):
            doc.close()
            msg = "the password does not open this PDF"
            raise WrongPassword(msg)
    if doc.page_count == 0:
        doc.close()
        msg = "not a readable PDF: the document has no pages"
        raise PdfOpenError(msg)
    return doc


def _raw_lines(page: pymupdf.Page) -> tuple[RawLine, ...]:
    raw = page.get_text("rawdict", flags=TEXT_FLAGS)
    lines: list[RawLine] = []
    for block in raw["blocks"]:
        for line in block.get("lines", []):
            spans = tuple(
                RawSpan(
                    font=span["font"],
                    size=span["size"],
                    flags=span["flags"],
                    char_flags=span["char_flags"],
                    chars=tuple(RawChar(ch["c"], ch["bbox"]) for ch in span["chars"]),
                )
                for span in line["spans"]
            )
            lines.append(RawLine(direction=line["dir"], spans=spans))
    return tuple(lines)


def _raw_item(item: "pymupdf.DrawItem") -> PathItem:  # stub-only alias
    match item:
        case ("l", p, q):
            return LineItem((p.x, p.y), (q.x, q.y))
        case ("re", r, _):
            return RectItem((r.x0, r.y0, r.x1, r.y1))
        case ("qu", quad):
            return QuadItem(
                (
                    (quad.ul.x, quad.ul.y),
                    (quad.ll.x, quad.ll.y),
                    (quad.ur.x, quad.ur.y),
                    (quad.lr.x, quad.lr.y),
                )
            )
        case _:
            return CurveItem()


def _raw_paths(page: pymupdf.Page) -> tuple[RawPath, ...]:
    return tuple(
        RawPath(
            kind=d["type"],
            width=d["width"],
            color=d["color"],
            stroke_opacity=d["stroke_opacity"],
            fill=d["fill"],
            fill_opacity=d["fill_opacity"],
            items=tuple(_raw_item(item) for item in d["items"]),
        )
        for d in page.get_drawings()
    )


def _page_model(page: pymupdf.Page, number: int, first_id: int) -> PageModel:
    out = build_words(_raw_lines(page), number, first_id)
    rules = extract_rules(_raw_paths(page), number)
    return PageModel(
        number=number,
        width=page.cropbox.width,
        height=page.cropbox.height,
        rotation=_rotation(page.rotation),
        text_layer=expected_text_layer(len(out.words), out.unmapped_chars),
        invisible_chars=out.invisible_chars,
        clipped_chars=0,
        unmapped_chars=out.unmapped_chars,
        hidden_chars=out.hidden_chars,
        image_area_ratio=0.0,
        words=out.words,
        rules=rules,
    )


def read_pdf(data: bytes, *, file_name: str | None, password: str | None) -> Reading:
    """Read every page of the PDF in `data` into a `Reading`.

    Raises:
        PdfOpenError: `data` is not a readable PDF, or has no pages.
        PasswordRequired: the PDF needs a user password and `password` is None.
        WrongPassword: `password` does not open the PDF.
    """
    pages: list[PageModel] = []
    with _quiet() as messages:
        doc = _open(data, password)
        try:
            next_id = 0
            for index in range(doc.page_count):
                model = _page_model(doc.load_page(index), index + 1, next_id)
                next_id += len(model.words)
                pages.append(model)
        finally:
            doc.close()
    findings: tuple[Finding, ...] = engine_warning_findings(messages)
    return Reading(
        source=Source(sha256=sha256_hex(data), pages=len(pages), file_name=file_name),
        reader=ReaderInfo(
            inkgrid=importlib.metadata.version("inkgrid"),
            pymupdf=pymupdf.VersionBind,
            mupdf=pymupdf.VersionFitz,
        ),
        pages=tuple(pages),
        findings=findings,
    )
