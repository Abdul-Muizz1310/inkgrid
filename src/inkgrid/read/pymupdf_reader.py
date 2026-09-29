"""Read a PDF's text layer and drawings with PyMuPDF. The only module that imports pymupdf.

PyMuPDF is not thread-safe, and neither is this module: parallelize across processes.

`pymupdf.DrawItem`, `pymupdf.ImageInfo` and `pymupdf.FontEntry` exist only in the local stub, so
annotations here are postponed and never evaluated at runtime.
"""

from __future__ import annotations

import importlib.metadata
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Final, Literal

import pymupdf

from inkgrid.errors import PasswordRequired, PdfOpenError, WrongPassword
from inkgrid.model.canonical import sha256_hex
from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.lattice import PageFrame
from inkgrid.model.page import PageModel, ReaderInfo, Reading, Source, Word, expected_text_layer
from inkgrid.read.glyphs import charset_names, differences_names, glyph_reading, stem
from inkgrid.read.page_findings import PageSignals, engine_warning_findings, page_findings
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
from inkgrid.read.rules import extract_fills, extract_rules
from inkgrid.read.words import WordsOut, build_words

# CID fallback, ligatures and images are all off on purpose: see docs/specs/02-reader.md section 3.
TEXT_FLAGS = pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_CLIP
# No clipping at all: with an infinite clip MuPDF also returns text outside the CropBox.
UNCLIPPED_FLAGS = pymupdf.TEXT_PRESERVE_WHITESPACE
QUARTER_TURNS: Final[tuple[Literal[0, 90, 180, 270], ...]] = (0, 90, 180, 270)
TYPE3 = "Type3"
# Font kinds whose glyphs carry names MuPDF may read from their digits (spec 13 section 3).
NAMED_GLYPH_KINDS: Final = frozenset({"Type1", "MMType1"})
NOT_EMBEDDED = "n/a"
ORIGIN_DIGITS = 2
# What MuPDF raises for damaged content. Its own error base is not a RuntimeError.
MUPDF_ERRORS: Final = (RuntimeError, pymupdf.mupdf.FzErrorBase)
# Loading a page also raises ValueError, for a page tree that declares more pages than it holds.
LOAD_ERRORS: Final = (ValueError, *MUPDF_ERRORS)


def _rotation(value: int) -> Literal[0, 90, 180, 270]:
    """The page's /Rotate as a quarter turn; PDF allows only multiples of 90, so snap others."""
    return QUARTER_TURNS[round((value % 360) / 90) % 4]


class _Warnings:
    """MuPDF's accumulated warnings, taken in batches so each can be pinned to where it arose."""

    def take(self) -> tuple[str, ...]:
        tools = pymupdf.TOOLS
        batch = tuple(line for line in tools.mupdf_warnings().splitlines() if line.strip())
        tools.reset_mupdf_warnings()
        return batch


@contextmanager
def _quiet() -> Iterator[_Warnings]:
    """Silence MuPDF's console output around a read; restore its settings afterwards."""
    tools = pymupdf.TOOLS
    show_errors = tools.mupdf_display_errors()
    show_warnings = tools.mupdf_display_warnings()
    tools.mupdf_display_errors(on=False)
    tools.mupdf_display_warnings(on=False)
    tools.reset_mupdf_warnings()
    try:
        yield _Warnings()
    finally:
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


type GlyphFixes = dict[tuple[str, float, float], str]


def _origin_key(font: str, origin: tuple[float, float]) -> tuple[str, float, float]:
    return (font, round(origin[0], ORIGIN_DIGITS), round(origin[1], ORIGIN_DIGITS))


def _in_agl(name: str) -> bool:
    return pymupdf.mupdf.fz_unicode_from_glyph_name_strict(stem(name)) != 0


