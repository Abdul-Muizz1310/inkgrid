import shutil
import subprocess
from pathlib import Path

import pytest

from inkgrid_bench.render import icdar_reg_xml, icdar_str_xml, soric_box, table_html
from inkgrid_bench.tables import NCell, NDocument, NPage, NTable

CACHE = Path.home() / ".cache" / "inkgrid-bench"
JAVA = CACHE / "tools" / "jdk-17.0.20.1+1-jre" / "bin" / "java"
JAR = CACHE / "tools" / "dataset-tools-20180206.jar"
PORTRAIT = NPage(box=(0.0, 0.0, 595.0, 842.0), rotation=0)


def table() -> NTable:
    cells = (
        NCell(0, 0, cols=2, text="Fee & charge", header=True),
        NCell(1, 0, text="Equity"),
        NCell(1, 1, text="0.30"),
    )
    return NTable(page=1, bbox=(100.0, 299.0, 482.0, 391.0), cells=cells)


def document() -> NDocument:
    return NDocument(
        tool="t", version="1", pdf_sha256="0" * 64, pages=(PORTRAIT,), tables=(table(),)
    )


def test_RD2_html_keeps_spans_and_header_rows() -> None:
    html = table_html(table(), header=True)
    assert html.startswith('<table><thead><tr><th colspan="2">Fee &amp; charge</th></tr></thead>')
    assert "<tbody><tr><td>Equity</td><td>0.30</td></tr></tbody></table>" in html
    plain = table_html(table(), header=False)
    assert "<thead>" not in plain
    assert plain.startswith('<table><tbody><tr><td colspan="2">Fee &amp; charge</td>')


def test_RD3_boxes_go_to_soric_pixels_as_their_ground_truth_does() -> None:
    # eu-001's first ICDAR region (100, 451, 482, 543) is their ground-truth [119, 355, 573, 464]
    box = soric_box((100.0, 842.0 - 543.0, 482.0, 842.0 - 451.0), PORTRAIT)
    assert [round(v) for v in box] == [119, 355, 572, 464]
    # eu-015 page 1 (/Rotate 90): ICDAR (60, 292, 356, 505) is their [101, 151, 599, 509]
    turned = NPage(box=(0.0, 0.0, 595.0, 842.0), rotation=90)
    box = soric_box((60.0, 842.0 - 505.0, 356.0, 842.0 - 292.0), turned)
    assert [round(v) for v in box] == [101, 151, 598, 509]


def test_RD1_icdar_xml_carries_regions_and_cells() -> None:
    reg = icdar_reg_xml(document(), "x.pdf")
    assert '<bounding-box x1="100" y1="451" x2="482" y2="543"' in reg
    structure = icdar_str_xml(document(), "x.pdf")
    assert structure.count("<cell ") == 3
    assert 'start-row="0" start-col="0" end-row="0" end-col="1"' in structure
    assert "<content>Fee &amp; charge</content>" in structure


@pytest.mark.skipif(
    not (JAVA.exists() and JAR.exists()), reason="the ICDAR jar and its JRE are not cached"
)
def test_RD1_the_competition_jar_scores_a_rendering_against_itself(tmp_path: Path) -> None:
    import pdf_factory  # noqa: PLC0415 - tests/support, on the path during the suite

    (tmp_path / "x.pdf").write_bytes(pdf_factory.ruled_grid())
    structure = icdar_str_xml(document(), "x.pdf")
    (tmp_path / "x-str.xml").write_text(structure, encoding="utf-8")
    shutil.copy(tmp_path / "x-str.xml", tmp_path / "x-result.xml")
    out = subprocess.run(
        [str(JAVA), "-jar", str(JAR), "-str", "x-str.xml", "x-result.xml", "x.pdf"],
        cwd=tmp_path, capture_output=True, text=True, check=True, timeout=120,
    )  # fmt: skip
    (line,) = [x for x in out.stdout.splitlines() if x.startswith("Table 1:")]
    assert line.count("= 1.0") == 2, line


def test_RD1_characters_xml_forbids_are_dropped_from_icdar_files() -> None:
    # PyMuPDF on practice us-008 (measured) returns U+0000 inside a cell
    import xml.etree.ElementTree as ET  # noqa: PLC0415

    cells = (NCell(0, 0, text="0.30\x00 bp\x0b"), NCell(0, 1, text="tab\tok"))
    doc = NDocument(
        tool="t", version="1", pdf_sha256="0" * 64, pages=(PORTRAIT,),
        tables=(NTable(page=1, bbox=(100.0, 299.0, 482.0, 391.0), cells=cells),),
    )  # fmt: skip
    structure = icdar_str_xml(doc, "x.pdf")
    contents = [c.text for c in ET.fromstring(structure.encode()).iter("content")]  # noqa: S314
    assert contents == ["0.30 bp", "tab\tok"]
