import hashlib
import json
from pathlib import Path

import pytest

from inkgrid_bench import ocr_data, ocr_run, run
from inkgrid_bench.ocr_data import BenchDoc


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
