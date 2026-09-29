"""The M5b run: every tool on every dataset, one document at a time; the scorers; the results.

`uv run python -m inkgrid_bench.run [prepare|read|verify|score|report|all]`, from the repository.
Everything fetched or produced lives under `~/.cache/inkgrid-bench/`, keyed by the commit measured;
a stage skips what an earlier run of it already wrote. `report` writes `bench/results/`.
"""

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from inkgrid_bench import fetch, pages, report
from inkgrid_bench.render import icdar_reg_xml, icdar_str_xml
from inkgrid_bench.scores import binding, icdar, olmocr, soric
from inkgrid_bench.tables import NCell, NDocument, NTable

CACHE = Path.home() / ".cache" / "inkgrid-bench"
BENCH = Path(__file__).resolve().parents[1]
REPO = BENCH.parent
TIMEOUT = 300  # seconds per document per tool (spec 12 section 2)
SCORER_TIMEOUT = 3600
NICE = ("nice", "-n", "10")
TOOL_PYTHON = "3.12"
JAVA = CACHE / "tools" / "jdk-17.0.20.1+1-jre" / "bin" / "java"
SORIC_DATA = CACHE / "soric" / "x" / "icdar"
SORIC_RELEASED = CACHE / "soric" / "x" / "icdar-2013"
SORIC_REPO = CACHE / "soric" / "repo"
SORIC_MODELS = ("cam", "pymu", "plum", "doc")  # their Camelot, PyMuPDF, pdfplumber, Docling
OLMOCR_DATA = CACHE / "olmocr" / "bench_data"
NO_TEXT_LAYER = BENCH / "olmocr-no-text-layer.txt"
EXPECTED = {"competition": 67, "practice": 58, "olmocr": 188}
# Each archive and the path its extraction creates.
EXTRACT = {
    "icdar2013-competition": ("icdar2013/competition", "competition-dataset-eu"),
    "icdar2013-practice-eu": ("icdar2013/practice/eu", "eu-dataset"),
    "icdar2013-practice-us": ("icdar2013/practice/us", "us-gov-dataset"),
    "temurin-jre-17": ("tools", "jdk-17.0.20.1+1-jre"),
    "jai-core": ("tools", "jai-1_1_3"),
    "soric-icdar2013": ("soric/x", "icdar"),
    "soric-predictions": ("soric/x", "icdar-2013"),
}


def config() -> dict[str, Any]:
    """The pinned sources, tools, and scorers."""
    with (BENCH / "sources.toml").open("rb") as f:
        return tomllib.load(f)


def log(message: str) -> None:
    """One progress line, flushed, with the time."""
    sys.stdout.write(f"{datetime.now(UTC):%H:%M:%S} {message}\n")
    sys.stdout.flush()


# --- processes ---------------------------------------------------------------------------------


def _env() -> dict[str, str]:
    return {**os.environ, "PYTHONPATH": str(BENCH)}


