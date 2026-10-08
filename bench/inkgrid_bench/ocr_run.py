"""The OCR benchmarks' run: `run.py --datasets ocr` (docs/specs/18-ocr-benchmarks.md s. 6).

Its own stages, so spec 12's run is untouched. Every stage that reads, scores or reports refuses to
start unless each benchmark's data and census manifest are the pinned ones (RN1); only the census's
born-digital documents in the scored groups are read and scored, one document at a time, niced.
Each scorer runs unmodified at its pin, in its own environment, through its driver (s. 4).
"""

import contextlib
import itertools
import json
import os
import shutil
import subprocess
import tomllib
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from inkgrid_bench import fetch, ocr_data, ocr_report, run
from inkgrid_bench.ocr_data import BenchDoc
from inkgrid_bench.scores import dpbench, olmocr_pages, omnidocbench, parsebench
from inkgrid_bench.tables import NDocument

type Stage = Callable[[Path, str, dict[str, Any]], None]
type DocCounts = dict[str, dict[str, float]]
type Scorer = Callable[[Path, dict[str, Any], Sequence[BenchDoc], Mapping[str, str]], DocCounts]

CENSUS = run.BENCH / "ocr"
BENCHMARKS = tuple(ocr_report.BENCHMARKS)
STAGES = ("prepare", "read", "score", "report")
PIPELINE = "inkgrid_bench_saved"  # the ParseBench pipeline that returns the saved Markdown
SCORER_TIMEOUT = 4 * 3600  # seconds for one scorer on one tool's documents of one benchmark
SCORERS_USED = ("olmocr", "omnidocbench", "parsebench", "opendataloader")
# A heavy tool reads at most this many documents per process, its models loaded once per batch: a
# failure, or a run stopped and resumed, then re-renders and re-starts at most one batch.
BATCH_DOCUMENTS = 100
WARM_TIMEOUT = 3600  # seconds to build one environment the first time
# What a tool's reading depends on besides its pin: the readings of a run at another commit carry
# over only when none of it changed, and inkgrid's own only when src/inkgrid did not (RR1).
READING_CODE = (
    "bench/inkgrid_bench/adapters",
    "bench/inkgrid_bench/ablation.py",
    "bench/inkgrid_bench/heavy.py",
    "bench/inkgrid_bench/page_markdown.py",
    "bench/inkgrid_bench/pages.py",
    "bench/inkgrid_bench/run.py",
    "bench/inkgrid_bench/tables.py",
)
INKGRID_CODE = ("src/inkgrid", "uv.lock")
INKGRID_TOOLS = ("inkgrid", "inkgrid-ocr")
PINS = ("tool", "tesseract")  # the sources.toml tables a reading depends on
BASELINE_READING = "v0.1.0"  # the release whose reading a baseline run measures (DR-0023)
ENGINE = "candidate"  # the engine folder opendataloader-bench's evaluator scores


def dataset(benchmark: str) -> str:
    """The run's dataset name for a benchmark's readings."""
    return f"ocr-{benchmark}"


def census(benchmark: str) -> dict[str, Any]:
    """The benchmark's committed census manifest (spec 18 section 2)."""
    return run.load(CENSUS / f"census-{benchmark}.json")


def verify_listing(listing: Path, root: Path) -> None:
    """Every file a `sha256sum`-style listing names holds its pinned bytes in `root` (RN1).

    Raises:
        RuntimeError: naming the first file that is missing or holds other bytes.
    """
    for line in listing.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        pinned, relative = line.split(maxsplit=1)
        path = root / relative
        if not path.is_file():
            msg = f"{path} is missing; `run.py --datasets ocr prepare` fetches it"
            raise RuntimeError(msg)
        found = fetch.digest(path)
        if found != pinned:
            msg = f"{path}: SHA-256 {found} is not the pinned {pinned} ({listing.name})"
            raise RuntimeError(msg)