@dataclass
class _GlyphFonts:
    """Per document, each font xref's program when its encoding names such a glyph, else None.

    A glyph MuPDF reads from its name's digits (`a71`) is found through the font program; a font
    with no such name costs a few dictionary lookups, once per document.
    """

    doc: pymupdf.Document
    programs: dict[int, pymupdf.Font | None] = field(default_factory=dict)

    def _text(self, xref: int, key: str) -> str:
        kind, value = self.doc.xref_get_key(xref, key)
        if kind == "xref":
            return self.doc.xref_object(int(value.split()[0]))
        return value if kind in {"dict", "string", "array"} else ""

    def _load(self, xref: int, ext: str, kind: str) -> pymupdf.Font | None:
        if kind not in NAMED_GLYPH_KINDS or ext == NOT_EMBEDDED:
            return None
        if self.doc.xref_get_key(xref, "ToUnicode")[0] != "null":
            return None
        names = differences_names(self._text(xref, "Encoding"))
        descriptor = self.doc.xref_get_key(xref, "FontDescriptor")
        if descriptor[0] == "xref":
            names |= charset_names(self._text(int(descriptor[1].split()[0]), "CharSet"))
        if not any(glyph_reading(n, font="", in_agl=_in_agl(n)) is not None for n in names):
            return None
        program = self.doc.extract_font(xref)[3]
        return pymupdf.Font(fontbuffer=program) if program else None

    def _program(self, xref: int, ext: str, kind: str) -> pymupdf.Font | None:
        if xref not in self.programs:
            try:
                self.programs[xref] = self._load(xref, ext, kind)
            except MUPDF_ERRORS:  # a broken dictionary or program: MuPDF's reading stands
                self.programs[xref] = None
        return self.programs[xref]

    def fixes(self, page: pymupdf.Page, fonts: list[pymupdf.FontEntry]) -> GlyphFixes:
        """The page's characters whose glyph names read otherwise, by font and origin.

        Text traces and `rawdict` name a font without its subset tag, so a font whose name another
        font on the page shares is left as MuPDF reads it: its glyphs cannot be told apart.
        """
        names = [basefont.split("+", 1)[-1] for _, _, _, basefont, *_ in fonts]
        programs: dict[str, pymupdf.Font] = {}
        for (xref, ext, kind, _, *_), name in zip(fonts, names, strict=True):
            program = self._program(xref, ext, kind)
            if program is not None and names.count(name) == 1:
                programs[name] = program
        if not programs:
            return {}
        try:
            return self._traced(page, programs)
        except MUPDF_ERRORS:
            return {}

    @staticmethod
    def _traced(page: pymupdf.Page, programs: dict[str, pymupdf.Font]) -> GlyphFixes:
        out: GlyphFixes = {}
        for trace in page.get_texttrace():
            program = programs.get(trace["font"])
            if program is None:
                continue
            for _, glyph, origin, _ in trace["chars"]:
                name = pymupdf.mupdf.fz_get_glyph_name2(program.this, glyph)
                reading = glyph_reading(name, font=trace["font"], in_agl=_in_agl(name))
                if reading is not None:
                    out[_origin_key(trace["font"], origin)] = reading
        return out


def _raw_lines(
    page: pymupdf.Page, fixes: GlyphFixes | None = None, *, unclipped: bool = False
) -> tuple[RawLine, ...]:
    fixes = fixes or {}
    if unclipped:
        raw = page.get_text("rawdict", flags=UNCLIPPED_FLAGS, clip=pymupdf.INFINITE_RECT())
    else:
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
                    alpha=span["alpha"],
                    chars=tuple(
                        RawChar(
                            fixes.get(_origin_key(span["font"], ch["origin"]), ch["c"]), ch["bbox"]
                        )
                        for ch in span["chars"]
                    ),
                )
                for span in line["spans"]
            )
            lines.append(RawLine(direction=line["dir"], spans=spans))
    return tuple(lines)


def _raw_item(item: pymupdf.DrawItem) -> PathItem:
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


def _image_area_ratio(images: list[pymupdf.ImageInfo], width: float, height: float) -> float:
    """The page area image placements cover, clipped to the page and capped at 1."""
    covered = 0.0
    for image in images:
        x0, y0, x1, y1 = image["bbox"]
        w = min(x1, width) - max(x0, 0.0)
        h = min(y1, height) - max(y0, 0.0)
        if w > 0 and h > 0:
            covered += w * h
    return min(1.0, covered / (width * height))


def _type3_names(fonts: list[pymupdf.FontEntry]) -> frozenset[str]:
    """The span font names PyMuPDF gives Type 3 fonts: `Type3 (<xref> 0 R)`, or their name."""
    names = {f"{TYPE3} ({xref} 0 R)" for xref, _, kind, *_ in fonts if kind == TYPE3}
    names |= {basefont for _, _, kind, basefont, *_ in fonts if kind == TYPE3 and basefont}
    return frozenset(names)


