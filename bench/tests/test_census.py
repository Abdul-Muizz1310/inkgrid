import hashlib
from pathlib import Path

import pymupdf
from hypothesis import given
from hypothesis import strategies as st

from inkgrid_bench.census import PageStats, classify, document_class, manifest, page_stats, split
from inkgrid_bench.ocr_data import BenchDoc


def test_CS1_each_class_starts_at_its_threshold() -> None:
    assert classify(PageStats(visible=49, invisible=0, image_share=0.0)) == "no_text"
    assert classify(PageStats(visible=50, invisible=0, image_share=0.0)) == "born_digital"
    assert classify(PageStats(visible=10, invisible=500, image_share=1.0)) == "no_text"
    assert classify(PageStats(visible=60, invisible=60, image_share=0.0)) == "ocr_layer"
    assert classify(PageStats(visible=60, invisible=59, image_share=0.0)) == "born_digital"
    assert classify(PageStats(visible=60, invisible=0, image_share=0.89)) == "born_digital"
    assert classify(PageStats(visible=60, invisible=0, image_share=0.90)) == "image_backed"
    assert classify(PageStats(visible=60, invisible=60, image_share=0.95)) == "ocr_layer"


def test_CS2_a_document_is_born_digital_only_when_every_page_is() -> None:
    assert document_class(["born_digital", "born_digital"]) == "born_digital"
    assert document_class(["born_digital", "image_backed", "no_text"]) == "image_backed"


def test_CS3_the_shell_counts_what_was_drawn() -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((20, 40), "Visible text", fontsize=10)  # 11 non-space characters
    page.insert_text((20, 80), "Hidden", fontsize=10, render_mode=3)  # 6, invisible
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 4, 4), False)
    page.insert_image(pymupdf.Rect(0, 0, 200, 180), stream=pix.tobytes("png"))
    stats = page_stats(page)
    assert (stats.visible, stats.invisible) == (11, 6)
    assert abs(stats.image_share - 0.9) < 1e-6


@given(st.lists(st.text(min_size=1, max_size=20), max_size=30), st.sampled_from(["olmocr", "dp"]))
def test_SP1_the_split_is_fixed_by_each_documents_hash(ids: list[str], bench: str) -> None:
    first = [split(bench, i) for i in ids]
    again = [split(bench, i) for i in reversed(ids)][::-1]
    assert first == again
    for doc_id, half in zip(ids, first, strict=True):
        digit = hashlib.sha256(f"inkgrid-m7:{bench}:{doc_id}".encode()).hexdigest()[0]
        assert half == ("dev" if digit in "01234567" else "test")


def test_CS4_the_manifest_records_each_documents_hash_classes_and_half(tmp_path: Path) -> None:
    pdf = tmp_path / "a.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((20, 40), "x" * 60, fontsize=6)
    doc.new_page(width=200, height=200)  # blank: no text
    doc.save(pdf)
    out = manifest("dpbench", "rev123", [BenchDoc("dpbench", "a", pdf, "page")])
    expected_sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert out == {
        "benchmark": "dpbench",
        "revision": "rev123",
        "documents": {
            "a": {
                "sha256": expected_sha,
                "pages": ["born_digital", "no_text"],
                "class": "no_text",
                "half": split("dpbench", "a"),
                "group": "page",
            }
        },
    }
