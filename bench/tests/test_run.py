import json
import sys
from pathlib import Path

import pytest

import pdf_factory
from inkgrid_bench import pages, run
from inkgrid_bench.adapters import _cli, ground_truth, inkgrid_read
from inkgrid_bench.tables import NPage

DATA = Path(__file__).parent / "data"
PY = sys.executable


def test_the_adapter_cli_writes_tables_and_the_reads_own_seconds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf, out = tmp_path / "grid.pdf", tmp_path / "out.json"
    pdf.write_bytes(pdf_factory.ruled_grid())
    monkeypatch.setattr(sys, "argv", ["adapter", str(pdf), str(out)])
    assert _cli.main(inkgrid_read.read) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["tables"]) == 1
    assert 0 < data["seconds"] < 60


@pytest.mark.parametrize(
    ("data", "box", "rotation"),
    [
        (pdf_factory.ruled_grid(), (0.0, 0.0, 612.0, 792.0), 0),
        (pdf_factory.ruled_grid(cropbox=(50, 50, 562, 742)), (50.0, 50.0, 562.0, 742.0), 0),
        (
            pdf_factory.ruled_grid(mediabox=(-100, -100, 512, 692)),
            (-100.0, -100.0, 512.0, 692.0),
            0,
        ),
        (pdf_factory.ruled_grid(rotation=90), (0.0, 0.0, 612.0, 792.0), 90),
    ],
)
def test_page_frames_are_the_clipped_box_in_user_space_and_the_rotation(
    data: bytes, box: tuple[float, ...], rotation: int, tmp_path: Path
) -> None:
    pdf = tmp_path / "p.pdf"
    pdf.write_bytes(data)
    assert pages.frames(pdf) == (NPage(box=box, rotation=rotation),)


def test_the_ground_truth_reads_as_a_tool(tmp_path: Path) -> None:
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(pdf_factory.blank())
    (tmp_path / "x-str.xml").write_text((DATA / "icdar-str-two-cells.xml").read_text())
    (table,) = ground_truth.read(pdf)
    assert table.page == 1
    assert table.bbox == (100.0, 50.0, 300.0, 102.0)  # blank() is a 612 x 792 page
    assert [(c.row, c.col, c.text) for c in table.cells] == [(0, 0, "Fee"), (0, 1, "0.30\nbp")]


def fake(tmp_path: Path, body: str) -> list[str]:
    script = tmp_path / "adapter.py"
    script.write_text("import json, sys, time\n" + body)
    return [PY, str(script)]


def test_a_crash_is_recorded_as_no_tables(tmp_path: Path) -> None:
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(pdf_factory.blank())
    cmd = fake(tmp_path, "sys.stderr.write('Traceback\\nValueError: bad page\\n'); sys.exit(1)")
    doc = run.read_document(cmd, pdf, tool="t", version="1", timeout=30)
    assert doc.tables == ()
    assert doc.error == "ValueError: bad page"
    assert doc.pages == pages.frames(pdf)


def test_a_timeout_is_recorded_as_no_tables(tmp_path: Path) -> None:
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(pdf_factory.blank())
    doc = run.read_document(fake(tmp_path, "time.sleep(30)"), pdf, tool="t", version="1", timeout=1)
    assert doc.tables == ()
    assert doc.error == "timeout after 1 s"


def test_output_that_breaks_the_table_contract_is_a_crash(tmp_path: Path) -> None:
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(pdf_factory.blank())
    overlap = [{"page": 1, "bbox": [0, 0, 1, 1], "cells": [
        {"row": 0, "col": 0, "cols": 2}, {"row": 0, "col": 1},
    ]}]  # fmt: skip
    body = f"json.dump({{'tables': {overlap!r}, 'seconds': 0.1}}, open(sys.argv[2], 'w'))"
    doc = run.read_document(fake(tmp_path, body), pdf, tool="t", version="1", timeout=30)
    assert doc.tables == ()
    assert doc.error is not None
    assert "covered twice" in doc.error


def test_a_good_reading_keeps_its_tables_and_seconds(tmp_path: Path) -> None:
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(pdf_factory.blank())
    table = [{"page": 1, "bbox": [0, 0, 1, 1], "cells": [{"row": 0, "col": 0, "text": "a"}]}]
    body = f"json.dump({{'tables': {table!r}, 'seconds': 0.25}}, open(sys.argv[2], 'w'))"
    doc = run.read_document(fake(tmp_path, body), pdf, tool="t", version="1", timeout=30)
    assert doc.error is None
    assert doc.seconds == 0.25
    assert doc.tables[0].cells[0].text == "a"
    assert len(doc.pdf_sha256) == 64
