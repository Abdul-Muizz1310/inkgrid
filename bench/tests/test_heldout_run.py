import json
import os
from pathlib import Path

import pytest
from heldout_data import fee_table, truth_json

from inkgrid_bench import fetch, heldout_run, report, run
from inkgrid_bench.heldout import GlyphCell, load_truth
from inkgrid_bench.scores import icdar
from inkgrid_bench.tables import NCell, NTable


def write_truths(tmp_path: Path, *, verified: bool = True, glyphs: bool = True) -> Path:
    tmp_path.mkdir(parents=True)
    (tmp_path / "x.json").write_text(truth_json([fee_table()], verified=verified))
    if glyphs:
        sample = [{"doc": "x", "table": 0, "cell": 5, "text": "4,715"}]
        (tmp_path / "glyphs.json").write_text(json.dumps(sample))
    return tmp_path


def test_RN1_the_held_out_run_refuses_a_changed_reading_or_unchecked_truth(tmp_path: Path) -> None:
    good = write_truths(tmp_path / "good")
    (good / "review-notes.json").write_text("{}")  # the review's notes are not a ground truth
    truths, glyphs = heldout_run.check(good, reading="7f70dd6", git=lambda _commit: 0)
    assert [t.id for t in truths] == ["x"]
    assert glyphs == [GlyphCell("x", 0, 5, "4,715")]
    with pytest.raises(RuntimeError, match="7f70dd6"):
        heldout_run.check(good, reading="7f70dd6", git=lambda _commit: 1)
    with pytest.raises(RuntimeError, match="not verified"):
        heldout_run.check(
            write_truths(tmp_path / "raw", verified=False), reading="7f70dd6", git=lambda _c: 0
        )
    with pytest.raises(RuntimeError, match="glyph"):
        heldout_run.check(
            write_truths(tmp_path / "noglyph", glyphs=False), reading="7f70dd6", git=lambda _c: 0
        )


def test_RN2_datasets_heldout_runs_the_held_out_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(run, "commit", lambda: "abc1234")
    monkeypatch.setattr(run, "config", dict)

    def recorder(name: str) -> heldout_run.Stage:
        return lambda _run, head, _cfg: calls.append((name, head))

    fake = {name: recorder(name) for name in heldout_run.STAGES}
    monkeypatch.setattr(heldout_run, "stages", lambda: fake)
    assert run.main(["read", "score", "--datasets", "heldout"]) == 0
    assert calls == [("read", "abc1234"), ("score", "abc1234")]
    assert run.main(["--datasets", "fintabnet"]) == 2
    assert heldout_run.results_dir(Path("/r"), "2026-10-02", "abc1234") == Path(
        "/r/2026-10-02-abc1234-heldout"
    )


def test_SC1_only_the_scored_pages_tables_are_scored() -> None:
    truth = load_truth(truth_json([fee_table()], pages=[2, 3]))
    good = NTable(page=2, bbox=(0, 0, 300, 80), cells=(
        NCell(0, 0, text="Service"), NCell(0, 1, text="Fees (AUD)"),
        NCell(1, 0, text="Orders"), NCell(1, 1, text="4,715"),
    ))  # fmt: skip
    off = NTable(page=5, bbox=(0, 0, 300, 80), cells=(NCell(0, 0, text="4,715"),))
    counts = heldout_run.score_document(truth, [GlyphCell("x", 0, 5, "4,715")], [good, off])
    assert counts["cer_chars"] == 5
    assert counts["cer_errors"] == 0
    assert counts["bind_paths"] == 3
    assert counts["bind_value"] == 1  # only 4,715 is among the tool's cells
    assert heldout_run.scored_tables(truth, [good, off]) == [good]


def test_RP3_a_held_out_report_says_so_and_shows_cer() -> None:
    one = {
        "seconds": 1.0, "pages": 2, "crashed": 0, "tables": 1,
        "str_correct": 1, "str_gt": 2, "str_detected": 2, "reg_correct": 1, "reg_gt": 1,
        "reg_detected": 1, "bind_paths": 3, "bind_value": 2, "bind_leaf": 1, "bind_bound": 1,
        "cer_chars": 10, "cer_errors": 1,
    }  # fmt: skip
    counts = {"heldout": {t: {"a": one, "b": one} for t in ("inkgrid", "camelot", "docling")}}
    data = {
        "counts": counts,
        "crashes": {},
        "defects": {"heldout": {"by_code": {}, "documents_with_defects": 0, "errors": 0}},
    }
    text = report.document(data, head="abc1234", date="2026-10-02", label="heldout", resamples=20)
    title, first = text.split("\n\n")[:2]
    assert "held-out" in title.lower()
    assert "no fix has seen" in first
    assert "### Cell character error rate" in text
    assert "## Held-out fee set (2 documents)" in text
    assert "PyMuPDF" in first  # where the truth's cell text comes from, and who shares it
    cer = text.split("### Cell character error rate\n", 1)[1].split("### ", 1)[0]
    assert "recurs" in cer  # what CER does not see
    assert "a negative difference favours inkgrid" in cer
    assert "Soric" not in text
    assert "olmOCR" not in text


def test_EN1_the_region_scorer_opens_an_encrypted_pdf() -> None:
    # tfex-usd is RC4-encrypted; PDFBox 1.8.2 opens it only with the BouncyCastle it names
    cmd = icdar.command(
        Path("java"), Path("t"), "-reg", gt=Path("a-reg.xml"), result=Path("b"), pdf=Path("a.pdf")
    )
    assert str(Path("t") / "bcprov-jdk15-1.44.jar") in cmd[3].split(os.pathsep)
    assert "tools/bcprov-jdk15-1.44.jar" in {s.file for s in fetch.sources().values()}
