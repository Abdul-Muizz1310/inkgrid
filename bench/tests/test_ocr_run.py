import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from inkgrid_bench import ocr_data, ocr_report, ocr_run, run
from inkgrid_bench.ocr_data import BenchDoc
from inkgrid_bench.tables import NDocument, NPage


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pages(tmp_path: Path, *ids: str) -> list[BenchDoc]:
    docs = []
    for doc_id in ids:
        pdf = tmp_path / f"{doc_id}.pdf"
        pdf.write_bytes(doc_id.encode())
        docs.append(BenchDoc("dpbench", doc_id, pdf, "page"))
    return docs


def census_of(docs: list[BenchDoc], revision: str = "r1") -> dict[str, object]:
    return {
        "benchmark": "dpbench",
        "revision": revision,
        "documents": {
            d.id: {"sha256": sha(d.pdf.read_bytes()), "class": "born_digital", "group": d.group}
            for d in docs
        },
    }


def test_RN1_a_census_and_documents_as_pinned_pass(tmp_path: Path) -> None:
    docs = pages(tmp_path, "01", "02")
    ocr_run.verify_census(census_of(docs), docs, revision="r1", path=tmp_path / "census.json")


def test_RN1_a_census_at_another_revision_is_refused_naming_it(tmp_path: Path) -> None:
    docs = pages(tmp_path, "01")
    path = tmp_path / "census-dpbench.json"
    with pytest.raises(RuntimeError, match=r"census-dpbench\.json.*old.*r1"):
        ocr_run.verify_census(census_of(docs, "old"), docs, revision="r1", path=path)


def test_RN1_a_pdf_whose_bytes_differ_from_the_census_is_refused_naming_it(tmp_path: Path) -> None:
    docs = pages(tmp_path, "01", "02")
    census = census_of(docs)
    docs[1].pdf.write_bytes(b"changed")
    with pytest.raises(RuntimeError, match=r"02\.pdf"):
        ocr_run.verify_census(census, docs, revision="r1", path=tmp_path / "census.json")


def test_RN1_a_census_of_other_documents_is_refused_naming_them(tmp_path: Path) -> None:
    docs = pages(tmp_path, "01", "02")
    with pytest.raises(RuntimeError, match=r"census\.json.*02"):
        ocr_run.verify_census(
            census_of(docs[:1]), docs, revision="r1", path=tmp_path / "census.json"
        )
    with pytest.raises(RuntimeError, match=r"census\.json.*02"):
        ocr_run.verify_census(
            census_of(docs), docs[:1], revision="r1", path=tmp_path / "census.json"
        )


def test_RN1_a_data_file_that_is_not_the_pinned_one_is_refused_naming_it(tmp_path: Path) -> None:
    root = tmp_path / "data"
    (root / "pdfs").mkdir(parents=True)
    (root / "tests.jsonl").write_bytes(b"{}\n")
    (root / "pdfs" / "a.pdf").write_bytes(b"pdf")
    listing = tmp_path / "data.sha256"
    listing.write_text(f"{sha(b'{}\n')}  tests.jsonl\n{sha(b'pdf')}  pdfs/a.pdf\n")
    ocr_run.verify_listing(listing, root)
    (root / "pdfs" / "a.pdf").write_bytes(b"other")
    with pytest.raises(RuntimeError, match=r"pdfs/a\.pdf"):
        ocr_run.verify_listing(listing, root)
    (root / "pdfs" / "a.pdf").unlink()
    with pytest.raises(RuntimeError, match=r"pdfs/a\.pdf"):
        ocr_run.verify_listing(listing, root)


def test_RN1_the_pins_the_census_and_the_listers_name_one_revision() -> None:
    cfg = run.config()
    for benchmark, (root, revision) in ocr_data.LOCATIONS.items():
        pin = cfg["ocr"][benchmark]
        assert pin["revision"] == revision
        assert run.CACHE / pin["root"] == root
        census = json.loads((ocr_run.CENSUS / f"census-{benchmark}.json").read_text())
        assert census["benchmark"] == benchmark
        assert census["revision"] == revision
        assert revision in pin.get("url", revision)
        if "list" in pin:
            assert (run.BENCH / pin["list"]).is_file()


