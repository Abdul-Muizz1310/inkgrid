import re
import struct

import pymupdf
import pytest

import inkgrid
import pdf_factory
from doc_builder import B, build, line
from inkgrid.model.verification import Verifier
from inkgrid.read.pymupdf_reader import render_pages
from inkgrid.render.inspector import build_inspector, inspector_html
from lattice_builder import read_with_tables


def page_sections(html: str) -> list[str]:
    return re.findall(r'<section class="page" id="(page-\d+)"', html)


def test_IN1_a_page_is_its_image_with_one_box_per_region() -> None:
    data = pdf_factory.simple_text()
    doc = inkgrid.read(data)
    html = build_inspector(doc, data)
    assert page_sections(html) == ["page-1"]
    assert len(re.findall(r'<image href="data:image/png;base64,[A-Za-z0-9+/=]+"', html)) == 1
    regions = sum(1 for b in doc.blocks for r in b.regions if r.page == 1)
    assert html.count("<rect ") == regions


def test_IN2_document_text_is_escaped() -> None:
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 100), "<script>alert(1)</script> fee", fontsize=10)
    data = pdf.tobytes()
    html = build_inspector(inkgrid.read(data), data)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script" not in html


def test_IN3_pages_appear_in_order() -> None:
    data = pdf_factory.multipage(3)
    assert page_sections(build_inspector(inkgrid.read(data), data)) == [
        "page-1",
        "page-2",
        "page-3",
    ]


def test_IN4_the_page_makes_no_external_request() -> None:
    data = pdf_factory.two_column()
    html = build_inspector(inkgrid.read(data), data)
    assert "http://" not in html
    assert "https://" not in html


def test_IN5_one_image_is_needed_per_page() -> None:
    doc = inkgrid.read(pdf_factory.multipage(3))
    with pytest.raises(ValueError, match="3 pages"):
        inspector_html(doc, [b"", b""])


def test_IN6_a_different_pdf_is_refused() -> None:
    doc = inkgrid.read(pdf_factory.simple_text())
    with pytest.raises(ValueError, match="SHA-256"):
        build_inspector(doc, pdf_factory.two_column())


def test_IN7_pages_render_unrotated() -> None:
    (png,) = render_pages(pdf_factory.rotated(), None, 72)
    assert png is not None
    width, height = struct.unpack(">II", png[16:24])
    page = inkgrid.read_pages(pdf_factory.rotated()).pages[0]
    assert (width, height) == (round(page.width), round(page.height))


def test_IN8_a_page_that_cannot_render_is_said_so() -> None:
    data = pdf_factory.nested_graphics_states()
    html = build_inspector(inkgrid.read(data), data)
    assert "could not be rendered" in html
    assert "<image" not in html


def test_IN9_rendering_stops_where_loading_stops() -> None:
    assert len(render_pages(pdf_factory.null_second_kid(), None, 36)) == 1


def test_IN10_each_card_names_its_kind_detail() -> None:
    doc = build(
        [
            B("heading", line(["Fees"], y=100), fields={"level": 2}),
            B("list_item", line(["a)", "item"], y=120), fields={"label": "a)"}),
            B("footnote", line(["3", "note"], y=140), fields={"label": "3"}),
            B("definition", line(["Term", "body"], y=160), fields={"term": "Term", "body": "body"}),
            B("furniture", line(["Page", "1"], y=700), fields={"role": "footer"}),
        ]
    )
    html = inspector_html(doc, [None])
    for detail in (
        "heading (level 2)",
        "list_item (label a))",
        "footnote (label 3)",
        "definition (term Term)",
        "furniture (footer)",
    ):
        assert detail in html


def test_EX5_the_inspector_draws_every_cell() -> None:
    data = pdf_factory.ruled_grid()
    html = build_inspector(read_with_tables(data), data)
    assert html.count('<rect class="cell"') == 10


# --- Verification overlays (spec 10 section 8) ----------------------------------------------------


def report_for(doc: inkgrid.Document, *defects: inkgrid.Defect) -> inkgrid.VerificationReport:
    pages = tuple(
        inkgrid.PageCheck(number=p.number, status="verified", ink_chars=0) for p in doc.pages
    )
    return inkgrid.VerificationReport(
        source=doc.source,
        verifier=Verifier(inkgrid="0.1.0.dev0", pypdfium2="5.13.0", pdfium="153.0.7999.0"),
        pages=pages,
        defects=defects,
    )


def text_defect(detail: str = "'Rate' has 1 of its 4 characters in the cell") -> inkgrid.Defect:
    return inkgrid.Defect(
        code=inkgrid.DefectCode.TEXT,
        page=1,
        block="b1",
        cell=(0, 1),
        text="Rate",
        bbox=inkgrid.Rect(100, 100, 160, 120),
        detail=detail,
    )


def test_VI1_a_defect_is_drawn_on_its_page_and_listed_beside_it() -> None:
    data = pdf_factory.ruled_grid()
    doc = inkgrid.read(data)
    html = build_inspector(doc, data, report=report_for(doc, text_defect()))
    (page,) = re.findall(r'<section class="page" id="page-1">.*?</section>', html, re.DOTALL)
    assert '<rect class="defect d-text" x="100.0" y="100.0" width="60.0" height="20.0"' in page
    assert "has 1 of its 4 characters" in page
    assert "verified: 1 defect, 0 advisories" in html


def test_VI2_without_a_report_nothing_is_added() -> None:
    data = pdf_factory.ruled_grid()
    html = build_inspector(inkgrid.read(data), data)
    assert "defect" not in html
    assert "advisor" not in html
    assert "verified:" not in html


def test_VI3_a_report_of_another_document_is_refused() -> None:
    doc = inkgrid.read(pdf_factory.ruled_grid())
    other = inkgrid.read(pdf_factory.simple_text())
    with pytest.raises(ValueError, match="report"):
        inspector_html(doc, [None], report_for(other))


def test_VI4_defect_text_is_escaped() -> None:
    data = pdf_factory.ruled_grid()
    doc = inkgrid.read(data)
    html = build_inspector(doc, data, report=report_for(doc, text_defect("holds <b>x</b>")))
    assert "holds &lt;b&gt;x&lt;/b&gt;" in html
    assert "<b>x</b>" not in html


def test_VI1_an_unverified_page_says_so() -> None:
    data = pdf_factory.simple_text()
    doc = inkgrid.read(data)
    report = inkgrid.VerificationReport(
        source=doc.source,
        verifier=Verifier(inkgrid="0.1.0.dev0", pypdfium2="5.13.0", pdfium="153.0.7999.0"),
        pages=(inkgrid.PageCheck(number=1, status="unverified", ink_chars=0),),
        defects=(
            inkgrid.Defect(
                code=inkgrid.DefectCode.UNVERIFIED, page=1, detail="PDFium cannot load page 1"
            ),
        ),
    )
    html = build_inspector(doc, data, report=report)
    assert "This page is unverified" in html
    assert "PDFium cannot load page 1" in html
