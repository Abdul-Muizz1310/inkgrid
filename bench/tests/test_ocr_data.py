import json
from pathlib import Path

import pytest

from inkgrid_bench.ocr_data import (
    BenchDoc,
    dpbench_docs,
    excluded,
    olmocr_docs,
    omnidocbench_docs,
    parsebench_docs,
    scored,
)


def touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4")
    return path


def jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_DS1_each_benchmark_lists_every_document_once_with_its_group(tmp_path: Path) -> None:
    olm = tmp_path / "olm"
    jsonl(
        olm / "headers_footers.jsonl",
        [{"pdf": "headers_footers/a.pdf"}, {"pdf": "headers_footers/a.pdf"}],
    )
    jsonl(olm / "multi_column.jsonl", [{"pdf": "multi_column/b.pdf"}])
    jsonl(olm / "table_tests.jsonl", [{"pdf": "tables/c.pdf"}])
    jsonl(olm / "long_tiny_text.jsonl", [{"pdf": "long_tiny_text/d.pdf"}])
    for name in ("headers_footers/a", "multi_column/b", "tables/c", "long_tiny_text/d"):
        touch(olm / "pdfs" / f"{name}.pdf")
    docs = olmocr_docs(olm)
    assert [(d.id, d.group) for d in docs] == [
        ("headers_footers/a.pdf", "headers_footers"),
        ("long_tiny_text/d.pdf", "long_tiny_text"),
        ("multi_column/b.pdf", "multi_column"),
        ("tables/c.pdf", "tables"),
    ]
    assert docs[0].pdf == olm / "pdfs" / "headers_footers" / "a.pdf"

    omni = tmp_path / "omni"
    pages = [
        {
            "page_info": {
                "image_path": "images/x.pdf_1.jpg",
                "page_attribute": {"language": "english"},
            }
        },
        {
            "page_info": {
                "image_path": "y_3.jpg",
                "page_attribute": {"language": "simplified_chinese"},
            }
        },
    ]
    (omni / "ori_pdfs").mkdir(parents=True)
    (omni / "OmniDocBench.json").write_text(json.dumps(pages))
    touch(omni / "ori_pdfs" / "x.pdf_1.pdf")
    touch(omni / "ori_pdfs" / "y_3.pdf")
    assert [(d.id, d.group) for d in omnidocbench_docs(omni)] == [
        ("x.pdf_1", "english"),
        ("y_3", "simplified_chinese"),
    ]

    pb = tmp_path / "pb"
    jsonl(pb / "table.jsonl", [{"pdf": "docs/table/t1.pdf", "category": "table"}])
    jsonl(
        pb / "text_content.jsonl",
        [
            {"pdf": "docs/text/s.pdf", "category": "text_content", "tags": ["easy", "simple"]},
            {"pdf": "docs/text/s.pdf", "category": "text_content", "tags": ["simple"]},
            {"pdf": "docs/text/o.pdf", "category": "text_content", "tags": ["hard", "ocr"]},
        ],
    )
    for name in ("table/t1", "text/s", "text/o"):
        touch(pb / "docs" / f"{name}.pdf")
    assert [(d.id, d.group) for d in parsebench_docs(pb)] == [
        ("table/t1", "table"),
        ("text/o", "text_ocr"),
        ("text/s", "text_simple"),
    ]

    dp = tmp_path / "dp"
    touch(dp / "pdfs" / "02.pdf")
    touch(dp / "pdfs" / "01.pdf")
    assert [(d.id, d.group) for d in dpbench_docs(dp)] == [("01", "page"), ("02", "page")]

    (olm / "pdfs" / "tables" / "c.pdf").unlink()
    with pytest.raises(FileNotFoundError, match=r"tables/c\.pdf"):
        olmocr_docs(olm)


def test_SL1_only_born_digital_documents_in_a_scored_group_are_scored(tmp_path: Path) -> None:
    def doc(doc_id: str, group: str) -> BenchDoc:
        return BenchDoc("parsebench", doc_id, tmp_path / f"{doc_id}.pdf", group)

    docs = [
        doc("table/a", "table"),
        doc("text/b", "text_simple"),
        doc("text/c", "text_ocr"),  # a scan's tag: never scored
        doc("text/d", "text_multilang"),
        doc("table/e", "table"),
    ]
    census = {
        "table/a": {"class": "born_digital"},
        "text/b": {"class": "born_digital"},
        "text/c": {"class": "born_digital"},
        "text/d": {"class": "born_digital"},
        "table/e": {"class": "image_backed"},
    }
    assert [d.id for d in scored(docs, census)] == ["table/a", "text/b", "text/d"]
    with pytest.raises(ValueError, match="text/x"):  # a document the census never classified
        scored([*docs, doc("text/x", "text_simple")], census)
    with pytest.raises(ValueError, match="text_new"):  # a group spec 18 never named
        scored([doc("text/y", "text_new")], {"text/y": {"class": "born_digital"}})
    pages = [BenchDoc("dpbench", "01", tmp_path / "01.pdf", "page")]
    assert scored(pages, {"01": {"class": "born_digital"}}) == pages


def test_SL1_every_document_not_scored_is_listed_by_its_class() -> None:
    census = {
        "table/a": {"class": "born_digital", "group": "table"},
        "text/b": {"class": "no_text", "group": "text_simple"},
        "text/c": {"class": "born_digital", "group": "text_ocr"},
        "text/d": {"class": "ocr_layer", "group": "text_ocr"},
        "text/e": {"class": "no_text", "group": "text_misc"},
    }
    assert excluded(census, {"table/a"}) == {
        "no_text": ["text/b", "text/e"],
        "ocr_layer": ["text/d"],
        "group": ["text/c (text_ocr)"],
    }