def test_RP1_run_py_runs_the_ocr_stages_with_the_label_given(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    labels: list[str] = []
    monkeypatch.setattr(run, "commit", lambda: "abc1234")
    monkeypatch.setattr(run, "config", dict)
    monkeypatch.setattr(
        ocr_run, "write_results", lambda _run, _head, _cfg, *, label: labels.append(label)
    )
    assert run.main(["report", "--datasets", "ocr", "--label", "tuned"]) == 0
    assert run.main(["--datasets", "ocr", "report"]) == 0
    assert labels == ["tuned", "baseline"]
    assert run.main(["--datasets", "ocr", "verify"]) == 2  # spec 12's stage, not the OCR run's
    assert "stage" in capsys.readouterr().err
    assert run.main(["--datasets", "scans"]) == 2
    assert "ocr" in capsys.readouterr().err


def test_RN2_a_baseline_run_refuses_an_inkgrid_that_is_not_0_1_0s(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ran: list[str] = []
    monkeypatch.setattr(ocr_run, "read", lambda *_args: ran.append("read"))
    monkeypatch.setattr(ocr_run, "write_results", lambda *_args, label: ran.append(label))
    monkeypatch.setattr(ocr_run, "src_changed", lambda tag: tag == ocr_run.BASELINE_READING)
    baseline = ocr_run.stages("baseline")
    for stage in ("read", "report"):
        with pytest.raises(RuntimeError, match=r"src/inkgrid differs from v0\.1\.0"):
            baseline[stage](tmp_path, "abc1234", {})
    assert ran == []
    tuned = ocr_run.stages("tuned")
    tuned["read"](tmp_path, "abc1234", {})
    tuned["report"](tmp_path, "abc1234", {})
    assert ran == ["read", "tuned"]
    monkeypatch.setattr(ocr_run, "src_changed", lambda _tag: False)
    ocr_run.stages("baseline")["read"](tmp_path, "abc1234", {})
    assert ran == ["read", "tuned", "read"]


def test_SC5_a_scorers_output_is_kept_and_its_failure_names_its_log(tmp_path: Path) -> None:
    script = "import sys; print('scored 3 pages'); print('a warning', file=sys.stderr)"
    log = tmp_path / "work" / "scorer.log"
    ocr_run.call([sys.executable, "-c", script], "a scorer", log)
    kept = log.read_text(encoding="utf-8")
    assert "scored 3 pages" in kept
    assert "a warning" in kept
    failing = "import sys; print('matching error'); sys.exit(3)"
    with pytest.raises(RuntimeError, match=r"a scorer failed.*scorer\.log"):
        ocr_run.call([sys.executable, "-c", failing], "a scorer", log)
    assert "matching error" in log.read_text(encoding="utf-8")


PINS = {"tool": {"docling": "1"}, "tesseract": {"spec": "t"}}


def test_RR1_readings_carry_over_only_where_this_commit_would_read_alike(tmp_path: Path) -> None:
    def changed(moved: str) -> object:
        return lambda _commit, paths: [f"{moved}/x.py"] if moved in paths else []

    def pins(_commit: str) -> dict[str, object]:
        return PINS

    same = ocr_run.reusable("aaa1111", PINS, changed=changed("nowhere"), pins=pins)
    assert same == ocr_report.TOOLS
    fixed = ocr_run.reusable("aaa1111", PINS, changed=changed("src/inkgrid"), pins=pins)
    assert fixed == tuple(t for t in ocr_report.TOOLS if t not in {"inkgrid", "inkgrid-ocr"})
    with pytest.raises(RuntimeError, match=r"adapters/x\.py"):
        ocr_run.reusable(
            "aaa1111", PINS, changed=changed("bench/inkgrid_bench/adapters"), pins=pins
        )
    other = {**PINS, "tool": {"docling": "2"}}
    with pytest.raises(RuntimeError, match="pins"):
        ocr_run.reusable("aaa1111", PINS, changed=changed("nowhere"), pins=lambda _c: other)
    source, target = tmp_path / "runs" / "aaa1111", tmp_path / "runs" / "bbb2222"
    for tool in ("inkgrid", "docling"):
        made = source / "readings" / tool / "ocr-dpbench" / "01.json"
        made.parent.mkdir(parents=True)
        made.write_text(tool)
    kept = target / "readings" / "docling" / "ocr-dpbench" / "01.json"
    kept.parent.mkdir(parents=True)
    kept.write_text("read here")
    assert ocr_run.link_readings(source, target, ["inkgrid", "docling", "marker"]) == 1
    linked = target / "readings" / "inkgrid" / "ocr-dpbench" / "01.json"
    assert linked.read_text() == "inkgrid"
    assert (
        linked.stat().st_ino
        == (source / "readings" / "inkgrid" / "ocr-dpbench" / "01.json").stat().st_ino
    )
    assert kept.read_text() == "read here"


def test_RD1_the_read_stage_reads_offline_and_never_leaves_half_a_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doc = BenchDoc("dpbench", "01", tmp_path / "01.pdf", "page")
    monkeypatch.setattr(ocr_run, "checked", lambda b, _cfg: [doc] if b == "dpbench" else [])
    monkeypatch.setattr(run, "command", lambda _tool: ["unused"])
    monkeypatch.setattr(run, "version", lambda _tool, _head: "1")
    offline: list[str | None] = []

    def readings(tool: run.Tool, _cmd: object, ver: str, todo: list[run.Doc]) -> object:
        offline.append(os.environ.get("UV_OFFLINE"))
        page = (NPage(box=(0.0, 0.0, 612.0, 792.0), rotation=0),)
        for d in todo:
            yield (
                d,
                NDocument(tool=tool.name, version=ver, pdf_sha256="x", pages=page, markdown="m"),
            )

    monkeypatch.setattr(run, "tool_readings", readings)
    monkeypatch.delenv("UV_OFFLINE", raising=False)
    out = run.reading_path(tmp_path, "inkgrid", "ocr-dpbench", run.Doc("01", doc.pdf))
    half = out.with_suffix(".part")  # what a killed write leaves
    half.parent.mkdir(parents=True)
    half.write_text("{")
    ocr_run.read(tmp_path, "abc1234", run.config())
    assert set(offline) == {"1"}
    assert "UV_OFFLINE" not in os.environ
    assert NDocument.from_json(out.read_text()).markdown == "m"
    assert not half.exists()


def test_RD1_prepare_builds_every_tool_and_scorer_environment_before_any_reading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ran: list[list[str]] = []

    def process(cmd: list[str], *, timeout: float, cwd: object = None) -> tuple[int, str, str]:
        ran.append(cmd)
        return (1, "", "error: No solution found") if "markitdown" in " ".join(cmd) else (0, "", "")

    monkeypatch.setattr(run, "run_process", process)
    with pytest.raises(RuntimeError, match=r"markitdown.*No solution found"):
        ocr_run.warm(run.config())
    ran.clear()
    monkeypatch.setattr(
        run, "run_process", lambda cmd, *, timeout, cwd=None: ran.append(cmd) or (0, "", "")
    )
    ocr_run.warm(run.config())
    imports = {c[-1] for c in ran}
    packaged = [t for t in ocr_run.tools(run.config()) if t.package is not None]
    assert {f"import inkgrid_bench.adapters.{t.module}" for t in packaged} <= imports
    assert len(ran) == len(packaged) + len(ocr_run.SCORERS_USED)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def test_RN1_a_clone_at_another_commit_or_with_changes_is_refused(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "scorer.py").write_text("score = 1\n")
    git(repo, "add", "scorer.py")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "scorer")
    head = git(repo, "rev-parse", "HEAD")
    ocr_run.verify_clone(repo, head)
    with pytest.raises(RuntimeError, match="not the pinned"):
        ocr_run.verify_clone(repo, "0" * 40)
    (repo / "scorer.py").write_text("score = 2\n")
    with pytest.raises(RuntimeError, match=r"scorer\.py"):
        ocr_run.verify_clone(repo, head)


def test_RR1_run_py_carries_readings_over_for_the_ocr_run_only(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    given: list[tuple[str, str | None]] = []

    def stages(label: str, readings_from: str | None = None) -> dict[str, object]:
        given.append((label, readings_from))
        return {"read": lambda *_args: None}

    monkeypatch.setattr(run, "commit", lambda: "abc1234")
    monkeypatch.setattr(run, "config", dict)
    monkeypatch.setattr(ocr_run, "stages", stages)
    assert run.main(["read", "--datasets", "ocr", "--readings-from", "aaa1111"]) == 0
    assert run.main(["read", "--datasets", "ocr", "--label", "tuned"]) == 0
    assert given == [("baseline", "aaa1111"), ("tuned", None)]
    assert run.main(["read", "--readings-from", "aaa1111"]) == 2
    assert "--readings-from" in capsys.readouterr().err
