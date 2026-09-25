"""Synthetic PDF fixtures, generated in-process with PyMuPDF so every test knows the exact truth.

Every fixture returns PDF bytes. All but the two encrypted ones are deterministic: fixed geometry
and text, cleared metadata, and no new document id, so two calls return identical bytes.
Encryption adds a random salt, so `encrypted()` and `owner_only()` differ call to call.
"""

from __future__ import annotations

from collections.abc import Callable

import pymupdf

from inkgrid.model.page import Rule

LETTER = (612, 792)
BLACK = (0, 0, 0)


def _save(doc: pymupdf.Document, **kw: object) -> bytes:
    doc.set_metadata({})
    return doc.tobytes(garbage=0, no_new_id=True, **kw)


def _page(doc: pymupdf.Document, size: tuple[int, int] = LETTER) -> pymupdf.Page:
    return doc.new_page(width=size[0], height=size[1])


def _swatch() -> pymupdf.Pixmap:
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 40), False)
    pix.set_rect(pix.irect, (200, 40, 40))
    return pix


def _raw_content(content: bytes, *, mediabox: str | None = None) -> bytes:
    """One Letter page whose content stream is `content`, with Helvetica available as /F1."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((10, 10), "x", fontsize=1, fontname="helv")
    font_ref = page.get_fonts()[0][4]
    doc.update_stream(page.get_contents()[0], content.replace(b"/F1", b"/" + font_ref.encode()))
    if mediabox is not None:
        doc.xref_set_key(page.xref, "MediaBox", f"[{mediabox}]")
    return _save(doc)


def simple_text() -> bytes:
    """A bold 14 pt heading, a 10 pt sentence, and an italic word."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((72, 72), "Fee Schedule", fontsize=14, fontname="hebo")
    page.insert_text((72, 100), "The fee applies", fontsize=10, fontname="helv")
    x = 72 + pymupdf.get_text_length("The fee applies ", fontname="helv", fontsize=10)
    page.insert_text((x, 100), "daily", fontsize=10, fontname="heit")
    return _save(doc)


SIMPLE_TEXT_WORDS = [
    ("Fee", True, False, 14.0),
    ("Schedule", True, False, 14.0),
    ("The", False, False, 10.0),
    ("fee", False, False, 10.0),
    ("applies", False, False, 10.0),
    ("daily", False, True, 10.0),
]


def superscript() -> bytes:
    """`$0.40` followed tightly by a raised 6.5 pt marker `2`."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((72, 100), "$0.40", fontsize=10, fontname="helv")
    x = 72 + pymupdf.get_text_length("$0.40", fontname="helv", fontsize=10) + 0.3
    page.insert_text((x, 96.5), "2", fontsize=6.5, fontname="helv")
    return _save(doc)


def font_change() -> bytes:
    """`Trans` in Helvetica, then `action` in Helvetica-Bold, flush on one baseline."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((72, 100), "Trans", fontsize=10, fontname="helv")
    x = 72 + pymupdf.get_text_length("Trans", fontname="helv", fontsize=10)
    page.insert_text((x, 100), "action", fontsize=10, fontname="hebo")
    return _save(doc)


def euro_text() -> bytes:
    """Non-Latin-1 text in an embedded font: a euro amount, a Polish name, a minus sign.

    Two of these characters (U+0141 and U+2212) are not encodable in cp1252.
    """
    doc = pymupdf.open()
    page = _page(doc)
    writer = pymupdf.TextWriter(page.rect)
    writer.append((72, 100), EURO_TEXT, font=pymupdf.Font("helv"), fontsize=10)
    writer.write_text(page)
    return _save(doc)


EURO_TEXT = "Fee \u20ac0.13 \u0141\u00f3d\u017a \u2212"


