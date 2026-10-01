"""The text-layer ablation: inkgrid fed Tesseract's words (docs/specs/15-heavy-competitors.md s. 4).

Only the words change. Each page keeps its own size, rotation, rules, and fills; Camelot reads the
ruled pages exactly as for inkgrid, and the pipeline builds the document unchanged, so the paired
difference against inkgrid is the text layer's effect on inkgrid's own gridders.
"""

import unicodedata
from collections.abc import Callable, Sequence

from inkgrid.core.pipeline import build_document
from inkgrid.core.tables.pages import lattice_pages
from inkgrid.model.config import Lexicon, Profile
from inkgrid.model.geometry import Rect
from inkgrid.model.page import PageModel, Reading, Word
from inkgrid.read.camelot_reader import read_lattice
from inkgrid.read.pymupdf_reader import lattice_copy, page_frames, read_pdf
from inkgrid_bench.adapters.inkgrid_read import tables_of
from inkgrid_bench.tables import NPage, NTable

DPI = 300
SCALE = 72 / DPI  # points per pixel of the rendered page
FONT = "tesseract"
WORD_LEVEL = "5"
COLUMNS = ("level", "left", "top", "width", "height", "text")
_DROP = frozenset({"Cc", "Cf", "Co", "Cn", "Cs"})  # categories a word may not hold


def _clean(text: str) -> str:
    return "".join(c for c in text if not c.isspace() and unicodedata.category(c) not in _DROP)


def words_from_tsv(tsv: str, *, page: int, frame: NPage, scale: float, first_id: int) -> list[Word]:
    """Tesseract's words (level 5, with a text) on one page, in points, ids from `first_id`.

    The page was rendered as it displays, so on a turned page each box is turned back into the
    unrotated page, and its words are not horizontal there, as the reader would have them.
    """
    lines = tsv.splitlines()
    if not lines:
        return []
    header = lines[0].split("\t")
    missing = [c for c in COLUMNS if c not in header]
    if missing:
        msg = f"a Tesseract TSV without {', '.join(missing)}"
        raise ValueError(msg)
    at = {c: header.index(c) for c in COLUMNS}
    out: list[Word] = []
    for line in lines[1:]:
        fields = line.split("\t")
        if fields[at["level"]] != WORD_LEVEL:
            continue
        text = _clean(fields[at["text"]] if len(fields) > at["text"] else "")
        if not text:
            continue
        left, top, width, height = (int(fields[at[c]]) for c in ("left", "top", "width", "height"))
        ax, ay = frame.from_shown(left * scale, top * scale)
        bx, by = frame.from_shown((left + width) * scale, (top + height) * scale)
        out.append(
            Word(
                id=first_id + len(out),
                page=page,
                bbox=Rect(min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)),
                text=text,
                size=height * scale,
                font=FONT,
                bold=False,
                italic=False,
                superscript=False,
                hidden=False,
                horizontal=frame.rotation == 0,
            )
        )
    return out


def ocr_reading(reading: Reading, frames: Sequence[NPage], ocr: Callable[[int], str]) -> Reading:
    """The reading with every page's words replaced by Tesseract's, all else kept."""
    pages: list[PageModel] = []
    next_id = 0
    for page, frame in zip(reading.pages, frames, strict=True):
        words = words_from_tsv(
            ocr(page.number), page=page.number, frame=frame, scale=SCALE, first_id=next_id
        )
        next_id += len(words)
        pages.append(
            PageModel(
                number=page.number,
                width=page.width,
                height=page.height,
                rotation=page.rotation,
                text_layer="full" if words else "none",
                invisible_chars=0,
                clipped_chars=0,
                unmapped_chars=0,
                hidden_chars=0,
                image_area_ratio=page.image_area_ratio,
                words=tuple(words),
                rules=page.rules,
                fills=page.fills,
            )
        )
    return Reading(source=reading.source, reader=reading.reader, pages=tuple(pages), findings=())


def ocr_tables(data: bytes, frames: Sequence[NPage], ocr: Callable[[int], str]) -> list[NTable]:
    """Inkgrid's tables with its words from `ocr` (a page number to Tesseract's TSV)."""
    reading = ocr_reading(read_pdf(data, file_name=None, password=None), frames, ocr)
    ruled = lattice_pages(reading)
    grids = (
        read_lattice(
            lattice_copy(data, None),
            page_frames(data, None),
            ruled,
            engine="combined",
            password=None,
        )
        if ruled
        else None
    )
    doc = build_document(
        reading, lexicon=Lexicon(), profile=Profile(), lattice="combined", grids=grids
    )
    return tables_of(doc)
