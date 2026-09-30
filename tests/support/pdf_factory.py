"""Synthetic PDF fixtures, generated in-process with PyMuPDF so every test knows the exact truth.

Every fixture returns PDF bytes. All but the two encrypted ones are deterministic: fixed geometry
and text, cleared metadata, and no new document id, so two calls return identical bytes.
Encryption adds a random salt, so `encrypted()` and `owner_only()` differ call to call.
"""

from __future__ import annotations

from collections.abc import Callable
from itertools import pairwise

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


def overprinted_banner() -> bytes:
    """A banner drawn twice at the same place, another word drawn between (competition us-020)."""
    return _raw_content(
        b"BT /F1 10 Tf 72 700 Td (HIGHLIGHTS FROM) Tj ET "
        b"BT /F1 10 Tf 72 600 Td (between) Tj ET "
        b"BT /F1 10 Tf 72 700 Td (HIGHLIGHTS FROM) Tj ET"
    )


def stroked_then_filled() -> bytes:
    """`PRESS` stroked, then filled at the same origin: `0 TL`, so `T*` stays (olmOCR c8cdd4)."""
    return _raw_content(b"BT /F1 24 Tf 0 TL 1 Tr 72 700 Td (PRESS) Tj 0 Tr T* (PRESS) Tj ET")


def wordart_shadow() -> bytes:
    """A title drawn five times within 0.03 em, as WordArt's shadow is (olmOCR f86995).

    The text matrix scales a 1 pt font by 30, so PDFium's own copy test, which uses the 1 pt size,
    keeps some of the copies; MuPDF returns all five.
    """
    title = b"(Y a h o o !) Tj "
    moves = (b"-0.03 0 TD ", b"0.03 0.03 TD ", b"-0.03 0 TD ", b"0.015 -0.015 TD ")
    body = b"BT /F1 1 Tf 30 0 0 30 101.13 473.63 Tm " + title + b"".join(m + title for m in moves)
    return _raw_content(body + b"ET")


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


RULED_GRID_CELLS: dict[str, tuple[float, float, float, float]] = {
    "Fee": (72, 100, 172, 120),
    "Rate": (172, 100, 372, 120),  # spans columns 1-2
    "Equity": (72, 120, 172, 160),  # spans rows 1-2
    "0.10": (172, 120, 272, 140),
    "0.20": (272, 120, 372, 140),
    "0.30": (172, 140, 272, 160),
    "0.40": (272, 140, 372, 160),
    "Bonds": (72, 160, 172, 180),
    "0.50": (172, 160, 272, 180),
    "0.60": (272, 160, 372, 180),
}
"""Each cell of `ruled_grid` by the one word it holds, as drawn (unrotated page coordinates)."""


def _draw_grid(page: pymupdf.Page, cells: dict[str, tuple[float, float, float, float]]) -> None:
    """Stroke every cell's outline and centre its word in it, at 9 pt."""
    shape = page.new_shape()
    for x0, y0, x1, y1 in cells.values():
        shape.draw_rect(pymupdf.Rect(x0, y0, x1, y1))
    shape.finish(color=BLACK, width=0.8)
    shape.commit()
    for text, (x0, y0, x1, y1) in cells.items():
        width = pymupdf.get_text_length(text, fontsize=9)
        page.insert_text(((x0 + x1 - width) / 2, (y0 + y1) / 2 + 3), text, fontsize=9)


def ruled_grid(
    rotation: int = 0,
    mediabox: tuple[float, float, float, float] | None = None,
    cropbox: tuple[float, float, float, float] | None = None,
) -> bytes:
    """A 4 x 3 ruled table: `Rate` spans columns 1-2 of the header, `Equity` rows 1-2."""
    doc = pymupdf.open()
    page = _page(doc)
    _draw_grid(page, RULED_GRID_CELLS)
    if mediabox is not None:
        page.set_mediabox(pymupdf.Rect(*mediabox))
    if cropbox is not None:
        page.set_cropbox(pymupdf.Rect(*cropbox))
    page.set_rotation(rotation)
    return _save(doc)


def formed_rules() -> bytes:
    """`ruled_grid` placed at half scale in (100, 100, 406, 496) as a Form XObject."""
    source = pymupdf.open(stream=ruled_grid(), filetype="pdf")
    doc = pymupdf.open()
    _page(doc).show_pdf_page(pymupdf.Rect(100, 100, 406, 496), source, 0)
    return _save(doc)


def ruled_grid_pages(n: int = 3) -> bytes:
    """`ruled_grid` on each of `n` pages."""
    doc = pymupdf.open()
    for _ in range(n):
        _draw_grid(_page(doc), RULED_GRID_CELLS)
    return _save(doc)


TABLE_BEFORE = ["The fees below apply to every order", "executed on the book this month."]
TABLE_AFTER = ["Rebates are credited on the invoice", "for the month after the trading."]


def table_between_paragraphs() -> bytes:
    """A paragraph, `ruled_grid`'s table, and a paragraph, top to bottom."""
    doc = pymupdf.open()
    page = _page(doc)
    for i, text in enumerate(TABLE_BEFORE):
        page.insert_text((72, 60 + 12 * i), text, fontsize=10)
    _draw_grid(page, RULED_GRID_CELLS)
    for i, text in enumerate(TABLE_AFTER):
        page.insert_text((72, 220 + 12 * i), text, fontsize=10)
    return _save(doc)


CONTINUED_HEAD = {"Fee": (72, 680, 172, 700), "Rate": (172, 680, 272, 700)}
CONTINUED_PAGE1 = {
    **CONTINUED_HEAD,
    "Band1": (72, 700, 172, 720),
    "$0.50": (172, 700, 272, 720),
    "Band2": (72, 720, 172, 740),
    "$0.60": (172, 720, 272, 740),
}
CONTINUED_PAGE2 = {
    "Band3": (72, 72, 172, 92),
    "$0.70": (172, 72, 272, 92),
    "Band4": (72, 92, 172, 112),
    "$0.80": (172, 92, 272, 112),
}


def continued_table() -> bytes:
    """A ruled `Fee | Rate` table at page 1's foot, continued headerless at page 2's top."""
    doc = pymupdf.open()
    page = _page(doc)
    for i, text in enumerate(TABLE_BEFORE):
        page.insert_text((72, 60 + 12 * i), text, fontsize=10)
    _draw_grid(page, CONTINUED_PAGE1)
    _draw_grid(_page(doc), CONTINUED_PAGE2)
    return _save(doc)


def headerless_table() -> bytes:
    """One ruled table whose first row holds values: no header, and nothing it continues."""
    doc = pymupdf.open()
    _draw_grid(_page(doc), CONTINUED_PAGE2)
    return _save(doc)


CONTINUED_PROSE = [
    "Members pay a monthly fee for each trading port they order,",
    "and a transaction fee for each order they execute. For orders",
    "executed in the closing auction the fee is charged per",
]


def continued_paragraph() -> bytes:
    """A sentence broken by the page: `... the fee is charged per` / `executed order.`"""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((72, 60), "Transaction fees", fontsize=14, fontname="hebo")
    for i, text in enumerate(CONTINUED_PROSE):
        page.insert_text((72, 716 + 12 * i), text, fontsize=10)
    _page(doc).insert_text((72, 80), "executed order.", fontsize=10)
    return _save(doc)


FOOTNOTED_CELLS = {
    "Fee": (72, 120, 172, 140),
    "Rate": (172, 120, 272, 140),
    "Trade": (72, 140, 172, 160),
    "$0.50": (172, 140, 272, 160),
}


def footnoted_table() -> bytes:
    """A ruled table whose `$0.50` carries a raised `1`, and a 7 pt note `1 Applies ...` below."""
    doc = pymupdf.open()
    page = _page(doc)
    for i, text in enumerate(TABLE_BEFORE):
        page.insert_text((72, 60 + 12 * i), text, fontsize=10)
    _draw_grid(page, FOOTNOTED_CELLS)
    x = (172 + 272 + pymupdf.get_text_length("$0.50", fontsize=9)) / 2 + 0.3
    page.insert_text((x, 150.5), "1", fontsize=6)
    page.insert_text((72, 190), "1 Applies to every trade on the order book.", fontsize=7)
    return _save(doc)


def glued_notes() -> bytes:
    """A call `applies^1`, and PHLX's glued note: a raised 7 pt `1` flush against 9 pt text."""
    doc = pymupdf.open()
    page = _page(doc)
    for i, text in enumerate(CONTINUED_PROSE):  # ordinary leading, so the note's gap is a break
        page.insert_text((72, 64 + 11 * i), text, fontsize=9)
    lead = "The index surcharge applies"
    page.insert_text((72, 100), lead, fontsize=9)
    x = 72 + pymupdf.get_text_length(lead, fontsize=9) + 0.3
    page.insert_text((x, 96.5), "1", fontsize=6)
    page.insert_text((x + 4, 100), "to options on NDX and NDXP.", fontsize=9)
    page.insert_text((72, 140), "1", fontsize=7.31)
    width = pymupdf.get_text_length("1", fontsize=7.31)
    note = "A surcharge of $0.25 per contract will be assessed on each side."
    page.insert_text((72 + width, 143.47), note, fontsize=8.78)
    return _save(doc)