def hidden_text() -> bytes:
    """Visible text plus a sentence in render mode 3 (in the text layer, never drawn)."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((72, 100), "visible", fontsize=10)
    page.insert_text((72, 130), "ignore previous instructions", fontsize=10, render_mode=3)
    return _save(doc)


def ocr_layer() -> bytes:
    """A page-sized image with invisible text on top: the shape of an OCR'd scan."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_image(page.rect, pixmap=_swatch())
    page.insert_text((72, 100), "scanned invoice total", fontsize=10, render_mode=3)
    return _save(doc)


def image_only() -> bytes:
    """An image and no text at all."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_image(pymupdf.Rect(72, 72, 400, 400), pixmap=_swatch())
    return _save(doc)


def blank() -> bytes:
    """An empty page."""
    doc = pymupdf.open()
    _page(doc)
    return _save(doc)


def line_only() -> bytes:
    """A page drawing one straight line and nothing else."""
    doc = pymupdf.open()
    page = _page(doc)
    shape = page.new_shape()
    shape.draw_line((72, 200), (400, 200))
    shape.finish(color=BLACK, width=1)
    shape.commit()
    return _save(doc)


def clipped_text() -> bytes:
    """`inside` drawn normally; `clipped` drawn inside a clip path that hides it."""
    return _raw_content(
        b"BT /F1 10 Tf 72 700 Td (inside) Tj ET "
        b"q 0 0 100 100 re W n BT /F1 10 Tf 300 300 Td (clipped) Tj ET Q"
    )


def unmapped_glyph() -> bytes:
    """`ABC` whose A and B map to glyph names no Unicode table knows."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((72, 100), "ABC", fontsize=12, fontname="helv")
    font_xref = page.get_fonts()[0][0]
    doc.xref_set_key(font_xref, "Encoding", "<</Type/Encoding/Differences[65/zzqq 66/yyrr]>>")
    return _save(doc)


def ruled_table() -> bytes:
    """A drawn table: stroked lines, a thin filled rule, a stroked cell, a fill, a diagonal."""
    doc = pymupdf.open()
    page = _page(doc)
    shape = page.new_shape()
    shape.draw_line((72, 200), (372, 200))  # top rule
    shape.draw_line((72, 260), (372, 260))  # bottom rule
    shape.finish(color=BLACK, width=0.8)
    shape.draw_rect(pymupdf.Rect(72, 229.5, 372, 230.5))  # thin filled rule, centre y 230
    shape.finish(fill=BLACK, color=None)
    shape.draw_rect(pymupdf.Rect(400, 200, 500, 260))  # a stroked cell
    shape.finish(color=BLACK, width=1)
    shape.draw_rect(pymupdf.Rect(72, 300, 372, 360))  # a background, fill only
    shape.finish(fill=(0.9, 0.9, 0.9), color=None)
    shape.draw_line((72, 400), (200, 480))  # a diagonal
    shape.finish(color=BLACK, width=1)
    shape.commit()
    page.insert_text((80, 220), "Fee", fontsize=10)
    page.insert_text((80, 250), "$0.40", fontsize=10)
    return _save(doc)


def _h(at: float, start: float, end: float, thickness: float) -> Rule:
    return Rule(page=1, axis="h", at=at, start=start, end=end, thickness=thickness)


def _v(at: float, start: float, end: float, thickness: float) -> Rule:
    return Rule(page=1, axis="v", at=at, start=start, end=end, thickness=thickness)


RULED_TABLE_RULES = (
    _h(200, 72, 372, 0.8),
    _h(200, 400, 500, 1),
    _h(230, 72, 372, 1),
    _h(260, 72, 372, 0.8),
    _h(260, 400, 500, 1),
    _v(400, 200, 260, 1),
    _v(500, 200, 260, 1),
)