def run_process(
    cmd: Sequence[str], *, timeout: float, cwd: Path | None = None
) -> tuple[int, str, str]:
    """Run a command in its own process group; on timeout kill the group and raise TimeoutError."""
    proc = subprocess.Popen(  # noqa: S603 - commands built here from pinned values
        cmd,
        cwd=cwd,
        env=_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        msg = f"timeout after {timeout:g} s"
        raise TimeoutError(msg) from None
    return proc.returncode, out, err


def _last_line(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else None


def _table(data: dict[str, Any]) -> NTable:
    x0, y0, x1, y1 = (float(v) for v in data["bbox"])
    cells = tuple(NCell(**c) for c in data["cells"])
    return NTable(page=int(data["page"]), bbox=(x0, y0, x1, y1), cells=cells)


def read_document(
    cmd: Sequence[str], pdf: Path, *, tool: str, version: str, timeout: float = TIMEOUT
) -> NDocument:
    """One tool's reading of one PDF; a crash, timeout, or broken output is its error, no tables."""
    frames = pages.frames(pdf)
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()

    def failed(error: str) -> NDocument:
        return NDocument(tool=tool, version=version, pdf_sha256=sha, pages=frames, error=error)

    with _scratch() as tmp:
        out = tmp / "out.json"
        try:
            code, _, err = run_process([*cmd, str(pdf), str(out)], timeout=timeout)
        except TimeoutError as exc:
            return failed(str(exc))
        if code != 0:
            return failed(_last_line(err) or f"exit status {code}")
        try:
            data = json.loads(out.read_text(encoding="utf-8"))
            tables = tuple(_table(t) for t in data["tables"])
            seconds = float(data["seconds"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return failed(f"unreadable output: {exc}")
    for t in tables:
        if not 1 <= t.page <= len(frames):
            return failed(f"a table on page {t.page} of {len(frames)}")
    return NDocument(
        tool=tool, version=version, pdf_sha256=sha, pages=frames, tables=tables, seconds=seconds
    )


class _scratch:  # noqa: N801 - used as a context manager, like tempfile's
    """A fresh scratch directory under the cache, removed on exit."""

    def __enter__(self) -> Path:
        base = CACHE / "scratch"
        base.mkdir(parents=True, exist_ok=True)
        self.path = base / f"{os.getpid()}-{datetime.now(UTC):%H%M%S%f}"
        self.path.mkdir()
        return self.path

    def __exit__(self, *_: object) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


# --- datasets and tools ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Doc:
    """A benchmark document: its id within the dataset and its PDF."""

    id: str
    pdf: Path


def datasets() -> dict[str, list[Doc]]:
    """The three datasets' documents, in sorted order; their counts are spec 12's."""
    icdar13 = CACHE / "icdar2013"
    out = {
        "competition": [
            Doc(p.stem, p) for p in sorted(icdar13.glob("competition/competition-dataset-*/*.pdf"))
        ],
        "practice": [Doc(p.stem, p) for p in sorted(icdar13.glob("practice/*/*/*.pdf"))],
        "olmocr": [
            Doc(f"tables/{p.name}", p)
            for p in sorted((OLMOCR_DATA / "pdfs" / "tables").glob("*.pdf"))
        ],
    }
    for name, docs in out.items():
        if len(docs) != EXPECTED[name]:
            msg = f"{name}: {len(docs)} documents, spec 12 has {EXPECTED[name]}"
            raise RuntimeError(msg)
    return out


@dataclass(frozen=True, slots=True)
class Tool:
    """A tool: its adapter module, its pinned package (None: this environment), its datasets."""

    name: str
    module: str
    package: str | None
    datasets: tuple[str, ...] = ("competition", "practice", "olmocr")


def tools(cfg: dict[str, Any]) -> list[Tool]:
    """The four tools of spec 12 section 2, and the ground truth read as a tool (a check)."""
    pins = cfg["tool"]
    return [
        Tool("inkgrid", "inkgrid_read", None),
        Tool("pdfplumber", "pdfplumber_tables", f"pdfplumber=={pins['pdfplumber']}"),
        Tool("pymupdf", "pymupdf_tables", f"pymupdf=={pins['pymupdf']}"),
        Tool("camelot", "camelot_lattice", f"camelot-py=={pins['camelot-py']}"),
        Tool("ground-truth", "ground_truth", None, ("competition", "practice")),
    ]


def isolated(packages: Sequence[str], python: str = TOOL_PYTHON) -> list[str]:
    """`uv run` in a fresh environment holding only `packages`."""
    withs = [arg for p in packages for arg in ("--with", p)]
    return ["uv", "run", "--isolated", "--no-project", "--python", python, *withs]


def command(tool: Tool) -> list[str]:
    """The adapter's command line, before its two arguments."""
    module = ["-m", f"inkgrid_bench.adapters.{tool.module}"]
    if tool.package is None:
        return [*NICE, sys.executable, *module]
    return [*NICE, *isolated([tool.package]), "python", *module]


def commit() -> str:
    """The commit measured; a dirty tree is refused, as no commit could reproduce its results."""
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],  # noqa: S607
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    if status.strip() and os.environ.get("INKGRID_BENCH_DIRTY") != "1":
        msg = "the working tree has changes; commit them first"
        raise RuntimeError(msg)
    return subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"],  # noqa: S607
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout.strip()  # fmt: skip


def version(tool: Tool, head: str) -> str:
    """What the reading is a reading by."""
    if tool.name == "inkgrid":
        import inkgrid  # noqa: PLC0415 - only this tool needs inkgrid in this process

        return f"{inkgrid.__version__}+{head}"
    if tool.package is None:
        return "icdar2013"
    return tool.package.split("==")[1]


def safe(doc_id: str) -> str:
    """A document id as a file name."""
    return doc_id.replace("/", "__")


# --- prepare -----------------------------------------------------------------------------------


def prepare(cfg: dict[str, Any]) -> None:
    """Fetch every pinned file (verifying each hash), extract the archives, clone the scorer."""
    for name, source in fetch.sources().items():
        path = fetch.fetch(source, CACHE)
        if name in EXTRACT:
            where, made = EXTRACT[name]
            target = CACHE / where
            if not (target / made).exists():
                log(f"extract {path.name} -> {target}")
                target.mkdir(parents=True, exist_ok=True)
                if path.suffix == ".zip":
                    with zipfile.ZipFile(path) as z:
                        z.extractall(target)  # noqa: S202 - hash-verified archive
                else:
                    with tarfile.open(path) as t:
                        t.extractall(target, filter="data")
    manifest = cfg["manifest"]["olmocr-tables"]
    fetch.fetch_manifest(manifest["url"], BENCH / manifest["list"], manifest["root"], CACHE)
    scorer = cfg["scorer"]["soric"]
    if not SORIC_REPO.exists():
        subprocess.run(  # noqa: S603
            ["git", "clone", "--branch", scorer["tag"], scorer["repository"], str(SORIC_REPO)],  # noqa: S607
            check=True,
        )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],  # noqa: S607
        cwd=SORIC_REPO, capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    if not head.startswith(scorer["commit"]):
        msg = f"Soric et al.'s evaluator is at {head[:8]}, not {scorer['commit']}"
        raise RuntimeError(msg)
    log("prepare: every source verified")


# --- read and verify ---------------------------------------------------------------------------


def reading_path(run: Path, tool: str, dataset: str, doc: Doc) -> Path:
    """Where a tool's reading of a document is kept."""
    return run / "readings" / tool / dataset / f"{safe(doc.id)}.json"


def read_all(run: Path, head: str, cfg: dict[str, Any]) -> None:
    """Every tool on every document of its datasets, one at a time."""
    docs = datasets()
    for tool in tools(cfg):
        cmd, ver = command(tool), version(tool, head)
        for dataset in tool.datasets:
            for doc in docs[dataset]:
                out = reading_path(run, tool.name, dataset, doc)
                if out.exists():
                    continue
                reading = read_document(cmd, doc.pdf, tool=tool.name, version=ver)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(reading.to_json(), encoding="utf-8")
                note = (
                    f" ERROR {reading.error}" if reading.error else f" {len(reading.tables)} tables"
                )
                log(f"read {tool.name} {dataset} {doc.id}{note}")


def verify_all(run: Path) -> None:
    """Run inkgrid's verifier on every document (spec 12 section 4.5)."""
    cmd = [*NICE, sys.executable, "-m", "inkgrid_bench.adapters.inkgrid_verify"]
    for dataset, docs in datasets().items():
        for doc in docs:
            out = run / "verify" / dataset / f"{safe(doc.id)}.json"
            if out.exists():
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            try:
                code, _, err = run_process([*cmd, str(doc.pdf), str(out)], timeout=TIMEOUT)
            except TimeoutError as exc:
                code, err = 1, str(exc)
            if code != 0:
                out.write_text(json.dumps({"error": _last_line(err) or f"exit {code}"}))
            log(f"verify {dataset} {doc.id}")


# --- scores ------------------------------------------------------------------------------------


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        msg = f"{path} holds no JSON object"
        raise TypeError(msg)
    return data


def _save(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, sort_keys=True), encoding="utf-8")


def _jar(mode: str, work: Path, gt: str, result: str, pdf: str) -> str:
    cmd = icdar.command(
        JAVA, CACHE / "tools", mode, gt=work / gt, result=work / result, pdf=work / pdf
    )
    code, out, err = run_process([*NICE, *cmd], timeout=SCORER_TIMEOUT, cwd=work)
    if code != 0:
        msg = f"the jar failed on {work / result}: {_last_line(err)}"
        raise RuntimeError(msg)
    return out


def score_icdar(run: Path, cfg: dict[str, Any]) -> None:
    """Structure and regions for every tool on both ICDAR-2013 sets, the jar's own way."""
    docs = datasets()
    for dataset in ("competition", "practice"):
        for doc in docs[dataset]:
            work = run / "icdar" / dataset / doc.id
            work.mkdir(parents=True, exist_ok=True)
            names = {"pdf": doc.pdf.name, "str": f"{doc.id}-str.xml", "reg": f"{doc.id}-reg.xml"}
            for name in names.values():
                if not (work / name).exists():
                    shutil.copy(doc.pdf.with_name(name), work / name)
            sizes_path = work / "gt-sizes.json"
            if not sizes_path.exists():
                _save(
                    sizes_path,
                    icdar.gt_sizes(_jar("-str", work, names["str"], names["str"], names["pdf"])),
                )
            sizes = {int(k): v for k, v in _load(sizes_path).items()}
            for tool in tools(cfg):
                out = work / f"{tool.name}-counts.json"
                if dataset not in tool.datasets or out.exists():
                    continue
                reading = NDocument.from_json(
                    reading_path(run, tool.name, dataset, doc).read_text()
                )
                res_str, res_reg = f"{doc.id}-{tool.name}-str.xml", f"{doc.id}-{tool.name}-reg.xml"
                (work / res_str).write_text(icdar_str_xml(reading, names["pdf"]), encoding="utf-8")
                (work / res_reg).write_text(icdar_reg_xml(reading, names["pdf"]), encoding="utf-8")
                structure = icdar.structure_counts(
                    _jar("-str", work, names["str"], res_str, names["pdf"]), sizes
                )
                regions = icdar.region_counts(
                    _jar("-reg", work, names["reg"], res_reg, names["pdf"])
                )
                _save(out, {"str": structure, "reg": regions})
                log(f"icdar {dataset} {doc.id} {tool.name} {structure} {regions}")


def _soric_eval(cfg: dict[str, Any], model: str, pred_dir: Path, save_dir: Path) -> Path:
    scorer = cfg["scorer"]["soric"]
    result = save_dir / f"results_{model}_final_bbox.json"
    if result.exists():
        return result
    save_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        *NICE,
        "uv", "run", "--isolated", "--no-project", "--python", scorer["python"],
        "--index", scorer["index"], "--index-strategy", "unsafe-best-match",
        *[arg for p in scorer["with"] for arg in ("--with", p)],
        "python", "src/main.py", "--mode", "eval", "--model", model,
        "--data_root_dir", f"{SORIC_DATA}/", "--save_dir", str(save_dir),
        "--pred_dir", f"{pred_dir}/", "--td_type", "bbox", "--type", "0",
        "--config_file", "src/detection_config.json", "--model_load_path", "", "--device", "cpu",
    ]  # fmt: skip
    code, out, err = run_process(cmd, timeout=SCORER_TIMEOUT, cwd=SORIC_REPO)
    (save_dir / "stdout.txt").write_text(out + "\n--- stderr\n" + err, encoding="utf-8")
    if code != 0 or not result.exists():
        msg = f"Soric et al.'s evaluator failed for {model}: {_last_line(err)}"
        raise RuntimeError(msg)
    soric.check_log(out + "\n" + err)
    return result