BOXED_PARAGRAPH = [
    "Members must notify the exchange",
    "in writing before they change",
    "their clearing arrangements.",
]


def boxed_paragraph() -> bytes:
    """A paragraph inside a drawn box: a 1 x 1 grid that is not a table."""
    doc = pymupdf.open()
    page = _page(doc)
    shape = page.new_shape()
    shape.draw_rect(pymupdf.Rect(60, 80, 360, 140))
    shape.finish(color=BLACK, width=0.8)
    shape.commit()
    for i, text in enumerate(BOXED_PARAGRAPH):
        page.insert_text((72, 100 + 12 * i), text, fontsize=10)
    return _save(doc)


RULED_COLUMNS_LEFT = [f"Left column prose line {i} with words." for i in range(12)]
RULED_COLUMNS_RIGHT = [f"Right column prose line {i} with text." for i in range(12)]


def ruled_columns() -> bytes:
    """A page frame with a rule under its header and a rule between two columns of prose."""
    doc = pymupdf.open()
    page = _page(doc)
    shape = page.new_shape()
    shape.draw_rect(pymupdf.Rect(40, 40, 572, 752))
    shape.draw_line((40, 70), (572, 70))
    shape.draw_line((306, 70), (306, 752))
    shape.finish(color=BLACK, width=0.6)
    shape.commit()
    page.insert_text((50, 60), "Official Bulletin of Fees", fontsize=9)
    for i, (left, right) in enumerate(zip(RULED_COLUMNS_LEFT, RULED_COLUMNS_RIGHT, strict=True)):
        page.insert_text((50, 100 + 13 * i), left, fontsize=10)
        page.insert_text((316, 100 + 13 * i), right, fontsize=10)
    return _save(doc)


RIGHT_COLUMN_LEFT = [
    [f"Left paragraph {n} line {i} of running text." for i in range(4)] for n in range(3)
]
RIGHT_COLUMN_RIGHT = [
    [f"Right paragraph {n} line {i} of text here." for i in range(3)] for n in range(2)
]
RIGHT_COLUMN_TABLE = {
    "Fee": (330, 200, 440, 220),
    "Rate": (440, 200, 550, 220),
    "Order": (330, 220, 440, 240),
    "0.10": (440, 220, 550, 240),
}


def table_in_right_column() -> bytes:
    """Two prose columns; the right one holds a paragraph, a ruled table, then a paragraph."""
    doc = pymupdf.open()
    page = _page(doc)
    for n, paragraph in enumerate(RIGHT_COLUMN_LEFT):
        for i, text in enumerate(paragraph):
            page.insert_text((72, 100 + 80 * n + 12 * i), text, fontsize=10)
    for n, paragraph in enumerate(RIGHT_COLUMN_RIGHT):
        for i, text in enumerate(paragraph):
            page.insert_text((330, 100 + 180 * n + 12 * i), text, fontsize=10)
    _draw_grid(page, RIGHT_COLUMN_TABLE)
    return _save(doc)


LABEL = "Sensitivity: C1 Public"


def labelled_page() -> bytes:
    """3 pages, each with a paragraph and, at its foot, a 3 x 3 box holding a furniture label."""
    doc = pymupdf.open()
    for n in range(3):
        page = _page(doc)
        word = ("alpha", "bravo", "charlie")[n]
        page.insert_text((72, 100), f"The {word} schedule lists every fee.", fontsize=10)
        shape = page.new_shape()
        xs, ys = (0, 7, 134, 595), (750, 755, 772, 781)
        for x0, x1 in pairwise(xs):
            for y0, y1 in pairwise(ys):
                shape.draw_rect(pymupdf.Rect(x0, y0, x1, y1))
        shape.finish(color=BLACK, width=0.5)
        shape.commit()
        page.insert_text((12, 767), LABEL, fontsize=7)
    return _save(doc)


RULED_LANDSCAPE_CELLS: dict[str, tuple[float, float, float, float]] = {
    "Fee": (72, 100, 172, 120),
    "Rate": (172, 100, 272, 120),
    "Cap": (272, 100, 372, 120),
    "Equity": (72, 120, 172, 140),
    "0.10": (172, 120, 272, 140),
    "0.20": (272, 120, 372, 140),
}
"""The cells of `ruled_landscape` as shown on screen (the /Rotate 90 frame, 792 x 612)."""


def ruled_landscape(cropbox: tuple[float, float, float, float] | None = None) -> bytes:
    """A 2 x 3 ruled table upright on screen on a `/Rotate 90` page."""
    doc = pymupdf.open()
    page = _page(doc)
    height = page.rect.height
    shape = page.new_shape()
    for x0, y0, x1, y1 in RULED_LANDSCAPE_CELLS.values():
        # Screen (X, Y) shows the unrotated point (Y, height - X).
        shape.draw_rect(pymupdf.Rect(y0, height - x1, y1, height - x0))
    shape.finish(color=BLACK, width=0.8)
    shape.commit()
    for text, (x0, y0, x1, y1) in RULED_LANDSCAPE_CELLS.items():
        width = pymupdf.get_text_length(text, fontsize=9)
        start_x, baseline = (x0 + x1 - width) / 2, (y0 + y1) / 2 + 3
        page.insert_text((baseline, height - start_x), text, fontsize=9, rotate=90)
    if cropbox is not None:
        page.set_cropbox(pymupdf.Rect(*cropbox))
    page.set_rotation(90)
    return _save(doc)


def ruled_encrypted(user_pw: str | None) -> bytes:
    """`ruled_grid`, AES-256 encrypted; with no user password it opens without one."""
    doc = pymupdf.open(stream=ruled_grid(), filetype="pdf")
    return doc.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw=user_pw or ""
    )


UNRULED_HEADER = ["Standard tariff", "Floor", "Scale", "Cap"]
UNRULED_ROWS = [
    ["a) Poster", "-", "1.00 bp", "-"],
    ["b) Aggressor", "CHF 0.50", "0.55 bp", "-"],
    ["c) Auction", "CHF 0.50", "0.75 bp", "-"],
]
UNRULED_ENDS = (285.0, 345.0, 404.0)  # right edges of the value columns
UNRULED_INTRO = [
    "The ad valorem fee differs depending on the rate band, according to the",
    "following table. It is charged on the value of every trade executed on the",
    "order book, and it is invoiced monthly to the member that entered the order.",
]
UNRULED_COMMITMENT = ["Commitment", "No commitment required"]


def _unruled_rows(
    page: pymupdf.Page, y: float, *, x0: float = 72.0, rotate: int = 0, height: float = 792.0
) -> float:
    """SIX's layout: a bold header, value rows 12 pt apart, and a commitment row; the next free y.

    With `rotate=90` each point (x, y) is drawn at the unrotated (y, height - x), so the table
    shows upright on a /Rotate 90 page.
    """

    def put(text: str, x: float, at: float, font: str) -> None:
        if rotate:
            page.insert_text((at, height - x), text, fontsize=9, fontname=font, rotate=90)
        else:
            page.insert_text((x, at), text, fontsize=9, fontname=font)

    def row(cells: list[str], at: float, font: str) -> None:
        put(cells[0], x0, at, font)
        for text, end in zip(cells[1:], UNRULED_ENDS, strict=True):
            put(
                text,
                x0 - 72 + end - pymupdf.get_text_length(text, fontname=font, fontsize=9),
                at,
                font,
            )

    row(UNRULED_HEADER, y, "hebo")
    for n, cells in enumerate(UNRULED_ROWS, 1):
        row(cells, y + 12 * n, "helv")
    at = y + 12 * (len(UNRULED_ROWS) + 1)
    put(UNRULED_COMMITMENT[0], x0, at, "helv")
    text = UNRULED_COMMITMENT[1]
    put(text, x0 - 72 + UNRULED_ENDS[-1] - pymupdf.get_text_length(text, fontsize=9), at, "helv")
    return at + 12