def _chars(words: tuple[Word, ...]) -> int:
    return sum(len(w.text) for w in words)


def _drawn(out: WordsOut) -> int:
    """The characters a reading's words were built from, copies (W8) included."""
    return _chars(out.words) + out.overprinted_chars


@dataclass(frozen=True, slots=True)
class _Extracted:
    lines: tuple[RawLine, ...] = ()
    unclipped: tuple[RawLine, ...] = ()
    paths: tuple[RawPath, ...] = ()
    images: tuple[pymupdf.ImageInfo, ...] = ()
    fonts: tuple[pymupdf.FontEntry, ...] = ()
    error: str | None = None


def _extract(page: pymupdf.Page, glyph_fonts: _GlyphFonts) -> _Extracted:
    """Everything the page model needs from PyMuPDF; a failure empties the page, never raises."""
    try:
        fonts = page.get_fonts()
        fixes = glyph_fonts.fixes(page, fonts)
        return _Extracted(
            lines=_raw_lines(page, fixes),
            unclipped=_raw_lines(page, fixes, unclipped=True),
            paths=_raw_paths(page),
            images=tuple(page.get_image_info()),
            fonts=tuple(fonts),
        )
    except MUPDF_ERRORS as exc:
        return _Extracted(error=f"{type(exc).__name__}: {exc}")


def _page_box(page: pymupdf.Page) -> pymupdf.Rect | None:
    """The CropBox clipped to the MediaBox, in PDF coordinates; None when they do not meet.

    PDF 32000-1 section 14.11.2 reduces a box reaching past the MediaBox to their intersection.
    PyMuPDF measures `cropbox` down from the MediaBox top, and `mediabox` in PDF coordinates.
    """
    crop, media = page.cropbox, page.mediabox
    x0, x1 = max(crop.x0, media.x0), min(crop.x1, media.x1)
    y0, y1 = max(media.y1 - crop.y1, media.y0), min(media.y1 - crop.y0, media.y1)
    if x1 <= x0 or y1 <= y0:
        return None
    return pymupdf.Rect(x0, y0, x1, y1)


def _page_size(page: pymupdf.Page) -> tuple[float, float]:
    """The page's unrotated size: its clipped CropBox's, or the MediaBox's when none is left."""
    box = _page_box(page) or page.mediabox
    return box.width, box.height


def _page_model(
    page: pymupdf.Page, number: int, first_id: int, glyph_fonts: _GlyphFonts
) -> tuple[PageModel, PageSignals]:
    if _page_box(page) is None:
        c, m = page.cropbox, page.mediabox
        crop = f"({c.x0:g}, {m.y1 - c.y1:g}, {c.x1:g}, {m.y1 - c.y0:g})"
        media = f"({m.x0:g}, {m.y0:g}, {m.x1:g}, {m.y1:g})"
        got = _Extracted(error=f"its CropBox {crop} does not meet its MediaBox {media}")
    else:
        got = _extract(page, glyph_fonts)
    type3 = _type3_names(list(got.fonts))
    out = build_words(got.lines, number, first_id, type3_fonts=type3)
    seen = build_words(got.unclipped, number, first_id, type3_fonts=type3)
    width, height = _page_size(page)
    model = PageModel(
        number=number,
        width=width,
        height=height,
        rotation=_rotation(page.rotation),
        text_layer=expected_text_layer(len(out.words), out.unmapped_chars),
        invisible_chars=out.invisible_chars,
        clipped_chars=max(0, _drawn(seen) - _drawn(out)),
        unmapped_chars=out.unmapped_chars,
        hidden_chars=out.hidden_chars,
        image_area_ratio=_image_area_ratio(list(got.images), width, height),
        overprinted_chars=out.overprinted_chars,
        words=out.words,
        rules=extract_rules(got.paths, number),
        fills=extract_fills(got.paths),
    )
    signals = PageSignals(
        has_image=bool(got.images),
        has_curves=any(isinstance(i, CurveItem) for path in got.paths for i in path.items),
        type3_chars=sum(len(w.text) for w in out.words if w.font in type3),
        extraction_error=got.error,
    )
    return model, signals


