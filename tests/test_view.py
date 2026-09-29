import pytest

from inkgrid.core.view import upright
from inkgrid.model.geometry import Rect
from model_builders import mk_page, mk_word


@pytest.mark.parametrize(
    ("rotation", "box", "size"),
    [
        (90, (762, 10, 772, 30), (792, 612)),
        (180, (582, 762, 602, 772), (612, 792)),
        (270, (20, 582, 30, 602), (792, 612)),
    ],
)
def test_VW1_a_rotated_page_of_vertical_words_turns_upright(
    rotation: int, box: tuple[float, float, float, float], size: tuple[float, float]
) -> None:
    word = mk_word(bbox=Rect(10, 20, 30, 30), horizontal=False)
    page = upright(mk_page(rotation=rotation, words=(word,)))
    assert (page.width, page.height, page.rotation) == (*size, 0)
    (turned,) = page.words
    assert turned.bbox == Rect(*box)
    assert turned.horizontal is True
    assert (turned.id, turned.text) == (word.id, word.text)


def test_VW2_mostly_horizontal_text_keeps_the_unrotated_frame() -> None:
    words = (mk_word(id=0, text="across"), mk_word(id=1, text="up", horizontal=False))
    page = mk_page(rotation=90, words=words)
    assert upright(page) is page


def test_VW3_an_unrotated_page_is_unchanged() -> None:
    page = mk_page(words=(mk_word(horizontal=False),))
    assert upright(page) is page


def test_DG2_a_diagonal_word_stays_diagonal_on_a_turned_page() -> None:
    upright_words = tuple(
        mk_word(id=i, bbox=Rect(10, 20 + 20 * i, 30, 30 + 20 * i), horizontal=False)
        for i in range(3)
    )
    watermark = mk_word(id=3, bbox=Rect(100, 100, 300, 300), horizontal=False, diagonal=True)
    page = upright(mk_page(rotation=90, words=(*upright_words, watermark)))
    turned = page.words[-1]
    assert (turned.diagonal, turned.horizontal) == (True, False)
    type(turned).model_validate_json(turned.model_dump_json())  # a valid word