def score_soric(run: Path, cfg: dict[str, Any]) -> None:
    """Soric et al.'s protocol on the competition set, and their released predictions re-scored."""
    docs = datasets()["competition"]
    gt = soric.gt_counts(SORIC_DATA)
    for tool in tools(cfg):
        out = run / "soric" / tool.name / "counts.json"
        if out.exists():
            continue
        readings = {
            d.id: NDocument.from_json(reading_path(run, tool.name, "competition", d).read_text())
            for d in docs
        }
        pred_dir = run / "soric" / tool.name
        _save(pred_dir / f"predictions_{soric.MODEL}.json", soric.predictions(readings))
        result = _soric_eval(cfg, soric.MODEL, pred_dir, pred_dir / "results")
        _save(out, soric.result_counts(_load(result), gt))
        log(f"soric {tool.name}")
    for model in SORIC_MODELS:
        out = run / "soric" / f"released-{model}" / "counts.json"
        if out.exists():
            continue
        result = _soric_eval(cfg, model, SORIC_RELEASED, out.parent / "results")
        _save(out, soric.result_counts(_load(result), gt))
        _save(
            out.parent / "released-counts.json",
            soric.result_counts(_load(SORIC_RELEASED / f"results_{model}_final_bbox.json"), gt),
        )
        log(f"soric released {model}")


