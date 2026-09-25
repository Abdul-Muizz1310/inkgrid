"""Small builders for page-model values, shared by unit tests."""

from typing import Any

from inkgrid.model.findings import Finding
from inkgrid.model.geometry import Rect
from inkgrid.model.page import PageModel, ReaderInfo, Reading, Source, Word

SHA = "0" * 64
READER = ReaderInfo(inkgrid="0.1.0.dev0", pymupdf="1.28.2", mupdf="1.28.2")


def mk_word(**kw: Any) -> Word:
    fields: dict[str, Any] = {
        "id": 0,
        "page": 1,
        "bbox": Rect(0, 0, 10, 10),
        "text": "a",
        "size": 10.0,
        "font": "Helvetica",
        "bold": False,
        "italic": False,
        "superscript": False,
        "hidden": False,
        "horizontal": True,
    }
    fields.update(kw)
    return Word(**fields)


def mk_page(**kw: Any) -> PageModel:
    fields: dict[str, Any] = {
        "number": 1,
        "width": 612.0,
        "height": 792.0,
        "rotation": 0,
        "text_layer": "full",
        "invisible_chars": 0,
        "clipped_chars": 0,
        "unmapped_chars": 0,
        "hidden_chars": 0,
        "image_area_ratio": 0.0,
        "words": (mk_word(),),
        "rules": (),
    }
    fields.update(kw)
    return PageModel(**fields)


def mk_reading(pages: tuple[PageModel, ...], findings: tuple[Finding, ...] = ()) -> Reading:
    return Reading(
        source=Source(sha256=SHA, pages=len(pages), file_name=None),
        reader=READER,
        pages=pages,
        findings=findings,
    )
