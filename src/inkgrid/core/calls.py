"""Footnote call candidates (docs/specs/09-notes-calls-and-continuation.md section 2).

Calls come in co-equal forms (L7): a superscript mark, a parenthesised number at body size, and
a named reference (`see footnote 27`). A parenthesised number is admitted only by the document's
own notes, and rejected by a named drafting convention: the rule underneath them is that a marker
attaches to the end of what it annotates (a noun phrase, a value, or another marker), never to a
delimiter or a function word. The conventions and their order are the prototype's decision D-21.
"""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from inkgrid.core.lexicon import call_parts
from inkgrid.model.page import Word

Method = Literal["superscript", "parenthetical", "named"]

PAREN = re.compile(r"\((\d{1,3})\)")  # three digits: a wider pattern matches years and amounts
NAMED = re.compile(r"\bfootnotes?\s+(\d{1,3})\b", re.IGNORECASE)
LAST_GROUP = re.compile(r"\(([^()]*)\)$")
LAST_WORD = re.compile(r"([A-Za-z]+)[^A-Za-z]*$")
CITATION_GROUP = re.compile(r"[a-z]|[ivxl]{1,4}")  # `202(a)(11)`: a single letter or roman numeral
ANCHOR_END = re.compile(r"[\w%.\]]$")
DELIMITERS = (",", ";", ":")
SPELLED = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
    9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
    15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty",
    30: "thirty", 40: "forty", 50: "fifty", 60: "sixty",
}  # fmt: skip
FUNCTION_WORDS = frozenset(
    {
        "and", "or", "except", "excluding", "including", "than", "that", "if", "of", "to", "for",
        "in", "by", "with", "the", "a", "an", "is", "are", "be", "as", "at", "on", "from",
        "provided", "least", "plus", "per", "over", "under", "between",
    }
)  # fmt: skip


@dataclass(frozen=True, slots=True)
class Candidate:
    """A call candidate: its label and method, and the convention that rejected it, if one did."""

    label: str
    method: Method
    reason: str | None = None


def superscript_calls(words: Sequence[Word]) -> list[Candidate]:
    """One call per label each superscript word carries (spec 09 section 2.1)."""
    return [
        Candidate(label, "superscript")
        for w in words
        if w.superscript
        for label in call_parts(w.text)
    ]


def _rejection(text: str, start: int, n: int) -> str | None:
    """The drafting convention the `(n)` at `start` follows, or None when it is a call (s. 2.2).

    The conventions are tried in order and the first that holds decides; a `None` rule accepts.
    """
    before = text[:start]
    pb = before.rstrip()
    glued = pb == before  # no space before `(`
    word_match = LAST_WORD.search(pb)
    word = word_match.group(1) if word_match else ""
    group = LAST_GROUP.search(pb)
    rules: tuple[tuple[str | None, Callable[[], bool]], ...] = (
        ("clause-initial", lambda: not pb),
        ("sub-clause-enumerator", lambda: pb.endswith(DELIMITERS)),
        (
            "statutory-citation",
            lambda: (
                pb.endswith(")")
                and glued
                and group is not None
                and CITATION_GROUP.fullmatch(group.group(1)) is not None
            ),
        ),
        (None, lambda: pb.endswith(")")),  # a marker run, or a marker after an aside
        ("attached-to-number", lambda: glued and pb[-1].isdigit()),
        ("spelled-number-gloss", lambda: bool(word) and word.casefold() == SPELLED.get(n)),
        ("function-word", lambda: word.islower() and word in FUNCTION_WORDS),
        ("no-anchor", lambda: ANCHOR_END.search(pb) is None),
    )
    return next((reason for reason, holds in rules if holds()), None)


def parenthetical_calls(text: str, register: frozenset[str]) -> list[Candidate]:
    """Every `(n)` some note carries, accepted or rejected with its convention (s. 2.2)."""
    out: list[Candidate] = []
    for match in PAREN.finditer(text):
        label = match.group(1)
        if label not in register:
            continue  # nothing admits it: no candidate at all
        reason = _rejection(text, match.start(), int(label))
        out.append(Candidate(label, "parenthetical", reason))
    return out


def named_calls(text: str) -> list[Candidate]:
    """Every `footnote n` (s. 2.3): the word says what it is."""
    return [Candidate(m.group(1), "named") for m in NAMED.finditer(text)]


def calls_in(
    kind: str,
    words: Sequence[Word],
    text: str,
    register: frozenset[str],
    *,
    own_label: str | None = None,
) -> list[Candidate]:
    """A block's (or a cell's) call candidates, in method order: superscript, parenthetical, named.

    A footnote's first word is its label, not a call, and a note never calls its own label.
    """
    marks = words[1:] if kind == "footnote" else words
    found = [*superscript_calls(marks), *parenthetical_calls(text, register), *named_calls(text)]
    return [c for c in found if c.label != own_label]