def unruled_table() -> bytes:
    """A heading, an intro paragraph, a SIX-style unruled table, then a heading."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((72, 80), "1.2 Ad valorem fee", fontsize=10, fontname="hebo")
    for i, text in enumerate(UNRULED_INTRO):
        page.insert_text((72, 98 + 12 * i), text, fontsize=10)
    after = _unruled_rows(page, 140)
    page.insert_text((72, after + 20), "1.3 Retail orders", fontsize=10, fontname="hebo")
    return _save(doc)


CENTRED_ROWS = [
    (["Standard trading"], "0.45bp"),
    (["Value of all nominated client orders that do", "not qualify for the scheme"], "0.30bp"),
    (["Passive orders"], "0.00bp"),
    (["Aggressive orders"], "0.15bp"),
]
CENTRED_BANNER = "Liquidity Provider Scheme"


def centred_values() -> bytes:
    """LSE's layout: two-line labels with their value centred beside them, and a bold banner.

    The label lines are 10.9 pt apart and the value sits 5.45 pt below the first, as LSE sets them.
    """
    doc = pymupdf.open()
    page = _page(doc)
    y = 100.0
    for index, (label, value) in enumerate(CENTRED_ROWS):
        if index == 2:
            page.insert_text((76, y), CENTRED_BANNER, fontsize=9, fontname="hebo")
            y += 19.3
        for i, text in enumerate(label):
            page.insert_text((76, y + 10.9 * i), text, fontsize=9)
        mid = y + 5.45 * (len(label) - 1)
        page.insert_text((522 - pymupdf.get_text_length(value, fontsize=9), mid), value, fontsize=9)
        y += 10.9 * (len(label) - 1) + 19.3
    return _save(doc)


def ruled_and_unruled() -> bytes:
    """`ruled_grid`'s table, and below it an unruled SIX-style table."""
    doc = pymupdf.open()
    page = _page(doc)
    _draw_grid(page, RULED_GRID_CELLS)
    _unruled_rows(page, 320)
    return _save(doc)


def unruled_landscape() -> bytes:
    """The unruled table of `unruled_table`, upright on a /Rotate 90 page."""
    doc = pymupdf.open()
    page = _page(doc)
    _unruled_rows(page, 116, rotate=90, height=page.rect.height)
    page.set_rotation(90)
    return _save(doc)


CENTRED_SPAN_ROWS = [
    ("Trading", "CHF 0.10", None),
    ("Post trade", "CHF 0.20", None),
    ("Drop copy", "CHF 0.30", None),
    ("Reporting", "CHF 0.40", "CHF 5.00"),
]


def centred_span() -> bytes:
    """9 pt rows at a 12 pt pitch, with `Free` centred beside rows 1 and 2 (LSE p10's pattern).

    Base-14 boxes are 1.38 em tall, so `Free` overlaps both rows enough to chain them into one line.
    """
    doc = pymupdf.open()
    page = _page(doc)

    def right(end: float, y: float, text: str, font: str = "helv") -> None:
        width = pymupdf.get_text_length(text, fontname=font, fontsize=9)
        page.insert_text((end - width, y), text, fontsize=9, fontname=font)

    page.insert_text((72, 100), "Component", fontsize=9, fontname="hebo")
    right(300, 100, "Fee", "hebo")
    right(400, 100, "Monthly fee", "hebo")
    for n, (label, fee, monthly) in enumerate(CENTRED_SPAN_ROWS, 1):
        page.insert_text((72, 100 + 12 * n), label, fontsize=9)
        right(300, 100 + 12 * n, fee)
        if monthly:
            right(400, 100 + 12 * n, monthly)
    right(400, 118, "Free")
    return _save(doc)


CHAINED_EDGE = [
    ("n/a", 356.1, 658.96, 10),
    ("1", 370.5, 659.76, 6),
    ("$5,000", 369.42, 663.8, 10),
    ("monthly charge", 60.0, 699.44, 10),
    ("$5,000", 339.42, 689.24, 10),
    ("12", 388.88, 690.68, 10),
]
"""A review's minimised crash: `$5,000` set 4.85 pt under `n/a` and starting before it ends."""


def chained_edge() -> bytes:
    """Words whose lines chain, so a cell's widest word is not its last (spec 07 CG6)."""
    doc = pymupdf.open()
    page = _page(doc)
    for text, x, top, size in CHAINED_EDGE:
        # MuPDF reports a base-14 Helvetica box 1.075 em above the baseline.
        page.insert_text((x, top + 1.075 * size), text, fontsize=size)
    return _save(doc)


LANDSCAPE_TITLE = "Landscape Fee Summary"
LANDSCAPE_PARAGRAPHS = [
    [
        "The exchange charges each member a",
        "monthly port fee for every order entry",
        "session it keeps open.",
    ],
    [
        "Rebates for added liquidity are credited",
        "on the invoice for the month after the",
        "trading that earned them.",
    ],
]


def _write(
    page: pymupdf.Page, x: float, y: float, text: str, *, size: float = 10, bold: bool = False
) -> float:
    """Text in an embedded Helvetica (curly quotes need it), returning where it ends."""
    font = pymupdf.Font("hebo" if bold else "helv")
    writer = pymupdf.TextWriter(page.rect)
    writer.append((x, y), text, font=font, fontsize=size)
    writer.write_text(page)
    return x + font.text_length(text, fontsize=size)


def definitions_section() -> bytes:
    """`Definitions`: quoted, bold, and hanging entries and a ruled grid; `Fees` ends it."""
    doc = pymupdf.open()
    page = _page(doc)
    _write(page, 72, 90, "Definitions", size=14, bold=True)
    _write(
        page,
        72,
        120,
        "\u201cABBO\u201d means the best bid or offer that other exchanges disseminate.",
    )
    end = _write(page, 72, 150, "Admission Fee:", bold=True)
    _write(page, end + 2.8, 150, "The fee an issuer pays for its securities to be admitted.")
    _write(page, 72, 180, "Access")
    _write(page, 190, 180, "Connection of a physical data line to the Exchange network")
    _write(page, 190, 192, "or a technical connection to the Exchange system.")
    shape = page.new_shape()
    for x0, y0, x1, y1 in ((72, 210, 192, 234), (192, 210, 522, 234), (72, 234, 192, 258)):
        shape.draw_rect(pymupdf.Rect(x0, y0, x1, y1))
    shape.draw_rect(pymupdf.Rect(192, 234, 522, 258))
    shape.finish(color=BLACK, width=0.8)
    shape.commit()
    _write(page, 76, 226, "Aggressor", size=9)
    _write(page, 196, 226, "An order that executes against a resting order.", size=9)
    _write(page, 76, 250, "bp", size=9)
    _write(page, 196, 250, "Basis points, one hundredth of a percentage point.", size=9)
    _write(page, 72, 290, "Fees", size=14, bold=True)
    _write(page, 72, 320, "\u201cFee\u201d applies to every trade on the order book.")
    return _save(doc)


def legend_grid() -> bytes:
    """A ruled table whose `EMDI` carries a raised `X2`, then a ruled `Legend` grid for it."""
    doc = pymupdf.open()
    page = _page(doc)
    shape = page.new_shape()
    table = [(72, 80, 222, 104), (222, 80, 372, 104), (72, 104, 222, 128), (222, 104, 372, 128)]
    table += [(72, 128, 222, 152), (222, 128, 372, 152)]
    legend = [(72, 200, 522, 224), (72, 224, 192, 248), (192, 224, 522, 248)]
    legend += [(72, 248, 192, 272), (192, 248, 522, 272)]
    for x0, y0, x1, y1 in table + legend:
        shape.draw_rect(pymupdf.Rect(x0, y0, x1, y1))
    shape.finish(color=BLACK, width=0.8)
    shape.commit()
    for text, x, y in (("Connection", 76, 95), ("Price", 226, 95), ("6,000", 226, 119)):
        page.insert_text((x, y), text, fontsize=9, fontname="helv")
    for text, x, y in (("EOBI", 76, 143), ("7,200", 226, 143)):
        page.insert_text((x, y), text, fontsize=9, fontname="helv")
    page.insert_text((76, 119), "EMDI", fontsize=9, fontname="helv")
    raised = 76 + pymupdf.get_text_length("EMDI", fontname="helv", fontsize=9) + 0.3
    page.insert_text((raised, 115.5), "X2", fontsize=5.5, fontname="helv")
    page.insert_text((76, 215), "Legend", fontsize=9, fontname="hebo")
    page.insert_text((76, 239), "Tier A", fontsize=9, fontname="helv")
    page.insert_text(
        (196, 239), "Metro areas of Amsterdam, Frankfurt and London", fontsize=9, fontname="helv"
    )
    page.insert_text((76, 263), "X2", fontsize=9, fontname="helv")
    page.insert_text(
        (196, 263), "Connection rebate: the monthly fees are reduced", fontsize=9, fontname="helv"
    )
    return _save(doc)


def landscape() -> bytes:
    """A `/Rotate 90` page whose bold title and two paragraphs are upright on screen."""
    doc = pymupdf.open()
    page = _page(doc)
    # rotate=90 runs the text upward (direction (0, -1)); /Rotate 90 turns it upright on screen.
    page.insert_text((80, 720), LANDSCAPE_TITLE, fontsize=14, fontname="hebo", rotate=90)
    x = 110.0
    for paragraph in LANDSCAPE_PARAGRAPHS:
        for text in paragraph:
            page.insert_text((x, 720), text, fontsize=10, rotate=90)
            x += 12
        x += 12
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


