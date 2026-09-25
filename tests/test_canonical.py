import re

from inkgrid.model.canonical import assign_keys, content_key, normalize_ws, sha256_hex


def test_C1_content_key_folds_whitespace() -> None:
    assert content_key("paragraph", "a  b\n c") == content_key("paragraph", "a b c")


def test_C2_content_key_depends_on_kind() -> None:
    assert content_key("paragraph", "x") != content_key("heading", "x")


def test_C3_content_key_shape() -> None:
    assert re.fullmatch(r"k[0-9a-f]{16}", content_key("table", "Fee $0.40"))


def test_C4_assign_keys_suffixes_twins_in_order() -> None:
    kx, ky = content_key("p", "x"), content_key("p", "y")
    got = assign_keys([("p", "x"), ("p", "y"), ("p", "x"), ("p", "x")])
    assert got == (kx, ky, f"{kx}:2", f"{kx}:3")


def test_C5_normalize_ws_folds_unicode_spaces() -> None:
    assert normalize_ws("\u00a0a\u202fb\tc\n") == "a b c"


def test_C6_sha256_hex_of_empty_input() -> None:
    assert sha256_hex(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
