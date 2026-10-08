from pathlib import Path

import inkgrid
import pdf_factory
from inkgrid_bench import run
from inkgrid_bench.adapters import inkgrid_read
from inkgrid_bench.heavy import unstructured_markdown
from inkgrid_bench.page_markdown import inkgrid_markdown
from inkgrid_bench.tables import NDocument, NPage, Output

UPRIGHT = (NPage(box=(0.0, 0.0, 612.0, 792.0), rotation=0),)


def test_AD0_a_reading_keeps_its_markdown_and_an_older_one_reads_empty() -> None:
    doc = NDocument(tool="t", version="1", pdf_sha256="x", pages=UPRIGHT, markdown="# A\n\nb")
    assert NDocument.from_json(doc.to_json()) == doc
    older = (
        '{"error": null, "pages": [{"box": [0, 0, 612, 792], "rotation": 0}], "pdf_sha256": "x", '
        '"seconds": 0.0, "tables": [], "tool": "t", "version": "1"}'
    )
    assert NDocument.from_json(older).markdown == ""


def test_AD1_inkgrid_reads_its_tables_and_its_page_markdown(tmp_path: Path) -> None:
    pdf = tmp_path / "page.pdf"
    pdf.write_bytes(pdf_factory.table_between_paragraphs())
    out = inkgrid_read.read(pdf)
    assert isinstance(out, Output)
    doc = inkgrid.read(pdf)
    assert list(out.tables) == inkgrid_read.tables_of(doc)
    assert out.markdown == inkgrid_markdown(doc)
    reading = run.read_document(
        run.command(next(t for t in run.tools(run.config()) if t.name == "inkgrid")),
        pdf,
        tool="inkgrid",
        version="test",
    )
    assert reading.error is None
    assert reading.markdown == out.markdown


def element(kind: str, text: str, **metadata: object) -> dict[str, object]:
    return {"type": kind, "text": text, "metadata": metadata}


def test_AD2_unstructured_elements_become_markdown_without_furniture() -> None:
    elements = [
        element("Header", "Annual report 2025"),
        element("Title", "Fees"),
        element("NarrativeText", "Every member pays the fee below."),
        element("ListItem", "Clearing"),
        element(
            "Table", "Fee 1.00", text_as_html="<table><tr><td>Fee</td><td>1.00</td></tr></table>"
        ),
        element("Image", "a chart"),
        element("Footer", "Confidential"),
        element("PageNumber", "7"),
    ]
    assert unstructured_markdown(elements) == (
        "# Fees\n\nEvery member pays the fee below.\n\n- Clearing\n\n"
        "<table><tr><td>Fee</td><td>1.00</td></tr></table>"
    )
    plain = [element("Table", "Fee 1.00")]
    assert unstructured_markdown(plain) == "Fee 1.00"
