"""Token classification (docs/specs/04-text-pipeline.md section 1). It never decides structure."""

import re

from inkgrid.model.config import Lexicon

ENUMERATOR = re.compile(r"(\d{1,3}|[a-z]|[ivxlc]{1,6}|[A-Z])[.)]|\((\d{1,3}|[a-z]|[ivxlc]{1,6})\)")
SECTION_NUMBER = re.compile(r"\d+(\.\d+)*\.?|[A-Z]\.")
YEAR = re.compile(r"(19|20)\d\d")
NOTE_MARK = re.compile("\\d{1,3}|[*\u2020\u2021\u00a7\u00b6#]{1,3}")


def is_bullet(token: str, lexicon: Lexicon) -> bool:
    """True when the token is exactly one of the lexicon's bullets."""
    return token in lexicon.bullets


def enumerator(token: str) -> str | None:
    """The token as printed when it is a list or note label (`1.`, `(b)`, `iv.`), else None."""
    return token if ENUMERATOR.fullmatch(token) else None


def section_number(token: str) -> str | None:
    """The token as printed when it numbers a section (`2.1`, `C.`); a bare year is not one."""
    if YEAR.fullmatch(token):
        return None
    return token if SECTION_NUMBER.fullmatch(token) else None


def note_label(token: str) -> str | None:
    """The token as printed when it can label a footnote: an enumerator, digits, or note marks."""
    if enumerator(token) is not None or NOTE_MARK.fullmatch(token):
        return token
    return None
