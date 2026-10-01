import json
import os
import sys
from pathlib import Path

import pytest

import pdf_factory
from inkgrid_bench import fetch, pages, run
from inkgrid_bench.adapters import _cli, ground_truth, inkgrid_read
from inkgrid_bench.tables import NDocument, NPage

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


def test_TR1_a_tuned_run_writes_its_results_beside_the_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    written: list[str] = []

    def document(_data: object, *, head: str, date: str, label: str) -> str:
        written.append(label)
        return f"# {label} {head} {date}\n"

    data = {"counts": {}, "reproduction": {}, "crashes": {}, "defects": {}, "olmocr_errors": {}}
    monkeypatch.setattr(run, "BENCH", tmp_path)
    monkeypatch.setattr(run, "gather", lambda _run, _cfg: data)
    monkeypatch.setattr(run, "environments", lambda _cfg: {})
    monkeypatch.setattr(run.report, "document", document)
    run.write_results(tmp_path / "run", "abc1234", {}, label="tuned")
    (target,) = (tmp_path / "results").glob("*-abc1234-tuned")
    assert written == ["tuned"]
    assert (target / "report.md").read_text(encoding="utf-8").startswith("# tuned abc1234")
    latest = (tmp_path / "results" / "latest.md").read_text(encoding="utf-8")
    assert f"bench/results/{target.name}/report.md" in latest


def test_TR1_the_label_reaches_the_report_stage_and_a_bad_one_is_refused(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    labels: list[str] = []
    monkeypatch.setattr(run, "commit", lambda: "abc1234")
    monkeypatch.setattr(run, "config", dict)
    monkeypatch.setattr(
        run, "write_results", lambda _run, _head, _cfg, *, label: labels.append(label)
    )
    assert run.main(["report", "--label", "tuned"]) == 0
    assert run.main(["report"]) == 0
    assert labels == ["tuned", "baseline"]
    assert run.main(["report", "--label", "final"]) == 2
    assert "label" in capsys.readouterr().err


BATCH = """
import os, sys, time
from pathlib import Path
from inkgrid_bench.adapters._cli import batch
from inkgrid_bench.tables import NCell, NTable

LOG = Path(sys.argv[0]).with_suffix(".log")


def read(pdf, frames):
    with LOG.open("a") as log:
        log.write(pdf.stem + "\\n")
    if pdf.stem == "b":
        BEHAVIOUR
    return [NTable(page=1, bbox=(0, 0, 1, 1), cells=(NCell(0, 0, text=pdf.stem),))]


raise SystemExit(batch(read))
"""


def batch_run(
    tmp_path: Path, behaviour: str
) -> tuple[list[tuple[str, str | None, tuple[str, ...]]], list[str]]:
    script = tmp_path / "adapter.py"
    script.write_text(BATCH.replace("BEHAVIOUR", behaviour))
    pdfs = []
    for name in ("a", "b", "c"):
        pdf = tmp_path / f"{name}.pdf"
        pdf.write_bytes(pdf_factory.blank())
        pdfs.append(pdf)
    results = run.read_batch(
        [PY, str(script)], pdfs, tool="t", version="1", deadline=lambda _pages: 3.0, startup=10.0
    )
    readings = [
        (pdf.stem, doc.error, tuple(c.text for t in doc.tables for c in t.cells))
        for pdf, doc in results
    ]
    return readings, script.with_suffix(".log").read_text().split()


def test_BM1_a_document_that_raises_is_its_own_error(tmp_path: Path) -> None:
    readings, reads = batch_run(tmp_path, "raise ValueError('bad page')")
    assert readings == [("a", None, ("a",)), ("b", "ValueError: bad page", ()), ("c", None, ("c",))]
    assert reads == ["a", "b", "c"]


@pytest.mark.parametrize(
    ("behaviour", "error"),
    [("time.sleep(60)", "timeout after 3 s"), ("os._exit(3)", "exit status 3")],
)
def test_BM2_a_hung_or_dead_document_fails_alone_and_the_batch_resumes(
    tmp_path: Path, behaviour: str, error: str
) -> None:
    readings, reads = batch_run(tmp_path, behaviour)
    assert readings == [("a", None, ("a",)), ("b", error, ()), ("c", None, ("c",))]
    assert reads == ["a", "b", "c"]  # a new process takes c; a is never read again


def test_BM3_a_heavy_documents_deadline_grows_with_its_pages() -> None:
    assert [run.deadline(n) for n in (1, 3, 15)] == [300.0, 360.0, 1800.0]


def test_TS1_tesseract_is_built_from_its_pin() -> None:
    cfg = run.config()
    cmd = run.tesseract_create(cfg)
    assert cmd[0] == str(run.MICROMAMBA)
    assert cmd[1:] == [
        "create", "--yes", "--quiet", "--prefix", str(run.TESSERACT),
        "--override-channels", "--channel", "conda-forge", "tesseract=5.5.3=h7618cdf_0",
    ]  # fmt: skip
    pin = fetch.sources()["micromamba"]
    assert pin.sha256 == "5512233cdd8564a671626081026dc861537a963baa06706baab08fac6f3bb9d2"
    assert pin.url.endswith("/2.3.2-0/micromamba-linux-64.tar.bz2")


def test_TL1_the_heavy_competitors_and_the_ablation_are_tools() -> None:
    cfg = run.config()
    found = {t.name: t for t in run.tools(cfg)}
    heavy = ("docling", "docling-ocr", "marker", "unstructured")
    assert set(heavy) | {"inkgrid-ocr"} <= set(found)
    assert [found[t].package for t in heavy] == [
        "docling==2.131.0", "docling==2.131.0", "marker-pdf==2.0.0", "unstructured[pdf]==0.27.10",
    ]  # fmt: skip
    assert all(found[t].batch for t in heavy)
    assert not found["inkgrid-ocr"].batch
    assert found["inkgrid-ocr"].package is None
    cmd = run.command(found["docling"])
    assert cmd[cmd.index("--index") + 1] == "https://download.pytorch.org/whl/cpu"
    env = run.tool_env(found["unstructured"])
    assert env["PATH"].split(os.pathsep)[0] == str(run.TESSERACT / "bin")
    assert env["TESSDATA_PREFIX"] == str(run.TESSERACT / "share" / "tessdata")
    assert "TESSDATA_PREFIX" not in run.tool_env(found["docling"])


def test_BM4_the_read_stage_batches_a_heavy_tool_and_never_rereads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "adapter.py"
    script.write_text(BATCH.replace("BEHAVIOUR", "pass"))
    docs = []
    for name in ("a", "b"):
        pdf = tmp_path / f"{name}.pdf"
        pdf.write_bytes(pdf_factory.blank())
        docs.append(run.Doc(name, pdf))
    tool = run.Tool("fake", "fake", "fake==1", datasets=("competition",), batch=True)
    monkeypatch.setattr(run, "datasets", lambda: {"competition": docs})
    monkeypatch.setattr(run, "tools", lambda _cfg: [tool])
    monkeypatch.setattr(run, "command", lambda _tool: [PY, str(script)])
    for _ in range(2):
        run.read_all(tmp_path / "run", "abc1234", {})
    saved = [run.reading_path(tmp_path / "run", "fake", "competition", d) for d in docs]
    texts = [NDocument.from_json(p.read_text()).tables[0].cells[0].text for p in saved]
    assert texts == ["a", "b"]
    assert script.with_suffix(".log").read_text().split() == ["a", "b"]  # never read again