def _unreadable(declared: int, loaded: int) -> Finding:
    missing = declared - loaded
    detail = (
        f"{missing} of {declared} declared pages could not be loaded "
        f"(pages {loaded + 1}-{declared}); the reading holds pages 1-{loaded}"
    )
    return Finding.of(FindingCode.UNREADABLE_PAGE, detail)


def read_pdf(data: bytes, *, file_name: str | None, password: str | None) -> Reading:
    """Read every page of the PDF in `data` into a `Reading`.

    Raises:
        PdfOpenError: `data` is not a readable PDF, or not even its first page can be loaded.
        PasswordRequired: the PDF needs a user password and `password` is None.
        WrongPassword: `password` does not open the PDF.
    """
    pages: list[PageModel] = []
    findings: list[Finding] = []
    with _quiet() as warnings:
        doc = _open(data, password)
        try:
            opening = warnings.take()
            declared = doc.page_count
            next_id = 0
            glyph_fonts = _GlyphFonts(doc)
            for index in range(declared):
                try:
                    page = doc.load_page(index)
                except LOAD_ERRORS:
                    break
                model, signals = _page_model(page, index + 1, next_id, glyph_fonts)
                signals = PageSignals(
                    has_image=signals.has_image,
                    has_curves=signals.has_curves,
                    type3_chars=signals.type3_chars,
                    warnings=warnings.take(),
                    extraction_error=signals.extraction_error,
                )
                next_id += len(model.words)
                pages.append(model)
                findings.extend(page_findings(model, signals))
            closing = warnings.take()
        finally:
            doc.close()
    if not pages:
        msg = f"not a readable PDF: none of its {declared} declared pages can be loaded"
        raise PdfOpenError(msg)
    findings.extend(engine_warning_findings((*opening, *closing)))
    if len(pages) < declared:
        findings.append(_unreadable(declared, len(pages)))
    return Reading(
        source=Source(sha256=sha256_hex(data), pages=len(pages), file_name=file_name),
        reader=ReaderInfo(
            inkgrid=importlib.metadata.version("inkgrid"),
            pymupdf=pymupdf.VersionBind,
            mupdf=pymupdf.VersionFitz,
        ),
        pages=tuple(pages),
        findings=tuple(findings),
    )


def render_pages(data: bytes, password: str | None, dpi: int) -> tuple[bytes | None, ...]:
    """Each page as PNG, unrotated to match the page model; None for a page MuPDF cannot render.

    Rendering stops at the first page that cannot load, as `read_pdf` does. The rotation change is
    made on the in-memory document only.
    """
    images: list[bytes | None] = []
    with _quiet():
        doc = _open(data, password)
        try:
            for index in range(doc.page_count):
                try:
                    page = doc.load_page(index)
                except LOAD_ERRORS:
                    break
                try:
                    page.set_rotation(0)
                    images.append(page.get_pixmap(dpi=dpi).tobytes("png"))
                except MUPDF_ERRORS:
                    images.append(None)
        finally:
            doc.close()
    return tuple(images)


def page_frames(data: bytes, password: str | None) -> tuple[PageFrame, ...]:
    """Each loadable page's rotation and unrotated CropBox size, for placing Camelot's grids."""
    frames: list[PageFrame] = []
    with _quiet():
        doc = _open(data, password)
        try:
            for index in range(doc.page_count):
                try:
                    page = doc.load_page(index)
                except LOAD_ERRORS:
                    break
                width, height = _page_size(page)
                frames.append(
                    PageFrame(
                        number=index + 1,
                        rotation=_rotation(page.rotation),
                        width=width,
                        height=height,
                    )
                )
        finally:
            doc.close()
    return tuple(frames)


def lattice_copy(data: bytes, password: str | None) -> bytes:
    """The document as Camelot must read it: decrypted, each page's MediaBox set to its CropBox.

    Camelot's raster engines render the CropBox but scale it by the MediaBox, and its parser needs
    an optional package for AES. With the two boxes equal (the CropBox clipped to the MediaBox)
    and no encryption, every engine places its grids in the page model's frame.
    """
    with _quiet():
        doc = _open(data, password)
        try:
            for index in range(doc.page_count):
                try:
                    page = doc.load_page(index)
                except LOAD_ERRORS:
                    break
                rotation = page.rotation
                page.set_rotation(0)
                box = _page_box(page)
                if box is not None:
                    page.set_mediabox(box)
                page.set_rotation(rotation)
            return doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_NONE)
        finally:
            doc.close()
