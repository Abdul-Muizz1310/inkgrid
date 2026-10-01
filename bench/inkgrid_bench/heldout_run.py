"""The held-out fee set's run: `run.py --datasets heldout` (docs/specs/16-held-out-fee-set.md s. 6).

Its own stages, so spec 12's run is untouched. Every stage that reads a document refuses to start
unless inkgrid's reading is the tuned run's, every ground truth is verified, and the glyph sample is
confirmed: the held-out numbers are that reading, on documents no fix has seen.
"""

import dataclasses
import hashlib
import json
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from inkgrid_bench import fetch, pages, report, run
from inkgrid_bench.heldout import GlyphCell, Truth, access_paths, cer_counts, load_truth
from inkgrid_bench.render import icdar_reg_xml, icdar_str_xml
from inkgrid_bench.scores import binding, icdar
from inkgrid_bench.tables import NDocument, NTable

type Stage = Callable[[Path, str, dict[str, Any]], None]
HELDOUT = run.BENCH / "heldout"
DATASET = "heldout"
READING = "7f70dd6"  # the tuned run's commit: the reading held out (spec 16 section 6)
NOT_TRUTHS = frozenset({"glyphs.json", "review-notes.json"})
PDFS = f"{DATASET}/candidates"  # in the cache, where the selection fetched them
STAGES = ("prepare", "read", "verify", "score", "report")


def _src_changed(commit: str) -> int:
    """`git diff --quiet`'s exit status for `src/inkgrid` against `commit`: 0 when unchanged."""
    return subprocess.run(  # noqa: S603 - fixed arguments
        ["git", "diff", "--quiet", commit, "--", "src/inkgrid"],  # noqa: S607
        cwd=run.REPO,
        check=False,
    ).returncode


def check(
    truth_dir: Path, *, reading: str = READING, git: Callable[[str], int] = _src_changed
) -> tuple[list[Truth], list[GlyphCell]]:
    """The verified truths and the confirmed glyph sample, or why the run must not start."""
    if git(reading) != 0:
        msg = (
            f"src/inkgrid differs from {reading}, the tuned run's reading the held-out run measures"
        )
        raise RuntimeError(msg)
    files = sorted(p for p in truth_dir.glob("*.json") if p.name not in NOT_TRUTHS)
    truths = [load_truth(p.read_text(encoding="utf-8")) for p in files]
    raw = [t.id for t in truths if t.verified is None]
    if raw:
        msg = f"the ground truth of {', '.join(raw)} is not verified"
        raise RuntimeError(msg)
    sample = truth_dir / "glyphs.json"
    if not sample.exists():
        msg = f"no confirmed glyph sample: {sample} is missing"
        raise RuntimeError(msg)
    glyphs = [
        GlyphCell(str(g["doc"]), int(g["table"]), int(g["cell"]), str(g["text"]))
        for g in json.loads(sample.read_text(encoding="utf-8"))
    ]
    return truths, glyphs


def docs(truths: Sequence[Truth]) -> list[run.Doc]:
    """The held-out documents, in the truths' order, each in the cache."""
    return [run.Doc(t.id, run.CACHE / PDFS / f"{t.id}.pdf") for t in truths]


def prepare(_run: Path, _head: str, _cfg: dict[str, Any]) -> None:
    """Fetch every document a ground truth names, verifying its SHA-256."""
    with (HELDOUT / "manifest.toml").open("rb") as f:
        candidates = tomllib.load(f)["candidate"]
    for path in sorted(p for p in HELDOUT.glob("*.json") if p.name not in NOT_TRUTHS):
        c = candidates[path.stem]
        fetch.fetch(fetch.Source(path.stem, c["url"], c["sha256"], f"{PDFS}/{path.stem}.pdf"))
    run.log("prepare: every held-out document verified")


def _truth_reading(truth: Truth, doc: run.Doc) -> NDocument:
    """The ground truth read as a tool: a check on the pipeline and each metric's ceiling."""
    return NDocument(
        tool=report.CHECK,
        version=DATASET,
        pdf_sha256=hashlib.sha256(doc.pdf.read_bytes()).hexdigest(),
        pages=pages.frames(doc.pdf),
        tables=tuple(t.table() for t in truth.tables),
    )


