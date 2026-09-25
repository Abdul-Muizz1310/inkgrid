"""Canonical helpers: whitespace folding, content-derived keys, digests."""

import hashlib
from collections import Counter
from collections.abc import Sequence

KEY_HEX = 16


def normalize_ws(text: str) -> str:
    """Fold every run of whitespace (including U+00A0, U+202F, tabs, newlines) to one space."""
    return " ".join(text.split())


def content_key(kind: str, text: str) -> str:
    """A key derived from a block's kind and its whitespace-folded text."""
    digest = hashlib.sha256(f"{kind}\x1f{normalize_ws(text)}".encode()).hexdigest()
    return f"k{digest[:KEY_HEX]}"


def assign_keys(items: Sequence[tuple[str, str]]) -> tuple[str, ...]:
    """Keys for `(kind, text)` pairs in reading order; the n-th identical twin gets `:n`."""
    seen: Counter[str] = Counter()
    keys: list[str] = []
    for kind, text in items:
        key = content_key(kind, text)
        seen[key] += 1
        keys.append(key if seen[key] == 1 else f"{key}:{seen[key]}")
    return tuple(keys)


def sha256_hex(data: bytes) -> str:
    """The lowercase hex SHA-256 digest of `data`."""
    return hashlib.sha256(data).hexdigest()