def score_olmocr(run: Path, cfg: dict[str, Any]) -> None:
    """olmOCR-bench's table tests for every tool, per test, checked against its command line."""
    scorer = cfg["scorer"]["olmocr"]
    env = isolated([scorer["package"], *scorer["with"]])
    docs = datasets()["olmocr"]
    for tool in tools(cfg):
        if "olmocr" not in tool.datasets:
            continue
        out = run / "olmocr" / f"{tool.name}.json"
        if out.exists():
            continue
        candidate = f"inkgrid-bench-{tool.name}"
        folder = OLMOCR_DATA / candidate
        shutil.rmtree(folder, ignore_errors=True)
        for doc in docs:
            reading = NDocument.from_json(reading_path(run, tool.name, "olmocr", doc).read_text())
            page = folder / olmocr.candidate_path(doc.id)
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(olmocr.page_markdown(reading), encoding="utf-8")
        driver = run / "olmocr" / f"{tool.name}-driver.json"
        driver.parent.mkdir(parents=True, exist_ok=True)
        cmd = [*NICE, *env, "python", "-m", "inkgrid_bench.scores.olmocr_driver"]
        code, _, err = run_process(
            [*cmd, str(OLMOCR_DATA), candidate, str(driver)], timeout=SCORER_TIMEOUT
        )
        if code != 0:
            msg = f"olmOCR's scorer failed for {tool.name}: {_last_line(err)}"
            raise RuntimeError(msg)
        cli = [*NICE, *env, "python", "-m", "olmocr.bench.benchmark", "--dir", str(OLMOCR_DATA)]
        code, stdout, err = run_process(
            [*cli, "--candidate", candidate, "--skip_baseline"], timeout=SCORER_TIMEOUT
        )
        if code != 0:
            msg = f"olmOCR's command line failed for {tool.name}: {_last_line(err)}"
            raise RuntimeError(msg)
        result = _load(driver)
        if result["errors"]:
            msg = f"olmOCR's scorer met errors for {tool.name}: {result['errors'][0]}"
            raise RuntimeError(msg)
        tests = [json.loads(line) for line in (OLMOCR_DATA / "table_tests.jsonl").open()]
        counts = olmocr.result_counts(tests, result["passed"])
        passed = int(sum(c["passed"] for c in counts.values()))
        total = int(sum(c["tests"] for c in counts.values()))
        cli_score = olmocr.cli_score(stdout, candidate, passed=passed, total=total)
        _save(out, {"counts": counts, "errors": result["errors"], "cli_score": cli_score})
        log(f"olmocr {tool.name} {passed}/{total} (command line {cli_score}%)")