def read(run_dir: Path, head: str, cfg: dict[str, Any]) -> None:
    """Every tool on every held-out document, one document at a time; finished ones are kept."""
    truths, _ = check(HELDOUT)
    held = docs(truths)
    for truth, doc in zip(truths, held, strict=True):
        out = run.reading_path(run_dir, report.CHECK, DATASET, doc)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_truth_reading(truth, doc).to_json(), encoding="utf-8")
    for tool in run.tools(cfg):
        if tool.name == report.CHECK:
            continue
        cmd, ver = run.command(tool), run.version(tool, head)
        todo = [d for d in held if not run.reading_path(run_dir, tool.name, DATASET, d).exists()]
        for doc, reading in run.tool_readings(tool, cmd, ver, todo):
            out = run.reading_path(run_dir, tool.name, DATASET, doc)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(reading.to_json(), encoding="utf-8")
            note = f" ERROR {reading.error}" if reading.error else f" {len(reading.tables)} tables"
            run.log(f"read {tool.name} {DATASET} {doc.id}{note}")


def verify(run_dir: Path, _head: str, _cfg: dict[str, Any]) -> None:
    """Run inkgrid's verifier on every held-out document."""
    truths, _ = check(HELDOUT)
    cmd = [*run.NICE, sys.executable, "-m", "inkgrid_bench.adapters.inkgrid_verify"]
    for doc in docs(truths):
        out = run_dir / "verify" / DATASET / f"{run.safe(doc.id)}.json"
        if out.exists():
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            code, _, err = run.run_process([*cmd, str(doc.pdf), str(out)], timeout=run.TIMEOUT)
        except TimeoutError as exc:
            code, err = 1, str(exc)
        if code != 0:
            out.write_text(json.dumps({"error": run.last_line(err) or f"exit {code}"}))
        run.log(f"verify {DATASET} {doc.id}")


def scored_tables(truth: Truth, tables: Sequence[NTable]) -> list[NTable]:
    """A tool's tables on the document's scored pages; the others are not scored."""
    return [t for t in tables if t.page in truth.pages]


def score_document(
    truth: Truth, glyphs: Sequence[GlyphCell], tables: Sequence[NTable]
) -> dict[str, int]:
    """Binding over the truth's access paths, and CER over its sampled cells (spec 16 s. 2, 5)."""
    mine = scored_tables(truth, tables)
    gt = [
        binding.GtTable(((t.page, t.bbox),), frozenset(binding.norm(c.text) for c in t.cells))
        for t in truth.tables
    ]
    bind = binding.binding_counts(gt, [access_paths(t) for t in truth.tables], mine)
    cells = [g for g in glyphs if g.doc == truth.id]
    cer = cer_counts(cells, {truth.id: truth}, {truth.id: mine})
    zero = {"chars": 0, "errors": 0}
    return {f"bind_{k}": v for k, v in bind.items()} | {
        f"cer_{k}": v for k, v in cer.get(truth.id, zero).items()
    }


def _icdar(work: Path, doc: run.Doc, truth: Truth, readings: dict[str, NDocument]) -> None:
    """Structure and regions on the scored pages, by the ICDAR-2013 competition scorer."""
    todo = {n: r for n, r in readings.items() if not (work / f"{n}-counts.json").exists()}
    if not todo:
        return
    work.mkdir(parents=True, exist_ok=True)
    pdf = doc.pdf.name
    shutil.copy(doc.pdf, work / pdf)
    gt = _truth_reading(truth, doc)
    (work / "gt-str.xml").write_text(icdar_str_xml(gt, pdf), encoding="utf-8")
    (work / "gt-reg.xml").write_text(icdar_reg_xml(gt, pdf), encoding="utf-8")
    sizes = icdar.gt_sizes(run.jar("-str", work, "gt-str.xml", "gt-str.xml", pdf))
    for name, reading in todo.items():
        mine = dataclasses.replace(reading, tables=tuple(scored_tables(truth, reading.tables)))
        (work / f"{name}-str.xml").write_text(icdar_str_xml(mine, pdf), encoding="utf-8")
        (work / f"{name}-reg.xml").write_text(icdar_reg_xml(mine, pdf), encoding="utf-8")
        structure = icdar.structure_counts(
            run.jar("-str", work, "gt-str.xml", f"{name}-str.xml", pdf), sizes
        )
        regions = icdar.region_counts(run.jar("-reg", work, "gt-reg.xml", f"{name}-reg.xml", pdf))
        run.save(work / f"{name}-counts.json", {"str": structure, "reg": regions})
        run.log(f"icdar {DATASET} {doc.id} {name} {structure} {regions}")