def cropbox_beyond(box: str = "-50 -50 650 850") -> bytes:
    """A 600 x 800 page whose CropBox `box` reaches past its MediaBox, `Crop` drawn at (100, 100).

    PDF 32000-1 section 14.11.2 clips such a box to the MediaBox (olmOCR 30c92c).
    """
    doc = pymupdf.open()
    page = _page(doc, (600, 800))
    page.insert_text((100, 100), "Crop", fontsize=10)
    doc.xref_set_key(page.xref, "CropBox", f"[{box}]")
    return _save(doc)


def multipage(n: int = 3) -> bytes:
    """`n` pages, each holding two words."""
    doc = pymupdf.open()
    for k in range(1, n + 1):
        _page(doc).insert_text((72, 100), f"page {k}", fontsize=10)
    return _save(doc)


TWO_COLUMN_TITLE = "Fee Schedule Overview"
TWO_COLUMN_LEFT = [
    "The exchange charges a fee",
    "for every contract executed",
    "on its order book during the",
    "regular trading session and",
    "for each order routed away",
    "to another venue on behalf",
    "of a member firm or its own",
    "customers in any product.",
]
TWO_COLUMN_RIGHT = [
    "Rebates are paid to members",
    "that add displayed liquidity",
    "in the monthly tiers shown",
    "in the table below and are",
    "credited on the invoice for",
    "the month after the trading",
    "activity that earned them",
    "under this fee schedule.",
]
TWO_COLUMN_CLOSING = (
    "Fees and rebates in this schedule take effect on the first trading day of each month."
)


def two_column() -> bytes:
    """A bold 14 pt title, two 8-line prose columns at least 24 pt apart, and a closing line."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((72, 60), TWO_COLUMN_TITLE, fontsize=14, fontname="hebo")
    left_width = max(pymupdf.get_text_length(t, fontsize=10) for t in TWO_COLUMN_LEFT)
    right_x = 72 + left_width + 24
    right_end = right_x + max(pymupdf.get_text_length(t, fontsize=10) for t in TWO_COLUMN_RIGHT)
    assert 72 + pymupdf.get_text_length(TWO_COLUMN_CLOSING, fontsize=10) > right_end
    for i, (left, right) in enumerate(zip(TWO_COLUMN_LEFT, TWO_COLUMN_RIGHT, strict=True)):
        page.insert_text((72, 100 + 12 * i), left, fontsize=10)
        page.insert_text((right_x, 100 + 12 * i), right, fontsize=10)
    page.insert_text((72, 216), TWO_COLUMN_CLOSING, fontsize=10)
    return _save(doc)


SPACED_PARAGRAPHS = (
    [
        ["The exchange charges a fee on", "every contract executed on its", "order book."],
        ["Rebates are paid to members that", "add displayed liquidity in the", "fee tiers."],
        ["Fees are invoiced monthly and are", "due within thirty days of the", "invoice date."],
    ],
    [
        ["Market makers quote both sides", "of the market in each of their", "series."],
        ["Orders routed away pay the fees", "charged by the venue that takes", "the order."],
        ["Credits appear on the statement", "for the month after the activity", "earning them."],
    ],
)
"""Each page's paragraphs; the pages differ, so no line recurs as a running header."""


def spaced_paragraphs() -> bytes:
    """Page 1: Helvetica 10/12, a blank line between paragraphs. Page 2: Times 10/12, 8 pt apart."""
    doc = pymupdf.open()
    styles = (("helv", 12), ("tiro", 8))
    for (fontname, extra), paragraphs in zip(styles, SPACED_PARAGRAPHS, strict=True):
        page = _page(doc)
        y = 100.0
        for paragraph in paragraphs:
            for text in paragraph:
                page.insert_text((72, y), text, fontsize=10, fontname=fontname)
                y += 12
            y += extra
    return _save(doc)


FURNISHED_PAGES = 5
FURNISHED_HEADER = "Acme Fee Guide"


def furnished_body(page: int) -> list[str]:
    """The paragraph on page `page` of `furnished`: its words differ from page to page."""
    word = ("alpha", "bravo", "charlie", "delta", "echo")[page - 1]
    return [f"The {word} tier charges members", f"a flat {word} fee on every", "contract executed."]


def furnished(empty_page: int | None = None) -> bytes:
    """5 pages with a running header, a `Page N of 5` footer, and a paragraph between them."""
    doc = pymupdf.open()
    for n in range(1, FURNISHED_PAGES + 1):
        page = _page(doc)
        page.insert_text((72, 50), FURNISHED_HEADER, fontsize=9)
        if n != empty_page:
            for i, text in enumerate(furnished_body(n)):
                page.insert_text((72, 300 + 12 * i), text, fontsize=10)
        page.insert_text((72, 760), f"Page {n} of {FURNISHED_PAGES}", fontsize=9)
    return _save(doc)


def furniture_only_page() -> bytes:
    """`furnished` whose page 3 holds only its header and footer."""
    return furnished(empty_page=3)


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


_FORM_TEXT = b"BT /F1 12 Tf 10 700 Td (Hidden) Tj ET BT /F1 12 Tf 350 700 Td (Shown) Tj ET"
_CLIP_RIGHT = (
    b"q 300 0 200 792 re W n /F Do Q"  # a clip over x 300-500, set before the form is drawn
)


def _form(content: bytes, inner: int | None = None, bbox: bytes = b"0 0 612 792") -> bytes:
    xobject = b"" if inner is None else b"/XObject << /F %d 0 R >> " % inner
    resources = b"/Resources << /Font << /F1 5 0 R >> %s>> " % xobject
    extra = b"/Type /XObject /Subtype /Form /BBox [%s] " % bbox + resources
    return _stream(content, extra)


def scaled_form_clipped() -> bytes:
    """`Inside Outside` in a Form XObject built as olmOCR-bench's c45171 is: a `/Matrix` scaling
    the form by 0.5, a `cm` before `Do` scaling it by 4, and a clip inside the form (x 0-94 in form
    space, 50-238 on the page after both) that cuts the run between the words. PDFium keeps a clip
    only on an object it cuts, and gives it after `/Matrix` but before the `cm`, so a clip must go
    through the form object's matrix (M5a)."""
    page = (
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> /XObject << /F 6 0 R >> >> /Contents 4 0 R >>"
    )
    content = b"q 0 0 94 300 re W n BT /F1 12 Tf 60 20 Td (Inside Outside) Tj ET Q"
    matrix = b"/Type /XObject /Subtype /Form /BBox [0 0 612 792] /Matrix [0.5 0 0 0.5 0 0] "
    form = _stream(content, matrix + b"/Resources << /Font << /F1 5 0 R >> >> ")
    objects = [_stream(b"q 4 0 0 4 50 50 cm /F Do Q"), _HELVETICA, form]
    return _build([_CATALOG, _ONE_PAGE, page, *objects])


def form_clipped(*, nested: bool = False) -> bytes:
    """`Hidden` and `Shown` in a Form XObject drawn inside a clip that hides `Hidden`.

    With `nested`, the clip is set inside a parent form, around the child form holding the text.
    """
    page = (
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> /XObject << /F 6 0 R >> >> /Contents 4 0 R >>"
    )
    if nested:
        objects = [_stream(b"/F Do"), _HELVETICA, _form(_CLIP_RIGHT, inner=7), _form(_FORM_TEXT)]
    else:
        objects = [_stream(_CLIP_RIGHT), _HELVETICA, _form(_FORM_TEXT)]
    return _build([_CATALOG, _ONE_PAGE, page, *objects])


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


def type3_digits() -> bytes:
    """A Type 3 font naming its digit glyphs `/1` and `/9`, with no ToUnicode (olmOCR e247cacc).

    MuPDF reads such a name as a code point (U+0001, U+0009): `t` and a lowered `1`, then `[9,`.
    """
    page = (
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /T3 5 0 R /F1 8 0 R >> >> /Contents 4 0 R >>"
    )
    content = (
        b"BT /F1 12 Tf 72 700 Td (t) Tj ET BT /T3 8 Tf 80 697 Td (1) Tj ET "
        b"BT /F1 12 Tf 72 650 Td ([) Tj /T3 12 Tf (9) Tj /F1 12 Tf (,) Tj ET"
    )
    font = (
        b"<< /Type /Font /Subtype /Type3 /FontBBox [0 0 600 700] /FontMatrix [0.001 0 0 0.001 0 0] "
        b"/CharProcs << /1 6 0 R /9 7 0 R >> /Encoding << /Type /Encoding /Differences "
        b"[49 /1 57 /9] >> /FirstChar 49 /LastChar 57 /Widths [600 0 0 0 0 0 0 0 600] "
        b"/Resources << >> >>"
    )
    glyph = _stream(b"600 0 0 0 600 700 d1 100 0 400 700 re f")
    return _build([_CATALOG, _ONE_PAGE, page, _stream(content), font, glyph, glyph, _HELVETICA])


