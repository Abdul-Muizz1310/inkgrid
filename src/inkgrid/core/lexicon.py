"""Token classification (docs/specs/04-text-pipeline.md section 1). It never decides structure."""

import re

from inkgrid.model.config import Lexicon

ENUMERATOR = re.compile(r"(\d{1,3}|[a-z]|[ivxlc]{1,6}|[A-Z])[.)]|\((\d{1,3}|[a-z]|[ivxlc]{1,6})\)")
SECTION_NUMBER = re.compile(r"\d+(\.\d+)*\.?|[A-Z]\.")
YEAR = re.compile(r"(19|20)\d\d")
# Values (docs/specs/06-ruled-tables.md section 1): numbers, money, units, ranges, placeholders.
_SIGN = "[-+\u2212]"
_GROUP = "[,.'\u00a0\u202f ]"
_NUMBER = rf"{_SIGN}?(?:\d{{1,3}}(?:{_GROUP}\d{{3}})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
_SYMBOL = "[$\u20ac\u00a3\u00a5\u20b9\u20a3R]"
_CURRENCY = rf"(?:{_SYMBOL}|[A-Z]{{3}})"
_MAGNITUDE = "(?:bn|mn|k|m|K|M|B)"
_UNIT = rf"(?:%|bps|bp|\u2030|{_SYMBOL}|[A-Z]{{3}})"
_VALUE = rf"{_SIGN}?(?:{_CURRENCY} ?)?{_NUMBER}{_MAGNITUDE}?(?: ?{_UNIT})?[*\u2020\u2021]*"
VALUE = re.compile(
    rf"{_VALUE}|\( ?{_VALUE} ?\)|{_VALUE} ?(?:-|\u2013|to) ?{_VALUE}"
    "|\u2014|\u2013|-|(?i:n/a|nil|free)"
)
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


def is_value(text: str) -> bool:
    """True when the whole text reads as one value: a number, money, a unit, a range, a placeholder.

    A bare year (1900-2099) is a label, not a value: years head columns.
    """
    text = text.strip()
    if YEAR.fullmatch(text):
        return False
    return VALUE.fullmatch(text) is not None

