from inkgrid.read.glyphs import ZAPF_DINGBATS, charset_names, differences_names, glyph_reading


def test_GN3_a_name_outside_the_glyph_list_reads_by_the_dingbats_list_or_as_no_unicode() -> None:
    assert glyph_reading("a71", font="ZapfDingbatsITC", in_agl=False) == "\u25cf"
    assert glyph_reading("a71.alt", font="ZapfDingbats", in_agl=False) == "\u25cf"
    assert glyph_reading("a71", font="LASY10", in_agl=False) == "\ufffd"
    assert glyph_reading("a999", font="ZapfDingbatsITC", in_agl=False) == "\ufffd"
    assert glyph_reading("50", font="LASY10", in_agl=False) == "\ufffd"


def test_GN3_a_name_the_glyph_list_knows_or_of_another_shape_is_left_alone() -> None:
    assert glyph_reading("A", font="ZapfDingbatsITC", in_agl=True) is None
    assert glyph_reading("uni2022", font="X", in_agl=False) is None
    assert glyph_reading("bullet", font="X", in_agl=True) is None
    assert glyph_reading("a71x", font="ZapfDingbatsITC", in_agl=False) is None
    assert glyph_reading("a71", font="X", in_agl=True) is None  # the Adobe Glyph List wins


def test_GN3_the_dingbats_list_is_adobes() -> None:
    assert len(ZAPF_DINGBATS) == 201
    assert (ZAPF_DINGBATS["a1"], ZAPF_DINGBATS["a50"], ZAPF_DINGBATS["a71"]) == (
        0x2701,
        0x2737,
        0x25CF,
    )


def test_GN3_glyph_names_come_from_differences_and_charsets() -> None:
    encoding = "<</BaseEncoding/MacRomanEncoding/Differences[3/a71 10/a1/a2 40/parenleft]>>"
    assert differences_names(encoding) == {"a71", "a1", "a2", "parenleft"}
    assert differences_names("/WinAnsiEncoding") == set()
    assert charset_names("/a50/a51.alt") == {"a50", "a51.alt"}