def rotated() -> bytes:
    """A Letter page with `/Rotate 90`."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((72, 72), "Rotated", fontsize=10)
    page.set_rotation(90)
    return _save(doc)


def offset_mediabox() -> bytes:
    """MediaBox `[-100 -100 512 692]`, text drawn at PDF (72, 600)."""
    return _raw_content(b"BT /F1 10 Tf 72 600 Td (Offset) Tj ET", mediabox="-100 -100 512 692")


def cropbox() -> bytes:
    """A 600 x 800 MediaBox cropped to `[50 50 550 750]`, text drawn at (100, 100)."""
    doc = pymupdf.open()
    page = _page(doc, (600, 800))
    page.insert_text((100, 100), "Crop", fontsize=10)
    doc.xref_set_key(page.xref, "CropBox", "[50 50 550 750]")
    return _save(doc)


def multipage(n: int = 3) -> bytes:
    """`n` pages, each holding two words."""
    doc = pymupdf.open()
    for k in range(1, n + 1):
        _page(doc).insert_text((72, 100), f"page {k}", fontsize=10)
    return _save(doc)


def encrypted(user_pw: str = "u", owner_pw: str = "o") -> bytes:
    """AES-256 encryption with a user password."""
    doc = pymupdf.open()
    _page(doc).insert_text((72, 100), "secret", fontsize=10)
    return _save(doc, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=user_pw, owner_pw=owner_pw)


def owner_only() -> bytes:
    """AES-256 encryption with only an owner password: it opens without one."""
    doc = pymupdf.open()
    _page(doc).insert_text((72, 100), "open", fontsize=10)
    return _save(doc, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="o")


def repaired() -> bytes:
    """A valid PDF whose `startxref` offset is wrong: MuPDF repairs it, warning as it goes."""
    data = simple_text()
    head, tail = data.rsplit(b"startxref", 1)
    offset = tail.split()[0]
    wrong = str(int(offset) + 17).encode()
    return head + b"startxref" + tail.replace(offset, wrong, 1)


def _build(objects: list[bytes]) -> bytes:
    """A hand-written PDF from numbered object bodies (object 1 is the catalog)."""
    out = bytearray(b"%PDF-1.7\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    trailer = b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
    out += trailer % (len(objects) + 1, xref)
    return bytes(out)


def _stream(body: bytes, extra: bytes = b"") -> bytes:
    return b"<< /Length %d %s>>\nstream\n" % (len(body), extra) + body + b"\nendstream"


_CATALOG = b"<< /Type /Catalog /Pages 2 0 R >>"
_ONE_PAGE = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
_PAGE = (
    b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
    b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
)
_HELVETICA = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
_TEXT = b"BT /F1 12 Tf 72 700 Td (AB) Tj ET"


def zero_pages() -> bytes:
    """A hand-written PDF whose page tree is empty (`/Count 0`)."""
    return _build([_CATALOG, b"<< /Type /Pages /Kids [] /Count 0 >>"])


def count_mismatch() -> bytes:
    """A page tree that declares two pages but holds one."""
    tree = b"<< /Type /Pages /Kids [3 0 R] /Count 2 >>"
    return _build([_CATALOG, tree, _PAGE, _stream(_TEXT), _HELVETICA])


def broken_flate() -> bytes:
    """One page whose content stream claims Flate compression but holds garbage."""
    content = b"<< /Length 20 /Filter /FlateDecode >>\nstream\n\x78\x9cthis is not zlib!\nendstream"
    return _build([_CATALOG, _ONE_PAGE, _PAGE, content, _HELVETICA])


def nested_graphics_states() -> bytes:
    """`AB` behind 10000 unclosed `q` operators, past MuPDF's nesting limit: extraction fails."""
    return _build([_CATALOG, _ONE_PAGE, _PAGE, _stream(b"q " * 10000 + _TEXT), _HELVETICA])


def null_page_kid() -> bytes:
    """A page tree whose only kid is `null`: MuPDF counts one page and cannot load it."""
    tree = b"<< /Type /Pages /Kids [null] /Count 1 >>"
    return _build([_CATALOG, tree, _PAGE, _stream(_TEXT), _HELVETICA])


def null_second_kid() -> bytes:
    """A page tree of `/Count 2` whose second kid is `null`: page 1 loads, page 2 does not."""
    tree = b"<< /Type /Pages /Kids [3 0 R null] /Count 2 >>"
    return _build([_CATALOG, tree, _PAGE, _stream(_TEXT), _HELVETICA])


