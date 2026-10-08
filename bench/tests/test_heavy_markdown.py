"""Heavy: each competitor in its pinned environment on one generated page (spec 18 s. 8, AD3-AD5).

Run with `uv run pytest -m heavy --no-cov`; they build or reuse the tools' environments and load
their models, so they are kept out of the default run and out of CI.
"""

from pathlib import Path

import pytest

import pdf_factory
from inkgrid_bench import run
from inkgrid_bench.tables import NDocument

pytestmark = pytest.mark.heavy
PARAGRAPHS = (pdf_factory.TABLE_BEFORE[0], pdf_factory.TABLE_AFTER[0])


def page(tmp_path: Path) -> Path:
    pdf = tmp_path / "page.pdf"
    pdf.write_bytes(pdf_factory.table_between_paragraphs())
    return pdf


def reading(name: str, pdf: Path) -> NDocument:
    tool = next(t for t in run.tools(run.config()) if t.name == name)
    if tool.batch:
        ((_, doc),) = run.read_batch(
            run.command(tool), [pdf], tool=name, version="test", env=run.tool_env(tool)
        )
        return doc
    return run.read_document(run.command(tool), pdf, tool=name, version="test", timeout=600)


def words(text: str) -> list[str]:
    return [w for w in text.replace("|", " ").split() if w.isalnum()]


@pytest.mark.parametrize("name", ["pymupdf4llm", "markitdown", "liteparse"])
def test_AD3_a_text_layer_converter_writes_both_paragraphs(tmp_path: Path, name: str) -> None:
    doc = reading(name, page(tmp_path))
    assert doc.error is None
    flat = " ".join(words(doc.markdown))
    for paragraph in PARAGRAPHS:
        assert " ".join(words(paragraph)) in flat


@pytest.mark.parametrize("name", ["docling", "marker"])
def test_AD4_a_heavy_tool_writes_its_page_with_an_html_table(tmp_path: Path, name: str) -> None:
    doc = reading(name, page(tmp_path))
    assert doc.error is None
    assert doc.tables
    assert "<table" in doc.markdown
    flat = " ".join(words(doc.markdown))
    for paragraph in PARAGRAPHS:
        assert " ".join(words(paragraph)) in flat


def test_AD5_inkgrid_on_tesseracts_words_writes_its_page(tmp_path: Path) -> None:
    doc = reading("inkgrid-ocr", page(tmp_path))
    assert doc.error is None
    flat = " ".join(words(doc.markdown))
    for paragraph in PARAGRAPHS:
        assert " ".join(words(paragraph)) in flat
    assert ("<table>" in doc.markdown) == bool(doc.tables)