def score_binding(run: Path, cfg: dict[str, Any]) -> None:
    """Binding on the practice set for every tool (spec 12 section 4.4)."""
    for doc in datasets()["practice"]:
        paths = binding.parse_fnc(
            doc.pdf.with_name(f"{doc.id}-fnc.csv").read_text(encoding="utf-8", errors="replace")
        )
        xml = doc.pdf.with_name(f"{doc.id}-str.xml").read_text(encoding="utf-8")
        gt = binding.gt_tables(xml, pages.frames(doc.pdf))
        for tool in tools(cfg):
            reading = NDocument.from_json(reading_path(run, tool.name, "practice", doc).read_text())
            counts = binding.binding_counts(gt, paths, reading.tables)
            _save(run / "binding" / tool.name / f"{doc.id}.json", counts)
    log("binding done")


# --- report ------------------------------------------------------------------------------------


def _with_prefix(prefix: str, counts: dict[str, float]) -> dict[str, float]:
    return {f"{prefix}_{k}": v for k, v in counts.items()}


def _no_text(docs: dict[str, list[Doc]]) -> set[str]:
    """The olmOCR PDFs without a text layer, as pinned in bench/olmocr-no-text-layer.txt."""
    lines = NO_TEXT_LAYER.read_text(encoding="utf-8").splitlines()
    no_text = {line.strip() for line in lines if line.strip() and not line.startswith("#")}
    if len(no_text) != 15 or not no_text <= {d.id for d in docs["olmocr"]}:  # noqa: PLR2004
        msg = f"{NO_TEXT_LAYER.name}: {len(no_text)} PDFs, spec 12 has 15 of the 188"
        raise RuntimeError(msg)
    return no_text