def _names(cfg: dict[str, Any]) -> list[str]:
    return [t.name for t in run.tools(cfg)]


def score(run_dir: Path, _head: str, cfg: dict[str, Any]) -> None:
    """Every scorer on every tool's held-out readings, the ground truth's included."""
    truths, glyphs = check(HELDOUT)
    for truth, doc in zip(truths, docs(truths), strict=True):
        readings = {
            n: NDocument.from_json(run.reading_path(run_dir, n, DATASET, doc).read_text())
            for n in _names(cfg)
        }
        _icdar(run_dir / "icdar" / DATASET / doc.id, doc, truth, readings)
        for n, reading in readings.items():
            counts = score_document(truth, glyphs, reading.tables)
            run.save(run_dir / "heldout-scores" / n / f"{doc.id}.json", counts)
        run.log(f"score {DATASET} {doc.id}")


def gather(run_dir: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    """Every held-out document's counts per tool, the crashes, and the verifier's defects."""
    truths, _ = check(HELDOUT)
    held = docs(truths)
    counts: dict[str, dict[str, dict[str, float]]] = {}
    crashes: dict[str, dict[str, list[list[str]]]] = {}
    for name in _names(cfg):
        per_doc: dict[str, dict[str, float]] = {}
        for doc in held:
            path = run.reading_path(run_dir, name, DATASET, doc)
            reading = NDocument.from_json(path.read_text(encoding="utf-8"))
            if reading.error:
                crashes.setdefault(name, {}).setdefault(DATASET, []).append([doc.id, reading.error])
            ic = run.load(run_dir / "icdar" / DATASET / doc.id / f"{name}-counts.json")
            scores = run.load(run_dir / "heldout-scores" / name / f"{doc.id}.json")
            per_doc[doc.id] = (
                {
                    "seconds": reading.seconds,
                    "pages": 0 if reading.error else len(reading.pages),
                    "crashed": 1 if reading.error else 0,
                    "tables": len(reading.tables),
                }
                | {f"str_{k}": v for k, v in ic["str"].items()}
                | {f"reg_{k}": v for k, v in ic["reg"].items()}
                | scores
            )
        counts[name] = per_doc
    by_code: dict[str, int] = {}
    flagged = errors = 0
    for doc in held:
        v = run.load(run_dir / "verify" / DATASET / f"{run.safe(doc.id)}.json")
        if "error" in v:
            errors += 1
            continue
        flagged += bool(v["defects"])
        for code, n in v["defects"].items():
            by_code[code] = by_code.get(code, 0) + n
    defects = {DATASET: {"by_code": by_code, "documents_with_defects": flagged, "errors": errors}}
    return {"counts": {DATASET: counts}, "crashes": crashes, "defects": defects}


def results_dir(base: Path, date: str, head: str) -> Path:
    """Where a held-out run's results go, beside spec 12's runs."""
    return base / f"{date}-{head}-heldout"


def write_results(run_dir: Path, head: str, cfg: dict[str, Any]) -> None:
    """The held-out results: counts, environments, checks, and the report."""
    data = gather(run_dir, cfg)
    date = datetime.now(UTC).date().isoformat()
    target = results_dir(run.BENCH / "results", date, head)
    target.mkdir(parents=True, exist_ok=True)
    run.save(target / "counts.json", data["counts"])
    run.save(target / "environment.json", run.environments(cfg))
    run.save(target / "checks.json", {k: v for k, v in data.items() if k != "counts"})
    text = report.document(data, head=head, date=date, label="heldout")
    (target / "report.md").write_text(text, encoding="utf-8")
    run.log(f"report written to {target}")


def stages() -> dict[str, Stage]:
    """The held-out run's stages, in order."""
    return dict(zip(STAGES, (prepare, read, verify, score, write_results), strict=True))