def glyph_named(
    base: bytes,
    code: int,
    name: bytes,
    *,
    program: bytes | None = None,
    encoding: bytes | None = None,
) -> bytes:
    """One glyph of an embedded Type 1 (CFF) font whose encoding names it `name`, no ToUnicode.

    The font program is MuPDF's own Dingbats unless `program` is given; `base` is the font's name
    (olmOCR 529eeb, 4fafd7). `encoding` replaces the font's `/Encoding` value.
    """
    cff = pymupdf.Font("zadb").buffer if program is None else program
    page = (
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /D 5 0 R /F1 8 0 R >> >> /Contents 4 0 R >>"
    )
    content = b"BT /D 12 Tf 72 700 Td <%02x> Tj ET BT /F1 12 Tf 72 650 Td (after) Tj ET" % code
    font = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /" + base + b" /FirstChar %d /LastChar %d "
        b"/Widths [791] /FontDescriptor 6 0 R /Encoding "
        + (
            encoding
            if encoding is not None
            else b"<< /BaseEncoding /MacRomanEncoding /Differences [%d /" % code + name + b"] >>"
        )
        + b" >>"
    ) % (code, code)
    descriptor = (
        b"<< /Type /FontDescriptor /FontName /" + base + b" /Flags 4 "
        b"/FontBBox [0 0 1000 1000] /ItalicAngle 0 /Ascent 1000 /Descent 0 /CapHeight 700 "
        b"/StemV 80 /FontFile3 7 0 R >>"
    )
    program = _stream(cff, b" /Subtype /Type1C")
    return _build(
        [_CATALOG, _ONE_PAGE, page, _stream(content), font, descriptor, program, _HELVETICA]
    )


def two_glyph_subsets() -> bytes:
    """Two subsets of `LASY10` on one page, both naming code 50 `/a50`; only the first has a
    ToUnicode (code 50 to U+25A1). A glyph name read by base name alone would reach the first."""
    cff = pymupdf.Font("zadb").buffer
    page = (
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /D 5 0 R /E 9 0 R /F1 8 0 R >> >> /Contents 4 0 R >>"
    )
    content = (
        b"BT /D 12 Tf 72 700 Td <32> Tj ET BT /E 12 Tf 72 680 Td <32> Tj ET "
        b"BT /F1 12 Tf 72 650 Td (after) Tj ET"
    )

    def font(tag: bytes, tounicode: bytes) -> bytes:
        return (
            b"<< /Type /Font /Subtype /Type1 /BaseFont /" + tag + b"+LASY10 /FirstChar 50 "
            b"/LastChar 50 /Widths [791] /FontDescriptor 6 0 R "
            b"/Encoding << /Differences [50 /a50] >>" + tounicode + b" >>"
        )

    descriptor = (
        b"<< /Type /FontDescriptor /FontName /LASY10 /Flags 4 /FontBBox [0 0 1000 1000] "
        b"/ItalicAngle 0 /Ascent 1000 /Descent 0 /CapHeight 700 /StemV 80 /FontFile3 7 0 R >>"
    )
    cmap = (
        b"/CIDInit /ProcSet findresource begin 12 dict begin begincmap /CMapName /X def "
        b"1 begincodespacerange <00> <FF> endcodespacerange 1 beginbfchar <32> <25A1> endbfchar "
        b"endcmap CMapName currentdict /CMap defineresource pop end end"
    )
    return _build(
        [
            _CATALOG, _ONE_PAGE, page, _stream(content), font(b"AAAAAA", b" /ToUnicode 10 0 R"),
            descriptor, _stream(cff, b" /Subtype /Type1C"), _HELVETICA, font(b"BBBBBB", b""),
            _stream(cmap),
        ]
    )  # fmt: skip


def shadow_outside() -> bytes:
    """The five-copy WordArt shadow drawn above a CropBox that ends at y = 700, then `Body`."""
    title = b"(Y a h o o !) Tj "
    moves = (b"-0.03 0 TD ", b"0.03 0.03 TD ", b"-0.03 0 TD ", b"0.015 -0.015 TD ")
    body = b"BT /F1 1 Tf 30 0 0 30 101.13 720 Tm " + title + b"".join(m + title for m in moves)
    doc = pymupdf.open(stream=_raw_content(body + b"ET BT /F1 10 Tf 72 600 Td (Body) Tj ET"))
    doc.xref_set_key(doc[0].xref, "CropBox", "[0 0 612 700]")
    return _save(doc)


def clip_hidden_then_visible() -> bytes:
    """`Banner` hidden by a clip path, then drawn again visibly 0.08 em away."""
    return _raw_content(
        b"q 0 0 1 1 re W n BT /F1 10 Tf 72 700 Td (Banner) Tj ET Q "
        b"BT /F1 10 Tf 72.8 700 Td (Banner) Tj ET"
    )


def fills_and_thin_rules() -> bytes:
    """A grey bar 20 x 100 pt, a grey column rule filled 2.75 pt wide, and a word."""
    return _raw_content(
        b"0.8 g 100 500 20 100 re f 291.45 72.65 2.75 248.1 re f 0 g "
        b"BT /F1 10 Tf 72 700 Td (Fee) Tj ET"
    )


FRAMED_CELLS = {  # a 4 x 3 ruled table, (x0, y0, x1, y1)
    "Service": (150, 300, 290, 320),
    "Fee": (290, 300, 390, 320),
    "Cap": (390, 300, 470, 320),
    "Orders": (150, 320, 290, 340),
    "$0.50": (290, 320, 390, 340),
    "$100": (390, 320, 470, 340),
    "Quotes": (150, 340, 290, 360),
    "$0.25": (290, 340, 390, 360),
    "$50": (390, 340, 470, 360),
    "Trades": (150, 360, 290, 380),
    "$0.10": (290, 360, 390, 380),
    "$20": (390, 360, 470, 380),
}
FRAMED_HEADING = "Schedule of Charges"
FRAMED_INTRO = "The charges below apply to every member of the exchange."


def _boxed_cells(page: pymupdf.Page, cells: dict[str, tuple[float, float, float, float]]) -> None:
    shape = page.new_shape()
    for x0, y0, x1, y1 in cells.values():
        shape.draw_rect(pymupdf.Rect(x0, y0, x1, y1))
    shape.finish(color=BLACK, width=0.5)
    shape.commit()
    for text, (x0, _, _, y1) in cells.items():
        page.insert_text((x0 + 4, y1 - 6), text, fontsize=9)


def _framed_page(doc: pymupdf.Document) -> pymupdf.Page:
    page = _page(doc)
    page.insert_text((150, 200), FRAMED_HEADING, fontsize=16)
    page.insert_text((150, 240), FRAMED_INTRO, fontsize=10)
    return page


def framed_table() -> bytes:
    """A page border 36 pt in, around a heading, a line, a 4 x 3 ruled table with blank margins
    to the border, a footnote, and a page number: Camelot returns one grid, the border (practice
    us-022, olmOCR c45171)."""
    doc = pymupdf.open()
    page = _framed_page(doc)
    shape = page.new_shape()
    shape.draw_rect(pymupdf.Rect(36, 36, 576, 756))
    shape.finish(color=BLACK, width=0.5)
    shape.commit()
    _boxed_cells(page, FRAMED_CELLS)
    page.insert_text(
        (150, 420), "* Charges are billed monthly in arrears to each member.", fontsize=8
    )
    page.insert_text((300, 740), "7", fontsize=9)
    return _save(doc)


def open_frame_table() -> bytes:
    """A `]` frame (two page-wide rules and one vertical rule) around a heading and a separate
    4 x 3 ruled table: Camelot returns the table and a frame grid over it (competition us-036)."""
    doc = pymupdf.open()
    page = _framed_page(doc)
    shape = page.new_shape()
    shape.draw_line((0, 36), (560, 36))
    shape.draw_line((0, 756), (560, 756))
    shape.draw_line((560, 36), (560, 756))
    shape.finish(color=BLACK, width=0.6)
    shape.commit()
    _boxed_cells(page, FRAMED_CELLS)
    return _save(doc)


def watermarked_table() -> bytes:
    """A 4 x 3 ruled table under a 36 pt `DRAFT COPY` drawn at 45 degrees (olmOCR 1ec1f9)."""
    doc = pymupdf.open()
    page = _page(doc)
    _boxed_cells(page, FRAMED_CELLS)
    for text, (x, y) in (("DRAFT", (200, 400)), ("COPY", (330, 400))):
        at = pymupdf.Point(x, y)
        page.insert_text(
            at, text, fontsize=36, color=(0.7, 0.8, 1.0), morph=(at, pymupdf.Matrix(45))
        )
    return _save(doc)