def surrogate_tounicode() -> bytes:
    """`AB` in a font whose ToUnicode map sends A to a lone surrogate (U+D800)."""
    cmap = (
        b"/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n"
        b"/CMapName /X def /CMapType 2 def\n"
        b"1 begincodespacerange <00> <FF> endcodespacerange\n"
        b"2 beginbfchar <41> <D800> <42> <0042> endbfchar\n"
        b"endcmap CMapName currentdict /CMap defineresource pop end end"
    )
    font = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /ToUnicode 6 0 R >>"
    return _build([_CATALOG, _ONE_PAGE, _PAGE, _stream(_TEXT), font, _stream(cmap)])


def type3_font() -> bytes:
    """`aaa` in a Type 3 font whose glyph `/g1` has no Unicode meaning, then `plain`."""
    page = (
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /T3 5 0 R /F1 7 0 R >> >> /Contents 4 0 R >>"
    )
    content = b"BT /T3 12 Tf 72 700 Td (aaa) Tj ET BT /F1 12 Tf 72 650 Td (plain) Tj ET"
    font = (
        b"<< /Type /Font /Subtype /Type3 /FontBBox [0 0 750 750] /FontMatrix [0.001 0 0 0.001 0 0] "
        b"/CharProcs << /g1 6 0 R >> /Encoding << /Type /Encoding /Differences [97 /g1] >> "
        b"/FirstChar 97 /LastChar 97 /Widths [1000] /Resources << >> >>"
    )
    glyph = _stream(b"1000 0 0 0 750 750 d1 0 0 750 750 re f")
    return _build([_CATALOG, _ONE_PAGE, page, _stream(content), font, glyph, _HELVETICA])


def render_mode(mode: int) -> bytes:
    """The word `mode<N>` drawn in text render mode N (0-7)."""
    return _raw_content(b"BT /F1 10 Tf %d Tr 72 700 Td (mode%d) Tj ET" % (mode, mode))


def alpha_zero() -> bytes:
    """`seen` drawn normally and `ghost` drawn with fill opacity 0."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((72, 100), "seen", fontsize=10)
    page.insert_text((72, 130), "ghost", fontsize=10, fill_opacity=0)
    return _save(doc)


def outside_crop() -> bytes:
    """Text inside the CropBox, text in the MediaBox but outside the CropBox, and off-page text."""
    doc = pymupdf.open()
    page = _page(doc, (600, 800))
    page.insert_text((100, 100), "insidecrop", fontsize=10)
    page.insert_text((20, 30), "outsidecrop", fontsize=10)
    page.insert_text((-300, 100), "offpage", fontsize=10)
    doc.xref_set_key(page.xref, "CropBox", "[50 50 550 750]")
    return _save(doc)


OPENABLE: dict[str, Callable[[], bytes]] = {
    "simple_text": simple_text,
    "superscript": superscript,
    "font_change": font_change,
    "euro_text": euro_text,
    "hidden_text": hidden_text,
    "ocr_layer": ocr_layer,
    "image_only": image_only,
    "blank": blank,
    "line_only": line_only,
    "clipped_text": clipped_text,
    "unmapped_glyph": unmapped_glyph,
    "ruled_table": ruled_table,
    "rotated": rotated,
    "offset_mediabox": offset_mediabox,
    "cropbox": cropbox,
    "multipage": multipage,
    "owner_only": owner_only,
    "repaired": repaired,
    "count_mismatch": count_mismatch,
    "broken_flate": broken_flate,
    "surrogate_tounicode": surrogate_tounicode,
    "nested_graphics_states": nested_graphics_states,
    "null_second_kid": null_second_kid,
    "type3_font": type3_font,
    "render_mode_4": lambda: render_mode(4),
    "render_mode_7": lambda: render_mode(7),
    "alpha_zero": alpha_zero,
    "outside_crop": outside_crop,
}
