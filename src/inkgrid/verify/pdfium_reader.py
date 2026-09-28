"""Read a PDF with PDFium into the verifier's ink (docs/specs/10-verify.md section 1).

The only module that imports pypdfium2. It turns PDFium's characters, clip paths and path objects
into `inkgrid.verify.ink` values at the boundary; nothing past it sees a ctypes object.
"""

import ctypes
from collections.abc import Iterator
from dataclasses import dataclass

import pypdfium2 as pdfium
from pypdfium2 import raw, version

from inkgrid.errors import PasswordRequired, WrongPassword
from inkgrid.model.geometry import Rect
from inkgrid.verify.ink import Ink, InkChar, InkPage, Point, char_kind, in_polygon
from inkgrid.verify.rules import InkPath, InkSubpath, extract_rules

Matrix = tuple[float, float, float, float, float, float]
IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
Polygon = tuple[Point, ...]


@dataclass(frozen=True, slots=True)
class _Frame:
    """The page box's top-left corner in PDF space: points map to `(x - x0, y1 - y)`."""

    x0: float
    y1: float

    def point(self, x: float, y: float) -> Point:
        return (x - self.x0, self.y1 - y)


def _then(inner: Matrix, outer: Matrix) -> Matrix:
    """The matrix applying `inner`, then `outer` (PDF row-vector convention)."""
    a, b, c, d, e, f = inner
    a2, b2, c2, d2, e2, f2 = outer
    return (
        a * a2 + b * c2,
        a * b2 + b * d2,
        c * a2 + d * c2,
        c * b2 + d * d2,
        e * a2 + f * c2 + e2,
        e * b2 + f * d2 + f2,
    )


def _apply(m: Matrix, x: float, y: float) -> Point:
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def _matrix(obj: raw.FPDF_PAGEOBJECT) -> Matrix:
    m = raw.FS_MATRIX()
    raw.FPDFPageObj_GetMatrix(obj, m)
    return (m.a, m.b, m.c, m.d, m.e, m.f)


def _point(segment: raw.FPDF_PATHSEGMENT) -> Point:
    x, y = ctypes.c_float(), ctypes.c_float()
    raw.FPDFPathSegment_GetPoint(segment, x, y)
    return (x.value, y.value)


@dataclass(frozen=True, slots=True)
class _Object:
    """A page object with its matrix to page space and its enclosing forms' clip polygons."""

    handle: raw.FPDF_PAGEOBJECT
    kind: int
    matrix: Matrix
    enclosing: tuple[Polygon, ...]


def _objects(page: raw.FPDF_PAGE, frame: _Frame) -> Iterator[_Object]:
    """Every page object, descending into Form XObjects.

    A clip set before a form is drawn belongs to the form object, not to the objects inside it, so
    each form's clip is carried down to everything it holds.
    """
    stack: list[tuple[raw.FPDF_PAGEOBJECT | None, Matrix, tuple[Polygon, ...]]] = [
        (None, IDENTITY, ())
    ]
    while stack:
        form, outer, enclosing = stack.pop()
        count = (
            raw.FPDFPage_CountObjects(page) if form is None else raw.FPDFFormObj_CountObjects(form)
        )
        for i in range(count):
            obj = (
                raw.FPDFPage_GetObject(page, i)
                if form is None
                else raw.FPDFFormObj_GetObject(form, i)
            )
            kind = raw.FPDFPageObj_GetType(obj)
            matrix = _then(_matrix(obj), outer)
            if kind == raw.FPDF_PAGEOBJ_FORM:
                stack.append((obj, matrix, enclosing + _clip(obj, frame)))
            yield _Object(obj, kind, matrix, enclosing)


def _address(obj: raw.FPDF_PAGEOBJECT) -> int | None:
    return ctypes.cast(obj, ctypes.c_void_p).value


def _visible(obj: raw.FPDF_PAGEOBJECT) -> tuple[bool, bool]:
    """Whether the path visibly strokes and fills: a draw mode that paints, and alpha above 0."""
    fill_mode, stroke_mode = ctypes.c_int(), ctypes.c_int()
    raw.FPDFPath_GetDrawMode(obj, fill_mode, stroke_mode)
    r, g, b, a = ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
    stroke = bool(stroke_mode.value) and bool(raw.FPDFPageObj_GetStrokeColor(obj, r, g, b, a))
    stroke = stroke and a.value > 0
    fill = fill_mode.value != 0 and bool(raw.FPDFPageObj_GetFillColor(obj, r, g, b, a))
    return stroke, fill and a.value > 0


