"""A tool's page as Markdown with HTML tables (docs/specs/18-ocr-benchmarks.md section 3).

Pure. `pipe_to_html` is the one converter every tool's GFM pipe tables go through when a scorer
reads only HTML tables; `inkgrid_markdown` is inkgrid's own Markdown with each table written by its
public `Table.to_html()`, so spans survive.
"""

import re
from html import escape

from inkgrid.model.document import Document

SEPARATOR = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")
LONE_SURROGATE = re.compile("[\ud800-\udfff]")


def scorable(text: str) -> str:
    """The text as a scorer reads it from a UTF-8 file: a lone surrogate becomes U+FFFD."""
    return LONE_SURROGATE.sub("\ufffd", text)


def _cells(line: str) -> list[str]:
    """A pipe row's cells: outer pipes dropped, escaped pipes kept as text, each cell stripped."""
    s = line.strip().removeprefix("|")
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [part.strip().replace("\\|", "|") for part in UNESCAPED_PIPE.split(s)]


def _html(header: list[str], body: list[list[str]]) -> str:
    width = len(header)

    def row(cells: list[str], tag: str) -> str:
        padded = (cells + [""] * width)[:width]
        return (
            "<tr>" + "".join(f"<{tag}>{escape(c, quote=False)}</{tag}>" for c in padded) + "</tr>"
        )

    parts = ["<table>", "<thead>", row(header, "th"), "</thead>"]
    if body:
        parts += ["<tbody>", *(row(r, "td") for r in body), "</tbody>"]
    parts.append("</table>")
    return "".join(parts)


def pipe_to_html(markdown: str) -> str:
    """The Markdown with every GFM pipe table written as HTML; the text around it unchanged.

    A table is a row with a pipe followed by a delimiter row with as many cells; its body runs to
    the first line without a pipe. The first row becomes `<thead>`; a short body row is padded and a
    long one cut to the header's width, as GFM reads them.
    """
    lines = markdown.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if (
            "|" in line
            and i + 1 < len(lines)
            and SEPARATOR.match(lines[i + 1])
            and len(_cells(lines[i + 1])) == len(_cells(line))
        ):
            header = _cells(line)
            j = i + 2
            body = []
            while j < len(lines) and "|" in lines[j] and lines[j].strip():
                body.append(_cells(lines[j]))
                j += 1
            out.append(_html(header, body))
            i = j
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def inkgrid_markdown(doc: Document) -> str:
    """The document as inkgrid writes it, each table by its `Table.to_html()` in its own place.

    `to_markdown` writes the blocks in order, so each table's pipe table is the first one at or
    after the end of the table before it: a table whose pipe table repeats another's, or begins
    another's, still gets its own HTML. A table whose pipe table is not there is refused.
    """
    text = doc.to_markdown()
    parts: list[str] = []
    at = 0
    for table in doc.tables():
        pipe = table.to_markdown()
        found = text.find(pipe, at)
        if found < 0:
            msg = f"table {table.id}'s Markdown is not in the document's Markdown"
            raise ValueError(msg)
        parts += [text[at:found], table.to_html()]
        at = found + len(pipe)
    parts.append(text[at:])
    return "".join(parts)
