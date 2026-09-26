"""The page as its reader sees it (docs/specs/04-text-pipeline.md, "The upright page").

The page model's coordinates are unrotated, so a landscape page (text upright on screen through a
`/Rotate`) holds nothing but vertical words. Layout needs the frame the reader sees.
"""

from inkgrid.model.geometry import Rect
from inkgrid.model.page import PageModel, Word


def _turn(x: float, y: float, page: PageModel) -> tuple[float, float]:
    """A point of the unrotated page, as shown on screen (PyMuPDF's rotation_matrix)."""
    width, height = page.width, page.height
    match page.rotation:
        case 90:
            return height - y, x
        case 180:
            return width - x, height - y
        case 270:
            return y, width - x
        case 0:
            return x, y


def _turned(word: Word, page: PageModel) -> Word:
    x0, y0 = _turn(word.bbox.x0, word.bbox.y0, page)
    x1, y1 = _turn(word.bbox.x1, word.bbox.y1, page)
    box = Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    # The reader flags only the direction (1, 0) as horizontal: turning flips which words are.
    return word.model_copy(update={"bbox": box, "horizontal": not word.horizontal})


def upright(page: PageModel) -> PageModel:
    """The page turned to its screen frame when most of its text is upright only there.

    The upright page carries no rules; M2 maps rules when it first reads them.
    """
    chars = sum(len(w.text) for w in page.words)
    across = sum(len(w.text) for w in page.words if not w.horizontal)
    if page.rotation == 0 or 2 * across <= chars:
        return page
    quarter = page.rotation in {90, 270}
    return PageModel(
        number=page.number,
        width=page.height if quarter else page.width,
        height=page.width if quarter else page.height,
        rotation=0,
        text_layer=page.text_layer,
        invisible_chars=page.invisible_chars,
        clipped_chars=page.clipped_chars,
        unmapped_chars=page.unmapped_chars,
        hidden_chars=page.hidden_chars,
        image_area_ratio=page.image_area_ratio,
        words=tuple(_turned(w, page) for w in page.words),
        rules=(),
    )