def _centred_text(page: pymupdf.Page, text: str, x0: float, x1: float, y: float) -> None:
    width = pymupdf.get_text_length(text, fontname="helv", fontsize=9)
    page.insert_text(((x0 + x1 - width) / 2, y), text, fontsize=9)


def grey_column_rule() -> bytes:
    """A 3-column ruled table whose rule between columns 0 and 1 is a fill-only grey rectangle
    2.75 pt wide; the third column is shaded, and one of its values sits on a 4.08 pt shaded strip
    (practice us-008)."""
    doc = pymupdf.open()
    page = _page(doc)
    xs, top, bottom, pitch = (100, 220, 340, 460), 200, 320, 20
    shape = page.new_shape()
    shape.draw_rect(pymupdf.Rect(340, top, 460, bottom))
    shape.finish(fill=(0.95, 0.95, 0.95), color=None)
    shape.draw_rect(pymupdf.Rect(360, 262.5, 440, 266.58))
    shape.finish(fill=(0.95, 0.95, 0.95), color=None)
    shape.draw_rect(pymupdf.Rect(218.625, top, 221.375, bottom))
    shape.finish(fill=(0.8, 0.8, 0.8), color=None)
    for y in range(top, bottom + 1, pitch):
        shape.draw_line((100, y), (460, y))
    for x in (100, 340, 460):
        shape.draw_line((x, top), (x, bottom))
    shape.finish(color=BLACK, width=0.5)
    shape.commit()
    rows = [("Band", "Rate", "Cap"), *((f"Band {i}", f"0.{i}0", f"{i}00") for i in range(1, 6))]
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            _centred_text(page, text, xs[c], xs[c + 1], top + pitch * r + 13)
    return _save(doc)


def stub_column_rule() -> bytes:
    """A 3-column ruled table whose header `Fees` spans columns 1-2, the rule between them
    starting 2.7 pt above the header's bottom edge: Camelot drops it (olmOCR 008d1d)."""
    doc = pymupdf.open()
    page = _page(doc)
    top, pitch, n = 200, 20, 6
    bottom = top + pitch * n
    shape = page.new_shape()
    for y in range(top, bottom + 1, pitch):
        shape.draw_line((100, y), (460, y))
    for x in (100, 220, 460):
        shape.draw_line((x, top), (x, bottom))
    shape.draw_line((340, top + pitch - 2.7), (340, bottom))
    shape.finish(color=BLACK, width=0.8)
    shape.commit()
    _centred_text(page, "Item", 100, 220, top + 13)
    _centred_text(page, "Fees", 220, 460, top + 13)
    for i in range(1, n):
        y = top + pitch * i + 13
        _centred_text(page, f"Item {i}", 100, 220, y)
        _centred_text(page, f"0.{i}0", 220, 340, y)
        _centred_text(page, f"{i}.00", 340, 460, y)
    return _save(doc)


def ruled_corridor() -> bytes:
    """A table ruled only by one horizontal rule under its header (so Camelot reads nothing) and
    a vertical rule between its label and value columns: each label ends 4.7 pt left of the rule
    and each value starts 4.8 pt right of it, 9.5 pt apart at 11 pt (practice us-012)."""
    doc = pymupdf.open()
    page = _page(doc)
    labels = ("Area", "United States", "Territories", "Overseas", "Total")
    values = (
        ("Army", "Navy"),
        ("1,768", "8,250"),
        ("25", "4,500"),
        ("371", "1,540"),
        ("2,164", "1,024"),
    )
    top, pitch, size = 300, 14, 11
    rule_x = 72 + pymupdf.get_text_length("United States", fontsize=size) + 4.7
    shape = page.new_shape()
    shape.draw_line((72, top + pitch + 1), (rule_x + 120, top + pitch + 1))
    shape.draw_line((rule_x, top - 10), (rule_x, top + pitch * 5))
    shape.finish(color=BLACK, width=0.5)
    shape.commit()
    for i, (label, (a, b)) in enumerate(zip(labels, values, strict=True)):
        y = top + pitch * i + 10
        page.insert_text((72, y), label, fontsize=size)
        page.insert_text((rule_x + 4.8, y), a, fontsize=size)
        page.insert_text((rule_x + 70, y), b, fontsize=size)
    return _save(doc)


def _centred(
    page: pymupdf.Page, text: str, x0: float, x1: float, y: float, *, font: str = "helv"
) -> None:
    width = pymupdf.get_text_length(text, fontname=font, fontsize=9)
    page.insert_text(((x0 + x1 - width) / 2, y), text, fontsize=9, fontname=font)


def spanning_header_pages() -> bytes:
    """3 pages (eu-001), each a varying heading, then a ruled table whose first row spans columns
    1-3 with the same `Threshold for releases`, in the page's top band; a running footer."""
    doc = pymupdf.open()
    for heading in ("Pesticides", "Solvents", "Metals"):
        page = _page(doc)
        page.insert_text((72, 60), heading, fontsize=11, fontname="hebo")
        xs, top, pitch = (72, 272, 352, 432, 512), 80, 16
        shape = page.new_shape()
        for r in range(22):
            shape.draw_line((72, top + pitch * r), (512, top + pitch * r))
        for x in xs:
            shape.draw_line((x, top + (pitch if x in {352, 432} else 0)), (x, top + pitch * 21))
        shape.finish(color=BLACK, width=0.5)
        shape.commit()
        _centred(page, "Threshold for releases", 272, 512, top + 12, font="hebo")
        for c, text in enumerate(("to air", "to water", "to land")):
            _centred(page, text, xs[c + 1], xs[c + 2], top + pitch + 12)
        for r in range(2, 21):
            y = top + pitch * r + 12
            page.insert_text((76, y), f"{heading} compound {r}", fontsize=9)
            for c in range(3):
                _centred(page, str(r * (c + 1)), xs[c + 1], xs[c + 2], y)
        page.insert_text((72, 740), "Acme Fee Guide", fontsize=9)
    return _save(doc)


def stub_banner_pages() -> bytes:
    """3 pages (us-017), each a running header, a varying title, a 4-fragment column header, the
    stub banner `Actual`, then value rows (unruled), and a page number."""
    doc = pymupdf.open()
    for n in range(3):
        page = _page(doc)
        page.insert_text((72, 40), "Acme Statistics", fontsize=9)
        title = f"Table {n + 1}. Enrolment by {('level', 'control', 'region')[n]}"
        page.insert_text((72, 58), title, fontsize=9, fontname="hebo")
        xs = (72, 200, 300, 400)
        for x, text in zip(xs, ("Year", "Total", "Public", "Private"), strict=True):
            page.insert_text((x, 76), text, fontsize=9)
        page.insert_text((72, 90), "Actual", fontsize=9, fontname="hebo")
        for i in range(40):
            y = 102 + 11 * i
            page.insert_text((72, y), str(1990 + i), fontsize=9)
            for k, x in enumerate(xs[1:]):
                page.insert_text((x, y), f"{(n + 1) * (i + 1) * (k + 3)},{100 + i}", fontsize=9)
        page.insert_text((72, 700), f"Page {n + 1}", fontsize=9)
    return _save(doc)


def mirrored_footer_pages() -> bytes:
    """2 pages (eu-030): a two-line running footer whose inner line `ECB` repeats and whose outer
    line's word order mirrors on the even page, so its key differs page to page."""
    doc = pymupdf.open()
    for n in (1, 2):
        page = _page(doc)
        for i in range(3):
            text = f"Body text line {i} of page {'abc'[n - 1] * (i + 1)}"
            page.insert_text((72, 100 + 14 * i), text, fontsize=10)
        page.insert_text((72, 740), "ECB", fontsize=8)
        outer = (
            f"S {n} Monthly Bulletin March 2006" if n % 2 else f"Monthly Bulletin March 2006 S {n}"
        )
        page.insert_text((72, 752), outer, fontsize=8)
    return _save(doc)