def _scores(run: Path, tool: str, dataset: str, doc: Doc) -> dict[str, float]:
    """A document's scorer counts for one tool, prefixed by scorer."""
    c: dict[str, float] = {}
    if dataset in ("competition", "practice"):
        ic = _load(run / "icdar" / dataset / doc.id / f"{tool}-counts.json")
        c |= _with_prefix("str", ic["str"]) | _with_prefix("reg", ic["reg"])
    if dataset == "competition":
        c |= _with_prefix("soric", _load(run / "soric" / tool / "counts.json")[doc.id])
    if dataset == "practice":
        c |= _with_prefix("bind", _load(run / "binding" / tool / f"{doc.id}.json"))
    if dataset == "olmocr":
        c |= _with_prefix("olm", _load(run / "olmocr" / f"{tool}.json")["counts"][doc.id])
    return c


def _defects(run: Path, docs: dict[str, list[Doc]]) -> dict[str, dict[str, Any]]:
    """The verifier's defects on inkgrid's readings per dataset, by class."""
    out: dict[str, dict[str, Any]] = {}
    for dataset, ds in docs.items():
        by_code: dict[str, int] = {}
        flagged = errors = 0
        for doc in ds:
            v = _load(run / "verify" / dataset / f"{safe(doc.id)}.json")
            if "error" in v:
                errors += 1
                continue
            flagged += bool(v["defects"])
            for code, n in v["defects"].items():
                by_code[code] = by_code.get(code, 0) + n
        out[dataset] = {"by_code": by_code, "documents_with_defects": flagged, "errors": errors}
    return out