def verify_census(
    manifest: Mapping[str, Any], docs: Sequence[BenchDoc], *, revision: str, path: Path
) -> None:
    """The census is the pinned revision's, over exactly these documents and bytes (RN1).

    Raises:
        RuntimeError: naming the census or the PDF that does not match.
    """
    if manifest["revision"] != revision:
        msg = f"{path} is a census of revision {manifest['revision']}; the pin is {revision}"
        raise RuntimeError(msg)
    pinned: Mapping[str, Mapping[str, Any]] = manifest["documents"]
    listed = {d.id for d in docs}
    unlisted = sorted(set(pinned) ^ listed)
    if unlisted:
        msg = f"{path} and the benchmark differ on {len(unlisted)} documents: {unlisted[:5]}"
        raise RuntimeError(msg)
    for doc in docs:
        found = fetch.digest(doc.pdf)
        if found != pinned[doc.id]["sha256"]:
            msg = f"{doc.pdf}: SHA-256 {found} is not the census's {pinned[doc.id]['sha256']}"
            raise RuntimeError(msg)


def _git(*args: str, repo: Path = run.REPO) -> str:
    return subprocess.run(  # noqa: S603 - fixed arguments
        ["git", "-C", str(repo), *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def verify_clone(repo: Path, commit: str) -> None:
    """A clone of a scorer or of data is at its pinned commit, with no change to a tracked file."""
    head = _git("rev-parse", "HEAD", repo=repo)
    if head != commit:
        msg = f"{repo} is at {head}, not the pinned {commit}"
        raise RuntimeError(msg)
    changes = _git("status", "--porcelain", "--untracked-files=no", repo=repo)
    if changes:
        msg = f"{repo} has changes to tracked files: {changes.splitlines()[:5]}"
        raise RuntimeError(msg)


def clone(repository: str, commit: str, target: Path) -> None:
    """The repository at `commit` in `target`, cloned once and verified each time."""
    if not target.exists():
        run.log(f"clone {repository} at {commit[:7]} -> {target}")
        git = ["git", "-c", "advice.detachedHead=false"]
        subprocess.run([*git, "clone", "--quiet", repository, str(target)], check=True)  # noqa: S603
        subprocess.run([*git, "-C", str(target), "checkout", "--quiet", commit], check=True)  # noqa: S603
    verify_clone(target, commit)


def checked(benchmark: str, cfg: dict[str, Any]) -> list[BenchDoc]:
    """The benchmark's scored documents, once its data and census are the pinned ones (RN1)."""
    pin = cfg["ocr"][benchmark]
    root = run.CACHE / pin["root"]
    if "list" in pin:
        verify_listing(run.BENCH / pin["list"], root)
    else:
        verify_clone(root, pin["revision"])
    docs = ocr_data.documents(benchmark)
    manifest = census(benchmark)
    path = CENSUS / f"census-{benchmark}.json"
    verify_census(manifest, docs, revision=pin["revision"], path=path)
    return ocr_data.scored(docs, manifest["documents"])


def warm(cfg: dict[str, Any]) -> None:
    """Every OCR tool's environment built and its adapter imported, and every scorer's built.

    The read stage then runs offline: a tool that cannot start fails here, never as a reading.
    """
    for tool in tools(cfg):
        if tool.package is not None:
            cmd = [
                *run.environment(tool),
                "python",
                "-c",
                f"import inkgrid_bench.adapters.{tool.module}",
            ]
            _warmed(cmd, tool.name)
    for name in SCORERS_USED:
        _warmed([*_scorer_env(cfg, name), "python", "-c", "pass"], f"the {name} scorer")


def _warmed(cmd: Sequence[str], what: str) -> None:
    code, _, err = run.run_process(cmd, timeout=WARM_TIMEOUT)
    if code != 0:
        msg = f"{what}'s environment does not start: {run.last_line(err) or f'exit status {code}'}"
        raise RuntimeError(msg)
    run.log(f"prepare: {what}'s environment is ready")


def prepare(_run: Path, _head: str, cfg: dict[str, Any]) -> None:
    """Spec 12's tools and Tesseract, then every OCR benchmark, scorer and environment, verified.

    Every tool's and scorer's environment is built here, so the read stage can run offline.
    """
    run.prepare(cfg)
    for pin in cfg["ocr"].values():
        if "list" in pin:
            fetch.fetch_manifest(pin["url"], run.BENCH / pin["list"], pin["root"], run.CACHE)
        else:
            clone(pin["repository"], pin["revision"], run.CACHE / pin["root"])
    omni = cfg["scorer"]["omnidocbench"]
    clone(omni["repository"], omni["commit"], run.CACHE / omni["root"])
    for benchmark in BENCHMARKS:
        run.log(f"prepare: {benchmark} verified, {len(checked(benchmark, cfg))} documents scored")
    warm(cfg)


def _doc(doc: BenchDoc) -> run.Doc:
    return run.Doc(doc.id, doc.pdf)


def tools(cfg: dict[str, Any]) -> list[run.Tool]:
    """The OCR run's tools (spec 18 section 3), in the report's order."""
    by_name = {t.name: t for t in run.tools(cfg)}
    return [by_name[name] for name in ocr_report.TOOLS]


@contextlib.contextmanager
def _offline() -> Iterator[None]:
    """Uv neither resolves nor downloads while tools read: their environments are built already."""
    before = os.environ.get("UV_OFFLINE")
    os.environ["UV_OFFLINE"] = "1"
    try:
        yield
    finally:
        if before is None:
            del os.environ["UV_OFFLINE"]
        else:
            os.environ["UV_OFFLINE"] = before


def _save(out: Path, reading: NDocument) -> None:
    """A reading, whole or not at all: a killed write leaves no reading for resume to skip."""
    out.parent.mkdir(parents=True, exist_ok=True)
    part = out.with_suffix(".part")
    part.write_text(reading.to_json(), encoding="utf-8")
    part.replace(out)


def read(run_dir: Path, head: str, cfg: dict[str, Any]) -> None:
    """Every tool on every scored document, one at a time, offline; finished readings are kept."""
    scored = {b: checked(b, cfg) for b in BENCHMARKS}
    with _offline():
        for tool in tools(cfg):
            _read_tool(run_dir, tool, run.command(tool), run.version(tool, head), scored)


def _read_tool(
    run_dir: Path,
    tool: run.Tool,
    cmd: Sequence[str],
    ver: str,
    scored: Mapping[str, Sequence[BenchDoc]],
) -> None:
    for benchmark, docs in scored.items():
        name = dataset(benchmark)
        todo = [
            _doc(d)
            for d in docs
            if not run.reading_path(run_dir, tool.name, name, _doc(d)).exists()
        ]
        batches = itertools.batched(todo, BATCH_DOCUMENTS) if tool.batch else [tuple(todo)]
        for batch in batches:
            for doc, reading in run.tool_readings(tool, cmd, ver, list(batch)):
                _save(run.reading_path(run_dir, tool.name, name, doc), reading)
                note = (
                    f" ERROR {reading.error}"
                    if reading.error
                    else f" {len(reading.markdown)} chars"
                )
                run.log(f"read {tool.name} {name} {doc.id}{note}")


def changed_files(commit: str, paths: Sequence[str]) -> list[str]:
    """The committed files under `paths` that differ between `commit` and HEAD."""
    return _git("diff", "--name-only", commit, "HEAD", "--", *paths).split()


def pins_at(commit: str) -> dict[str, Any]:
    """The tool pins `sources.toml` held at `commit`."""
    data = tomllib.loads(_git("show", f"{commit}:bench/sources.toml"))
    return {key: data.get(key) for key in PINS}


def reusable(
    commit: str,
    cfg: Mapping[str, Any],
    *,
    changed: Callable[[str, Sequence[str]], list[str]] = changed_files,
    pins: Callable[[str], Mapping[str, Any]] = pins_at,
) -> tuple[str, ...]:
    """The tools whose readings at `commit` this commit would read alike (spec 18 s. 6, RR1).

    Raises:
        RuntimeError: the reading code or a tool's pin changed since, so every tool reads again.
    """
    moved = changed(commit, READING_CODE)
    if moved:
        msg = f"the reading code changed since {commit} ({', '.join(moved[:5])}); read again"
        raise RuntimeError(msg)
    if dict(pins(commit)) != {key: cfg.get(key) for key in PINS}:
        msg = f"the tool pins changed since {commit}; read again"
        raise RuntimeError(msg)
    fixed = INKGRID_TOOLS if changed(commit, INKGRID_CODE) else ()
    return tuple(t for t in ocr_report.TOOLS if t not in fixed)


def link_readings(source: Path, target: Path, tool_names: Sequence[str]) -> int:
    """Hard-link the tools' OCR readings from the run `source` into `target`; how many it linked.

    A reading `target` already holds is kept.
    """
    linked = 0
    for tool in tool_names:
        for benchmark in BENCHMARKS:
            folder = source / "readings" / tool / dataset(benchmark)
            for path in sorted(folder.glob("*.json")):
                dest = target / "readings" / tool / dataset(benchmark) / path.name
                if dest.exists():
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.link(path, dest)
                linked += 1
    return linked


def carry_over(run_dir: Path, commit: str, cfg: dict[str, Any]) -> None:
    """Link the readings of the run at `commit` that this commit would read alike, and record them.

    The record is `readings-from.json` in this run; the read stage then reads only the rest.
    """
    short = _git("rev-parse", "--short=7", commit)
    source = run.CACHE / "runs" / short
    if not source.is_dir():
        msg = f"no run at {short} in {source.parent}"
        raise RuntimeError(msg)
    names = reusable(short, cfg)
    linked = link_readings(source, run_dir, names)
    run.save(run_dir / "readings-from.json", {"commit": short, "tools": list(names)})
    run.log(f"read: {linked} readings of {', '.join(names)} carried over from {short}")


def reading(run_dir: Path, tool: str, benchmark: str, doc: BenchDoc) -> NDocument:
    """A tool's reading of a scored document; one not yet read is refused."""
    path = run.reading_path(run_dir, tool, dataset(benchmark), _doc(doc))
    return NDocument.from_json(path.read_text(encoding="utf-8"))


def _scorer_env(cfg: dict[str, Any], name: str) -> list[str]:
    """A scorer's pinned environment, niced."""
    pin = cfg["scorer"][name]
    packages = [pin["package"]] if "package" in pin else []
    env = run.isolated(
        [*packages, *pin.get("with", [])],
        python=pin.get("python", run.TOOL_PYTHON),
        exclude_newer=pin.get("exclude-newer"),
    )
    return [*run.NICE, *env]


def call(cmd: Sequence[str], what: str, log: Path, cwd: Path | None = None) -> str:
    """Run a scorer, keeping all it prints in `log`; its output, or a failure naming the log."""
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        code, out, err = run.run_process(cmd, timeout=SCORER_TIMEOUT, cwd=cwd)
    except TimeoutError as exc:
        log.write_text(f"{what}: {exc}\n", encoding="utf-8")
        msg = f"{what} failed: {exc}; see {log}"
        raise RuntimeError(msg) from exc
    log.write_text(f"{out}\n--- stderr ---\n{err}", encoding="utf-8")
    if code != 0:
        msg = f"{what} failed: {run.last_line(err) or f'exit status {code}'}; see {log}"
        raise RuntimeError(msg)
    return out


def score_olmocr(
    work: Path, cfg: dict[str, Any], docs: Sequence[BenchDoc], markdown: Mapping[str, str]
) -> DocCounts:
    """olmOCR-bench's tests of the scored PDFs, by its own code (spec 18 section 4)."""
    shutil.rmtree(work, ignore_errors=True)
    ids = [d.id for d in docs]
    olmocr_pages.write_candidate(work / "candidate", ids, markdown)
    (work / "pdfs.txt").write_text("\n".join(ids) + "\n", encoding="utf-8")
    out = work / "results.json"
    driver = "inkgrid_bench.scores.olmocr_pages_driver"
    data = ocr_data.LOCATIONS["olmocr"][0]
    groups = [f"{group}={name}" for group, name in olmocr_pages.GROUPS.items()]
    args = [str(data), str(work / "candidate"), str(work / "pdfs.txt"), str(out), *groups]
    env = _scorer_env(cfg, "olmocr")
    call([*env, "python", "-m", driver, *args], "olmOCR-bench's scorer", work / "scorer.log")
    result = run.load(out)
    if result["errors"]:
        msg = f"olmOCR-bench's scorer met {len(result['errors'])} errors: {result['errors'][0]}"
        raise RuntimeError(msg)
    return olmocr_pages.pdf_counts(result["results"], ids)


def score_omnidocbench(
    work: Path, cfg: dict[str, Any], docs: Sequence[BenchDoc], markdown: Mapping[str, str]
) -> DocCounts:
    """OmniDocBench's end-to-end evaluation of the scored pages, by its own code (section 4)."""
    shutil.rmtree(work, ignore_errors=True)
    ids = [d.id for d in docs]
    data = ocr_data.LOCATIONS["omnidocbench"][0]
    pages = json.loads((data / "OmniDocBench.json").read_text(encoding="utf-8"))
    truth = work / "truth.json"
    truth.parent.mkdir(parents=True)
    truth.write_text(json.dumps(omnidocbench.subset(pages, set(ids))), encoding="utf-8")
    predictions = work / "predictions"
    omnidocbench.write_predictions(predictions, ids, markdown)
    config = work / "config.yaml"
    config.write_text(omnidocbench.config_yaml(truth, predictions), encoding="utf-8")
    (work / "result").mkdir()  # the scorer writes to ./result and does not make it
    script = run.CACHE / cfg["scorer"]["omnidocbench"]["root"] / "pdf_validation.py"
    env = _scorer_env(cfg, "omnidocbench")
    cmd = [*env, "python", str(script), "--config", str(config)]
    log = call(cmd, "OmniDocBench's scorer", work / "scorer.log", work)
    missing = omnidocbench.unpredicted(log)
    if missing:
        msg = f"OmniDocBench's scorer found no prediction for {len(missing)} pages: {missing[:5]}"
        raise RuntimeError(msg)
    name = omnidocbench.save_name(predictions)
    pages = omnidocbench.page_counts(work / "result", name, ids)
    for page in omnidocbench.fallbacks(log):
        pages[page]["omni_fallback"] = 1  # matched the simple way: listed in the report
    result = run.load(work / "result" / f"{name}_metric_result.json")
    problems = omnidocbench.check(pages, {d.id: d.group for d in docs}, result)
    if problems:
        msg = f"OmniDocBench's pages do not reproduce its own averages: {'; '.join(problems)}"
        raise RuntimeError(msg)
    return pages


def score_parsebench(
    work: Path, cfg: dict[str, Any], docs: Sequence[BenchDoc], markdown: Mapping[str, str]
) -> DocCounts:
    """ParseBench's table and text evaluations of the scored documents, by its own code."""
    shutil.rmtree(work, ignore_errors=True)
    saved = work / "saved"
    parsebench.write_saved(saved, [d.id for d in docs], markdown)
    data = ocr_data.LOCATIONS["parsebench"][0]
    env = _scorer_env(cfg, "parsebench")
    out: DocCounts = {}
    tracks = (
        ("table", [d.id for d in docs if d.group == "table"], parsebench.TABLE_METRICS),
        ("text_content", [d.id for d in docs if d.group != "table"], parsebench.TEXT_METRICS),
    )
    for group, ids, metrics in tracks:
        if not ids:
            continue
        target = work / f"out-{group}"
        driver = ["python", "-m", "inkgrid_bench.scores.parsebench_driver"]
        args = [str(data), str(saved), str(target), group, PIPELINE]
        call([*env, *driver, *args], f"ParseBench's {group} scorer", work / f"{group}.log", work)
        result = run.load(target / PIPELINE / "_evaluation_report.json")
        out |= parsebench.document_scores(result, ids, metrics)
    return out


def score_dpbench(
    work: Path, cfg: dict[str, Any], docs: Sequence[BenchDoc], markdown: Mapping[str, str]
) -> DocCounts:
    """DP-Bench's NID, TEDS and MHS of the scored pages, by opendataloader-bench's evaluator."""
    shutil.rmtree(work, ignore_errors=True)
    ids = [d.id for d in docs]
    root = work / "prediction"
    dpbench.write_predictions(root, ENGINE, ids, markdown)
    repo = ocr_data.LOCATIONS["dpbench"][0]
    args = [
        "--ground-truth-dir", str(repo / "ground-truth" / "markdown"),
        "--prediction-root", str(root),
        "--engine", ENGINE,
        "--log-level", "WARNING",
    ]  # fmt: skip
    env = _scorer_env(cfg, "opendataloader")
    cmd = [*env, "python", str(repo / "src" / "evaluator.py"), *args]
    call(cmd, "DP-Bench's scorer", work / "scorer.log", work)
    return dpbench.document_scores(run.load(root / ENGINE / "evaluation.json"), ids)


SCORERS: dict[str, Scorer] = {
    "olmocr": score_olmocr,
    "omnidocbench": score_omnidocbench,
    "parsebench": score_parsebench,
    "dpbench": score_dpbench,
}


def score(run_dir: Path, _head: str, cfg: dict[str, Any]) -> None:
    """Every benchmark's scorer on every tool's readings; finished scores are kept."""
    scored = {b: checked(b, cfg) for b in BENCHMARKS}
    for tool in ocr_report.TOOLS:
        for benchmark, docs in scored.items():
            out = run_dir / "ocr" / benchmark / f"{tool}.json"
            if out.exists():
                continue
            markdown = {d.id: reading(run_dir, tool, benchmark, d).markdown for d in docs}
            work = run_dir / "ocr" / benchmark / tool
            run.save(out, SCORERS[benchmark](work, cfg, docs, markdown))
            run.log(f"score {benchmark} {tool}")


def filled(by_tool: Mapping[str, Mapping[str, Mapping[str, float]]]) -> dict[str, DocCounts]:
    """Every document's counts with every key any document has: a key it lacks counts 0."""
    keys = {k for per_doc in by_tool.values() for c in per_doc.values() for k in c}
    return {
        tool: {doc: {k: float(c.get(k, 0)) for k in sorted(keys)} for doc, c in per_doc.items()}
        for tool, per_doc in by_tool.items()
    }


def gather(run_dir: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    """Each scored document's group, half and stratum, each tool's counts, crashes, the census."""
    mask = ocr_data.LOCATIONS["omnidocbench"][0] / "with_mask.json"
    masked = {str(name).removesuffix(".jpg") for name in json.loads(mask.read_text("utf-8"))}
    documents: dict[str, dict[str, dict[str, Any]]] = {}
    counts: dict[str, dict[str, DocCounts]] = {}
    crashes: dict[str, dict[str, list[list[str]]]] = {}
    classes: dict[str, dict[str, Any]] = {}
    left_out: dict[str, dict[str, list[str]]] = {}
    for benchmark in BENCHMARKS:
        docs = checked(benchmark, cfg)
        manifest = census(benchmark)["documents"]
        documents[benchmark] = {
            d.id: {
                "group": d.group,
                "half": manifest[d.id]["half"],
                "primary": d.id not in masked,  # OmniDocBench's pages with no masked area
            }
            for d in docs
        }
        classes[benchmark] = {
            "documents": len(manifest),
            "classes": dict(Counter(str(v["class"]) for v in manifest.values())),
        }
        left_out[benchmark] = ocr_data.excluded(manifest, {d.id for d in docs})
        by_tool: dict[str, dict[str, dict[str, float]]] = {}
        for tool in ocr_report.TOOLS:
            scores = run.load(run_dir / "ocr" / benchmark / f"{tool}.json")
            per_doc = {}
            for doc in docs:
                r = reading(run_dir, tool, benchmark, doc)
                if r.error:
                    crashes.setdefault(tool, {}).setdefault(benchmark, []).append([doc.id, r.error])
                per_doc[doc.id] = {
                    **scores[doc.id],
                    "seconds": r.seconds,
                    "pages": 0 if r.error else len(r.pages),
                    "crashed": 1 if r.error else 0,
                }
            by_tool[tool] = per_doc
        counts[benchmark] = filled(by_tool)
    carried = run_dir / "readings-from.json"
    return {
        "documents": documents,
        "counts": counts,
        "census": classes,
        "crashes": crashes,
        "excluded": left_out,
        "readings_from": run.load(carried) if carried.exists() else None,
    }


def environments(cfg: dict[str, Any]) -> dict[str, Any]:
    """Spec 12's environment record, and each OCR scorer's resolved packages."""
    out = run.environments(cfg)
    dump = (
        "import importlib.metadata as m, json; "
        "print(json.dumps({d.metadata['Name']: d.version for d in m.distributions()}))"
    )
    for name in SCORERS_USED:
        _, stdout, _ = run.run_process([*_scorer_env(cfg, name), "python", "-c", dump], timeout=600)
        out[f"scorer-{name}"] = json.loads(stdout)
    return out


def results_dir(base: Path, date: str, head: str) -> Path:
    """Where an OCR run's results go (spec 18 section 6)."""
    return base / f"{date}-{head}-ocr"


def write_results(
    run_dir: Path, head: str, cfg: dict[str, Any], *, label: ocr_report.OcrLabel = "baseline"
) -> None:
    """The OCR run's results: counts, documents, checks, environments, and the report."""
    data = gather(run_dir, cfg)
    date = datetime.now(UTC).date().isoformat()
    target = results_dir(run.BENCH / "results", date, head)
    target.mkdir(parents=True, exist_ok=True)
    run.save(target / "counts.json", data["counts"])
    run.save(target / "documents.json", data["documents"])
    checks = {k: data[k] for k in ("census", "crashes", "excluded", "readings_from")}
    run.save(target / "checks.json", checks)
    run.save(target / "environment.json", environments(cfg))
    text = ocr_report.document(data, head=head, date=date, label=label)
    (target / "report.md").write_text(text, encoding="utf-8")
    run.log(f"report written to {target}")


def src_changed(tag: str) -> bool:
    """Whether `src/inkgrid` differs from `tag`'s; a tag git cannot compare with is refused."""
    code = subprocess.run(  # noqa: S603 - fixed arguments
        ["git", "diff", "--quiet", tag, "--", "src/inkgrid"],  # noqa: S607
        cwd=run.REPO,
        check=False,
    ).returncode
    if code not in {0, 1}:
        msg = f"git cannot compare src/inkgrid with {tag} (exit status {code})"
        raise RuntimeError(msg)
    return code == 1


def stages(label: ocr_report.OcrLabel, readings_from: str | None = None) -> dict[str, Stage]:
    """The OCR run's stages, in order; a baseline run reads and reports only 0.1.0's inkgrid.

    With `readings_from`, the read stage first carries over that run's readings where this commit
    would read alike (`carry_over`).
    """

    def baseline_only(stage: Stage) -> Stage:
        def checked_stage(run_dir: Path, head: str, cfg: dict[str, Any]) -> None:
            if label == "baseline" and src_changed(BASELINE_READING):
                msg = (
                    f"src/inkgrid differs from {BASELINE_READING}, whose reading a baseline run "
                    "measures; a run after a fix is labelled tuned (--label tuned)"
                )
                raise RuntimeError(msg)
            stage(run_dir, head, cfg)

        return checked_stage

    def report(run_dir: Path, head: str, cfg: dict[str, Any]) -> None:
        write_results(run_dir, head, cfg, label=label)

    def reading_stage(run_dir: Path, head: str, cfg: dict[str, Any]) -> None:
        if readings_from is not None:
            carry_over(run_dir, readings_from, cfg)
        read(run_dir, head, cfg)

    return dict(
        zip(
            STAGES,
            (prepare, baseline_only(reading_stage), score, baseline_only(report)),
            strict=True,
        )
    )