def _ink_path(obj: raw.FPDF_PAGEOBJECT, m: Matrix, frame: _Frame) -> InkPath:
    stroke, fill = _visible(obj)
    subpaths: list[InkSubpath] = []
    points: list[Point | None] = []
    closed = False
    for i in range(raw.FPDFPath_CountSegments(obj)):
        segment = raw.FPDFPath_GetPathSegment(obj, i)
        kind = raw.FPDFPathSegment_GetType(segment)
        at = frame.point(*_apply(m, *_point(segment)))
        if kind == raw.FPDF_SEGMENT_MOVETO and points:
            subpaths.append(InkSubpath(tuple(points), closed))
            points, closed = [], False
        if kind == raw.FPDF_SEGMENT_BEZIERTO:
            points.append(None)  # a curve is never part of a straight rule
        points.append(at)
        closed = closed or bool(raw.FPDFPathSegment_GetClose(segment))
    if points:
        subpaths.append(InkSubpath(tuple(points), closed))
    return InkPath(stroke=stroke, fill=fill, subpaths=tuple(subpaths))


def _clip(obj: raw.FPDF_PAGEOBJECT, frame: _Frame) -> tuple[Polygon, ...]:
    """The object's clip paths as polygons in the frame; none when it has no clip path."""
    clip = raw.FPDFPageObj_GetClipPath(obj)
    if not clip:
        return ()
    polygons = []
    for p in range(raw.FPDFClipPath_CountPaths(clip)):
        count = raw.FPDFClipPath_CountPathSegments(clip, p)
        polygons.append(
            tuple(
                frame.point(*_point(raw.FPDFClipPath_GetPathSegment(clip, p, s)))
                for s in range(count)
            )
        )
    return tuple(polygons)


def _box(text_page: raw.FPDF_TEXTPAGE, index: int, frame: _Frame) -> Rect:
    r = raw.FS_RECTF()
    raw.FPDFText_GetLooseCharBox(text_page, index, r)
    (x0, y0), (x1, y1) = frame.point(r.left, r.top), frame.point(r.right, r.bottom)
    return Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def _chars(
    text_page: raw.FPDF_TEXTPAGE, frame: _Frame, clips: dict[int | None, tuple[Polygon, ...]]
) -> tuple[InkChar, ...]:
    """The page's characters; `clips` holds each text object's clip polygons and its forms'."""
    out = []
    for i in range(raw.FPDFText_CountChars(text_page)):
        kind, char = char_kind(
            raw.FPDFText_GetUnicode(text_page, i),
            generated=raw.FPDFText_IsGenerated(text_page, i) == 1,
            hyphen=raw.FPDFText_IsHyphen(text_page, i) == 1,
            map_error=raw.FPDFText_HasUnicodeMapError(text_page, i) == 1,
        )
        box = _box(text_page, i, frame)
        clipped = False
        obj = raw.FPDFText_GetTextObject(text_page, i)
        if obj:
            key = _address(obj)
            if key not in clips:
                clips[key] = _clip(obj, frame)
            x, y = box.center
            clipped = any(not in_polygon(polygon, x, y) for polygon in clips[key])
        out.append(InkChar(i, char, box, kind, clipped))
    return tuple(out)


def _page(pdf: pdfium.PdfDocument, index: int) -> InkPage:
    try:
        page = pdf[index]
    except pdfium.PdfiumError as exc:
        return InkPage(index + 1, 0.0, 0.0, error=str(exc) or "PDFium cannot load the page")
    try:
        bounds = raw.FS_RECTF()
        raw.FPDF_GetPageBoundingBox(page.raw, bounds)
        frame = _Frame(bounds.left, bounds.top)
        objects = list(_objects(page.raw, frame))
        clips = {
            _address(o.handle): o.enclosing + _clip(o.handle, frame)
            for o in objects
            if o.kind == raw.FPDF_PAGEOBJ_TEXT
        }
        text_page = page.get_textpage()
        try:
            chars = _chars(text_page.raw, frame, clips)
        finally:
            text_page.close()
        paths = (o for o in objects if o.kind == raw.FPDF_PAGEOBJ_PATH)
        rules = extract_rules(_ink_path(o.handle, o.matrix, frame) for o in paths)
        return InkPage(
            index + 1,
            bounds.right - bounds.left,
            bounds.top - bounds.bottom,
            chars=chars,
            rules=rules,
        )
    finally:
        page.close()


def read_ink(data: bytes, password: str | None) -> Ink:
    """Every page of the PDF as PDFium reads it (spec 10 sections 1.1-1.5).

    Raises:
        PasswordRequired: the PDF needs a password and none was given.
        WrongPassword: the password does not open the PDF.
    """
    versions = {"pypdfium2": version.PYPDFIUM_INFO.version, "pdfium": version.PDFIUM_INFO.version}
    try:
        pdf = pdfium.PdfDocument(data, password=password)
    except pdfium.PdfiumError as exc:
        if exc.err_code == raw.FPDF_ERR_PASSWORD:
            if password is None:
                msg = "the PDF needs a password to verify it"
                raise PasswordRequired(msg) from exc
            msg = "the password does not open the PDF"
            raise WrongPassword(msg) from exc
        return Ink(pages=(), error=str(exc) or "PDFium cannot open the PDF", **versions)
    try:
        return Ink(pages=tuple(_page(pdf, i) for i in range(len(pdf))), **versions)
    finally:
        pdf.close()