def bar_chart(*, turned: bool = False) -> bytes:
    """A boxed bar chart: 5 bars on one baseline at 1.88 pt per unit, their values above (decimal
    commas), category labels below between ticks, axis labels without ticks (olmOCR 2ad3ea).

    `turned` draws it upright on screen on a `/Rotate 90` page (practice eu-018)."""
    doc = pymupdf.open()
    page = _page(doc)
    height = page.rect.height

    def rect(x0: float, y0: float, x1: float, y1: float) -> pymupdf.Rect:
        # Screen (X, Y) shows the unrotated point (Y, height - X), as `ruled_landscape` draws.
        return (
            pymupdf.Rect(y0, height - x1, y1, height - x0)
            if turned
            else pymupdf.Rect(x0, y0, x1, y1)
        )

    def point(x: float, y: float) -> tuple[float, float]:
        return (y, height - x) if turned else (x, y)

    def text(x: float, y: float, label: str, size: float) -> None:
        page.insert_text(point(x, y), label, fontsize=size, rotate=90 if turned else 0)

    base, k, x = 500.0, 1.88, 160.0
    values = [1.4, 7.8, 20.0, 44.4, 20.9]
    shape = page.new_shape()
    shape.draw_rect(rect(100, 300, 520, 540))
    shape.finish(color=(0.6, 0.6, 0.6), width=0.75)
    for i, v in enumerate(values):
        shape.draw_rect(rect(x + 64 * i, base - k * v, x + 64 * i + 25, base))
    shape.finish(color=None, fill=(0.75, 0, 0))
    shape.draw_line(point(140, base), point(140 + 64 * 5, base))
    for i in range(6):
        shape.draw_line(point(140 + 64 * i, base), point(140 + 64 * i, base + 3.3))
    shape.finish(color=(0.6, 0.6, 0.6), width=0.75)
    shape.commit()
    for i, v in enumerate(values):
        text(x + 64 * i + 4, base - k * v - 6, f"{v:.1f}".replace(".", ","), 8)
        text(x + 64 * i, base + 16, ["Poor", "Fair", "Good", "Great", "Superb"][i], 8)
    for v in range(0, 60, 10):
        text(115, base - k * v + 3, str(v), 8)
    text(200, 320, "How would you rate your sleep?", 10)
    if turned:
        page.set_rotation(90)
    return _save(doc)


def bar_chart_landscape() -> bytes:
    """`bar_chart` upright on screen on a `/Rotate 90` page."""
    return bar_chart(turned=True)


PROSE_PAGES = (
    (
        "The exchange publishes its fees each year in this guide for members.",
        "Orders sent before the open are charged at the auction rate shown below.",
        "Quotes that rest for a full second earn the maker rebate for the day.",
    ),
    (
        "Clearing is charged per contract and billed monthly to each member firm.",
        "Settlement failures are charged at the penalty rate after two days.",
        "Members may appeal a charge within thirty days of the invoice date.",
    ),
    (
        "Market data is licensed per user, with discounts for non-display use.",
        "Connectivity is billed per port and per cross-connect in the data centre.",
        "The schedule takes effect on the first business day of the next month.",
    ),
)
"""Three pages' body lines that differ in their words, as real text does."""


