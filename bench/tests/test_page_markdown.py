from html.parser import HTMLParser

from hypothesis import given
from hypothesis import strategies as st

import inkgrid
import pdf_factory
from inkgrid_bench.page_markdown import inkgrid_markdown, pipe_to_html


class Cells(HTMLParser):
    """The text of every th/td, in document order, and how many of them were th."""

    def __init__(self) -> None:
        super().__init__()
        self.cells: list[str] = []
        self.heads = 0
        self._in = False

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag in ("th", "td"):
            self.cells.append("")
            self.heads += tag == "th"
            self._in = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("th", "td"):
            self._in = False

    def handle_data(self, data: str) -> None:
        if self._in:
            self.cells[-1] += data


def cells_of(html: str) -> Cells:
    parser = Cells()
    parser.feed(html)
    return parser


def test_MD1_a_pipe_table_becomes_html_and_the_text_around_it_stays() -> None:
    md = "Intro text.\n\n| A | B \\| C |\n| --- | :---: |\n| 1 | <2> |\n| 3 |\n\nAfter."
    out = pipe_to_html(md)
    assert out.startswith("Intro text.\n\n<table>")
    assert out.endswith("</table>\n\nAfter.")
    assert "<thead><tr><th>A</th><th>B | C</th></tr></thead>" in out
    assert "<tr><td>1</td><td>&lt;2&gt;</td></tr>" in out
    assert "<tr><td>3</td><td></td></tr>" in out  # a short row is padded
    assert pipe_to_html("a | b\nno table here") == "a | b\nno table here"
    assert pipe_to_html("no tables") == "no tables"


WORD = st.text(alphabet=st.characters(categories=["L", "N"]), min_size=1, max_size=8)


@given(
    st.integers(1, 5).flatmap(
        lambda n: st.lists(st.lists(WORD, min_size=n, max_size=n), min_size=2, max_size=6)
    )
)
def test_MD1_every_cell_survives_the_conversion(rows: list[list[str]]) -> None:
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * len(rows[0])]
    lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    parsed = cells_of(pipe_to_html("\n".join(lines)))
    assert parsed.cells == [c for r in rows for c in r]
    assert parsed.heads == len(rows[0])


def test_MD2_inkgrid_writes_its_tables_as_html_and_leaves_furniture_out() -> None:
    doc = inkgrid.read(pdf_factory.table_between_paragraphs())
    (table,) = doc.tables()
    out = inkgrid_markdown(doc)
    assert out == doc.to_markdown().replace(table.to_markdown(), table.to_html())
    assert "<table>" in out
    assert "| --- |" not in out
    furnished = inkgrid.read(pdf_factory.furnished())
    text = inkgrid_markdown(furnished)
    assert pdf_factory.FURNISHED_HEADER not in text
    assert "Page 1 of 5" not in text
    assert "alpha tier charges" in text