def gather(run: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    """Every document's counts per dataset and tool, crashes, defects, and the reproduction row."""
    docs = datasets()
    no_text = _no_text(docs)
    counts: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
    crashes: dict[str, dict[str, list[list[str]]]] = {}
    for tool in tools(cfg):
        for dataset in tool.datasets:
            per_doc: dict[str, dict[str, float]] = {}
            for doc in docs[dataset]:
                path = reading_path(run, tool.name, dataset, doc)
                reading = NDocument.from_json(path.read_text(encoding="utf-8"))
                if reading.error:
                    crashes.setdefault(tool.name, {}).setdefault(dataset, []).append(
                        [doc.id, reading.error]
                    )
                per_doc[doc.id] = {
                    "seconds": reading.seconds,
                    "pages": 0 if reading.error else len(reading.pages),
                    "crashed": 1 if reading.error else 0,
                    "tables": len(reading.tables),
                } | _scores(run, tool.name, dataset, doc)
            counts.setdefault(dataset, {})[tool.name] = per_doc
    counts["olmocr-text-layer"] = {
        tool: {d: c for d, c in per_doc.items() if d not in no_text}
        for tool, per_doc in counts["olmocr"].items()
    }
    reproduction = {
        model: {
            "here": _load(run / "soric" / f"released-{model}" / "counts.json"),
            "released": _load(run / "soric" / f"released-{model}" / "released-counts.json"),
        }
        for model in SORIC_MODELS
    }
    olm_errors = {
        tool.name: _load(run / "olmocr" / f"{tool.name}.json")["errors"]
        for tool in tools(cfg)
        if "olmocr" in tool.datasets
    }
    return {
        "counts": counts,
        "crashes": crashes,
        "defects": _defects(run, docs),
        "reproduction": reproduction,
        "olmocr_errors": olm_errors,
    }


def environments(cfg: dict[str, Any]) -> dict[str, Any]:
    """Every tool environment's resolved packages, and the scorers' pins."""
    dump = (
        "import importlib.metadata as m, json; "
        "print(json.dumps({d.metadata['Name']: d.version for d in m.distributions()}))"
    )
    out: dict[str, Any] = {}
    for tool in tools(cfg):
        if tool.package is None:
            continue
        _, stdout, _ = run_process([*isolated([tool.package]), "python", "-c", dump], timeout=600)
        out[tool.name] = json.loads(stdout)
    _, stdout, _ = run_process([sys.executable, "-c", dump], timeout=60)
    out["inkgrid"] = json.loads(stdout)
    _, _, java = run_process([str(JAVA), "-version"], timeout=60)
    out["java"] = java.strip().splitlines()
    out["scorers"] = cfg["scorer"]
    return out


def score_all(run: Path, _head: str, cfg: dict[str, Any]) -> None:
    """Every scorer on every tool's readings."""
    score_icdar(run, cfg)
    score_soric(run, cfg)
    score_olmocr(run, cfg)
    score_binding(run, cfg)


def _stages() -> dict[str, Callable[[Path, str, dict[str, Any]], None]]:
    return {
        "prepare": lambda _run, _head, cfg: prepare(cfg),
        "read": read_all,
        "verify": lambda run, _head, _cfg: verify_all(run),
        "score": score_all,
        "report": write_results,
    }


def write_results(run: Path, head: str, cfg: dict[str, Any]) -> None:
    """The results directory and `latest.md` (spec 12 section 7)."""
    data = gather(run, cfg)
    date = datetime.now(UTC).date().isoformat()
    target = BENCH / "results" / f"{date}-{head}"
    target.mkdir(parents=True, exist_ok=True)
    _save(target / "counts.json", data["counts"])
    _save(target / "environment.json", environments(cfg))
    extra = {k: v for k, v in data.items() if k != "counts"}
    _save(target / "checks.json", extra)
    text = report.document(data, head=head, date=date)
    (target / "report.md").write_text(text, encoding="utf-8")
    (BENCH / "results" / "latest.md").write_text(
        f"<!-- the newest report: bench/results/{target.name}/report.md -->\n" + text,
        encoding="utf-8",
    )
    log(f"report written to {target}")


def main(argv: Sequence[str] = sys.argv[1:]) -> int:
    """Run the stages named, or all of them."""
    stages = _stages()
    wanted = list(argv) or ["all"]
    if wanted == ["all"]:
        wanted = list(stages)
    unknown = [s for s in wanted if s not in stages]
    if unknown:
        sys.stderr.write(f"unknown stage {unknown[0]!r}; stages: {', '.join(stages)}, all\n")
        return 2
    head, cfg = commit(), config()
    run = CACHE / "runs" / head
    for stage in wanted:
        log(f"stage {stage} ({head})")
        stages[stage](run, head, cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