def unruled_watermarked_table() -> bytes:
    """An unruled 9 x 3 table under a 45 degree `DRAFT` watermark (the final review's R3)."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((72, 80), "Schedule of Charges", fontsize=14, fontname="hebo")
    page.insert_text(
        (72, 110), "The charges below apply to every member of the exchange.", fontsize=10
    )
    fees = (
        ("Orders", 0.50, 100),
        ("Quotes", 0.25, 50),
        ("Trades", 0.10, 20),
        ("Cancels", 0.05, 10),
        ("Amends", 0.02, 5),
        ("Reports", 1.00, 200),
        ("Ports", 25.00, 500),
        ("Sessions", 12.50, 250),
    )
    rows = [("Service", "Fee", "Cap"), *((s, f"${a:.2f}", f"${b}") for s, a, b in fees)]
    for i, row in enumerate(rows):
        for x, text in zip((72, 250, 360), row, strict=True):
            page.insert_text(
                (x, 150 + 16 * i), text, fontsize=9, fontname="hebo" if i == 0 else "helv"
            )
    page.insert_text(
        (72, 320), "Charges are billed monthly in arrears to each member firm.", fontsize=10
    )
    at = pymupdf.Point(180, 260)
    page.insert_text(
        at, "DRAFT", fontsize=40, color=(0.7, 0.8, 1.0), morph=(at, pymupdf.Matrix(45))
    )
    return _save(doc)


DATA_BAR_ROWS = (
    ("North", 4120, 12),
    ("South", 6480, 15),
    ("East", 7950, 9),
    ("West", 9300, 21),
    ("Central", 5210, 7),
    ("Overseas", 8040, 11),
)


def _right(page: pymupdf.Page, text: str, x1: float, y: float) -> None:
    width = pymupdf.get_text_length(text, fontname="helv", fontsize=9)
    page.insert_text((x1 - 4 - width, y), text, fontsize=9)


def data_bar_table() -> bytes:
    """A ruled 7 x 3 table whose Revenue column carries in-cell data bars (a fill from the cell's
    left edge in proportion to the value, the value right-aligned over it; the review's R4)."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((100, 170), "Revenue by region, 2026", fontsize=12, fontname="hebo")
    xs, top, pitch = (100, 250, 370, 450), 200, 20
    shape = page.new_shape()
    for i, (_, value, _) in enumerate(DATA_BAR_ROWS, start=1):
        y0 = top + pitch * i + 3
        shape.draw_rect(pymupdf.Rect(252, y0, 252 + 116 * value / 9300, y0 + pitch - 6))
    shape.finish(fill=(0.6, 0.75, 0.95), color=None)
    for r in range(len(DATA_BAR_ROWS) + 2):
        shape.draw_line((xs[0], top + pitch * r), (xs[-1], top + pitch * r))
    for x in xs:
        shape.draw_line((x, top), (x, top + pitch * (len(DATA_BAR_ROWS) + 1)))
    shape.finish(color=BLACK, width=0.5)
    shape.commit()
    for c, head in enumerate(("Region", "Revenue", "Staff")):
        page.insert_text((xs[c] + 4, top + 14), head, fontsize=9, fontname="hebo")
    for i, (name, value, staff) in enumerate(DATA_BAR_ROWS, start=1):
        y = top + pitch * i + 14
        page.insert_text((xs[0] + 4, y), name, fontsize=9)
        _right(page, f"{value:,}", xs[2], y)
        _right(page, str(staff), xs[3], y)
    return _save(doc)


def tier_sub_rules() -> bytes:
    """A fee table ruled by horizontal rules only: each tier number, centred under `Tier`, sits
    level with the rule between its two sub-rows, which starts at the next column (the review's
    R5)."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((72, 110), "Clearing fee tiers", fontsize=12, fontname="hebo")
    _centred(page, "Tier", 72, 94, 140, font="hebo")
    for x, text in ((104, "Monthly volume"), (260, "Rate"), (330, "Cap")):
        page.insert_text((x, 140), text, fontsize=9, fontname="hebo")
    shape = page.new_shape()
    shape.draw_line((72, 146), (400, 146))
    tops = ("1,000,000", "5,000,000", "20,000,000", "50,000,000")
    for t, bound in enumerate(tops):
        ya = 160 + 34 * t
        yb = ya + 16
        for x, text in ((104, f"Up to {bound}"), (260, f"0.{t + 1}0"), (330, f"{(t + 1) * 100}")):
            page.insert_text((x, ya), text, fontsize=9)
        for x, text in ((104, f"Over {bound}"), (260, f"0.0{t + 5}"), (330, f"{(t + 1) * 50}")):
            page.insert_text((x, yb), text, fontsize=9)
        mid = (ya + yb) / 2
        _centred(page, str(t + 1), 72, 94, mid + 3.2)
        shape.draw_line((98, mid), (400, mid))  # the rule between the tier's two sub-rows
        shape.draw_line((72, yb + 6), (400, yb + 6))  # the rule under the tier
    shape.finish(color=BLACK, width=0.5)
    shape.commit()
    page.insert_text((72, 320), "Rates are charged per contract cleared in the month.", fontsize=10)
    return _save(doc)


def top_aligned_side_cells() -> bytes:
    """A ruled table whose row-spanning label and notes columns run its full height, their text
    top-aligned level with the spanning header row (FR3's shape; the review's R12)."""
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((72, 130), "Clearing fees by product", fontsize=12, fontname="hebo")
    xs, top, pitch, n = (72, 170, 300, 400, 540), 150, 20, 6
    bottom = top + pitch * n
    shape = page.new_shape()
    shape.draw_rect(pymupdf.Rect(xs[0], top, xs[-1], bottom))
    for r in range(1, n):  # rows only across the middle columns
        shape.draw_line((xs[1], top + pitch * r), (xs[3], top + pitch * r))
    shape.draw_line((xs[1], top), (xs[1], bottom))
    shape.draw_line((xs[3], top), (xs[3], bottom))
    shape.draw_line((xs[2], top + pitch), (xs[2], bottom))  # the header row spans columns 1-2
    shape.finish(color=BLACK, width=0.5)
    shape.commit()
    page.insert_text((xs[0] + 4, top + 14), "Equities", fontsize=9, fontname="hebo")
    page.insert_text((xs[3] + 4, top + 14), "Billed monthly", fontsize=9)
    page.insert_text(
        (xs[1] + 4, top + 14), "Clearing fee per contract", fontsize=9, fontname="hebo"
    )
    rows = (
        ("Service", "Fee"),
        ("Orders", "0.50"),
        ("Quotes", "0.25"),
        ("Trades", "0.10"),
        ("Cancels", "0.05"),
    )
    for r, (a, b) in enumerate(rows, start=1):
        y = top + pitch * r + 14
        font = "hebo" if r == 1 else "helv"
        page.insert_text((xs[1] + 4, y), a, fontsize=9, fontname=font)
        page.insert_text((xs[2] + 4, y), b, fontsize=9, fontname=font)
    return _save(doc)


def framed_pages() -> bytes:
    """3 pages, each a page border around a running header, a heading, a line, the 4 x 3 ruled
    table of `framed_table`, a footnote, and a page number (the review's R1)."""
    doc = pymupdf.open()
    for n, heading in enumerate(("Equities", "Options", "Futures"), start=1):
        page = _page(doc)
        page.insert_text((150, 60), "Acme Exchange Fee Guide 2026", fontsize=9)
        page.insert_text((150, 200), f"Schedule of {heading} Charges", fontsize=16)
        page.insert_text(
            (150, 240), f"The {heading.lower()} charges below apply to every member.", fontsize=10
        )
        shape = page.new_shape()
        shape.draw_rect(pymupdf.Rect(36, 36, 576, 756))
        shape.finish(color=BLACK, width=0.5)
        shape.commit()
        _boxed_cells(page, FRAMED_CELLS)
        page.insert_text(
            (150, 420), f"* {heading} charges are billed monthly in arrears.", fontsize=8
        )
        page.insert_text((300, 740), str(n), fontsize=9)
    return _save(doc)


NEWSLETTER_WORDS = (
    "members",
    "exchange",
    "market",
    "trading",
    "orders",
    "quotes",
    "volume",
    "session",
    "clearing",
    "settlement",
    "venue",
    "liquidity",
    "auction",
    "closing",
    "opening",
    "rules",
    "notice",
)


def bordered_newsletter() -> bytes:
    """3 pages of a two-column newsletter inside a page border, a rule under the running header
    and one between the columns; no table (the review's R1b)."""
    doc = pymupdf.open()
    words = NEWSLETTER_WORDS
    for n in range(1, 4):
        page = _page(doc)
        page.insert_text((60, 58), "Acme Exchange Member Newsletter", fontsize=9)
        shape = page.new_shape()
        shape.draw_rect(pymupdf.Rect(36, 36, 576, 756))
        shape.draw_line((36, 70), (576, 70))
        shape.draw_line((306, 70), (306, 756))
        shape.finish(color=BLACK, width=0.5)
        shape.commit()
        for col, x in enumerate((60, 330)):
            for i in range(40):
                picked = (words[(i * 7 + j * 3 + n * 5 + col) % len(words)] for j in range(6))
                issue = ("alpha", "bravo", "charlie")[n - 1]  # body lines differ page to page
                text = f"Item {n}.{col}.{i} {issue} " + " ".join(picked)
                page.insert_text((x, 100 + 15 * i), text, fontsize=9)
        page.insert_text((540, 740), str(n), fontsize=9)
    return _save(doc)


def running_box_pages() -> bytes:
    """3 pages, each with a ruled 2 x 2 running-header box (company | document number, title |
    revision), then prose that varies by page, and a page number (the review's R11)."""
    doc = pymupdf.open()
    for n, body in enumerate(PROSE_PAGES, start=1):
        page = _page(doc)
        shape = page.new_shape()
        for y in (36, 54, 72):
            shape.draw_line((72, y), (540, y))
        for x in (72, 400, 540):
            shape.draw_line((x, 36), (x, 72))
        shape.finish(color=BLACK, width=0.5)
        shape.commit()
        page.insert_text((76, 49), "Acme Exchange Ltd", fontsize=9, fontname="hebo")
        page.insert_text((404, 49), "Doc FS-014", fontsize=9)
        page.insert_text((76, 67), "Schedule of Fees and Charges", fontsize=9)
        page.insert_text((404, 67), "Revision 3", fontsize=9)
        for i, line in enumerate(body):
            page.insert_text((72, 120 + 14 * i), line, fontsize=10)
        page.insert_text((300, 750), str(n), fontsize=9)
    return _save(doc)


def three_part_footer_pages() -> bytes:
    """3 pages; a two-line running footer: a copyright line, and nearest the edge a footer in
    three parts (left, centre, right); prose that varies by page (the review's R2)."""
    doc = pymupdf.open()
    for n, body in enumerate(PROSE_PAGES, start=1):
        page = _page(doc)
        for i, line in enumerate(body):
            page.insert_text((72, 100 + 14 * i), line, fontsize=10)
        page.insert_text(
            (72, 728), "Copyright 2026 Acme Exchange. All rights reserved.", fontsize=8
        )
        page.insert_text((72, 745), "Acme Fee Guide", fontsize=8)
        page.insert_text((280, 745), "Confidential", fontsize=8)
        page.insert_text((500, 745), f"Page {n}", fontsize=8)
    return _save(doc)


def marked_value() -> bytes:
    """`.54` with a raised mark glued on, beside a line in the next column set 7 pt higher.

    The mark (a Type 3 glyph, whose box has no descender, as tight as the measured one) overlaps
    that line by more than half its height and is reached before its own row when lines are
    clustered by centre, while the row stays below the line (olmOCR 2d54e9).
    """
    page = (
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /T3 5 0 R /F1 7 0 R >> >> /Contents 4 0 R >>"
    )
    content = (
        b"BT /F1 9 Tf 72 700 Td (.54) Tj /T3 5.5 Tf 3.8 Ts (*) Tj /F1 9 Tf 0 Ts ( \\(.17\\)) Tj ET "
        b"BT /F1 9 Tf 120 707.1 Td (chological Bulletin, 111, 203) Tj ET "
        b"BT /F1 9 Tf 72 680 Td (Note. Values in parentheses.) Tj ET"
    )
    font = (
        b"<< /Type /Font /Subtype /Type3 /FontBBox [0 0 500 600] /FontMatrix [0.001 0 0 0.001 0 0] "
        b"/CharProcs << /asterisk 6 0 R >> "
        b"/Encoding << /Type /Encoding /Differences [42 /asterisk] >> "
        b"/FirstChar 42 /LastChar 42 /Widths [500] /Resources << >> >>"
    )
    glyph = _stream(b"500 0 0 0 500 600 d1 100 300 300 300 re f")
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
    "overprinted_banner": overprinted_banner,
    "stroked_then_filled": stroked_then_filled,
    "wordart_shadow": wordart_shadow,
    "type3_digits": type3_digits,
    "glyph_dingbats": lambda: glyph_named(b"ABCDEF+ZapfDingbatsITC", 3, b"a71"),
    "glyph_digit_name": lambda: glyph_named(b"ABCDEF+LASY10", 50, b"a50"),
    "cropbox_beyond": cropbox_beyond,
    "cropbox_overhang": lambda: cropbox_beyond("0 -4.3 602.29 800"),
    "marked_value": marked_value,
    "framed_table": framed_table,
    "open_frame_table": open_frame_table,
    "watermarked_table": watermarked_table,
    "grey_column_rule": grey_column_rule,
    "stub_column_rule": stub_column_rule,
    "ruled_corridor": ruled_corridor,
    "bar_chart": bar_chart,
    "bar_chart_landscape": bar_chart_landscape,
    "unruled_watermarked_table": unruled_watermarked_table,
    "data_bar_table": data_bar_table,
    "tier_sub_rules": tier_sub_rules,
    "top_aligned_side_cells": top_aligned_side_cells,
    "framed_pages": framed_pages,
    "bordered_newsletter": bordered_newsletter,
    "running_box_pages": running_box_pages,
    "three_part_footer_pages": three_part_footer_pages,
    "spanning_header_pages": spanning_header_pages,
    "stub_banner_pages": stub_banner_pages,
    "mirrored_footer_pages": mirrored_footer_pages,
    "shadow_outside": shadow_outside,
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
    "form_clipped": form_clipped,
    "nested_form_clipped": lambda: form_clipped(nested=True),
    "scaled_form_clipped": scaled_form_clipped,
    "two_column": two_column,
    "landscape": landscape,
    "unruled_table": unruled_table,
    "chained_edge": chained_edge,
    "continued_table": continued_table,
    "headerless_table": headerless_table,
    "continued_paragraph": continued_paragraph,
    "footnoted_table": footnoted_table,
    "glued_notes": glued_notes,
    "definitions_section": definitions_section,
    "legend_grid": legend_grid,
    "centred_span": centred_span,
    "centred_values": centred_values,
    "ruled_and_unruled": ruled_and_unruled,
    "unruled_landscape": unruled_landscape,
    "ruled_grid": ruled_grid,
    "formed_rules": formed_rules,
    "ruled_landscape": ruled_landscape,
    "table_between_paragraphs": table_between_paragraphs,
    "boxed_paragraph": boxed_paragraph,
    "labelled_page": labelled_page,
    "ruled_columns": ruled_columns,
    "table_in_right_column": table_in_right_column,
    "spaced_paragraphs": spaced_paragraphs,
    "furnished": furnished,
    "furniture_only_page": furniture_only_page,
}
