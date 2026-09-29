"""The page as its reader sees it (docs/specs/04-text-pipeline.md, "The upright page").

The page model's coordinates are unrotated, so a landscape page (text upright on screen through a
`/Rotate`) holds nothing but vertical words. Layout needs the frame the reader sees.
"""

from inkgrid.model.geometry import turn_rect
from inkgrid.model.page import PageModel, Word


def _turned(word: Word, page: PageModel) -> Word:
    box = turn_rect(word.bbox, page.rotation, page.width, page.height)
    # The reader flags only the direction (1, 0) as horizontal: turning flips which words are. A
    # diagonal word stays diagonal under a quarter turn, so it is never horizontal.
    horizontal = not word.horizontal and not word.diagonal
    return word.model_copy(update={"bbox": box, "horizontal": horizontal})


def upright(page: PageModel) -> PageModel:
    """The page turned to its screen frame when most of its text is upright only there.

    The upright page carries no rules and no fills; M2 maps rules when it first reads them.
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
