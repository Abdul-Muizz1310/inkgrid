# M5d-1 Heavy Competitors and the Text-Layer Ablation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Score Docling (default and forced OCR), marker (text layer only), and unstructured `hi_res`
with Tesseract on spec 12's datasets and metrics, and the ablation that feeds inkgrid's gridders
Tesseract's words, so the README can say where inkgrid stands against OCR and vision readers.

**Architecture:** Pure conversions (`html_tables.py`, `heavy.py`) turn each tool's output into spec 12's
normalized tables and are tested without the tools installed; thin adapters import each tool inside
its own isolated environment. A batch mode runs a heavy tool's documents in one process with
per-document deadlines. Tesseract comes from conda-forge through a pinned micromamba.

**Tech Stack:** Python 3.12, uv, pytest 9, Ruff, mypy `--strict` (bench typed like `src`); Docling
2.131.0, marker-pdf 2.0.0, unstructured 0.27.10, Tesseract 5.5.3, micromamba 2.3.2.

**Spec:** `docs/specs/15-heavy-competitors.md`

## Global Constraints

- Everything in spec 15 §§ 1–5 is fixed before any of these tools is scored; probes score nothing.
- spec 12's four tools and their one-process-per-document mode stay exactly as they are.
- No tool is installed into inkgrid's own environment; the heavy tools run only in `uv run --isolated`.
- The full run happens once, after the final review's fixes, one document at a time, niced.
- ASCII-only source; Conventional Commits, a subject of at most 72 characters, no trailer.

## Review Focus

1. **A tool scored on something it did not output**: a box in the wrong frame (bottom-left vs top-left,
   pixels vs points, a rotated page), a page off by one (marker's 0-based ids), a header flag invented.
2. **A timeout or crash that loses other documents' readings**: the batch must resume after the
   failing document, and a finished document must never be re-read or overwritten.
3. **Time charged to the wrong document**: model loading inside the first document's seconds.
4. **The ablation changing more than the words**: rules, fills, Camelot's grids, or the furniture and
   pipeline profile must be inkgrid's own; only the words come from Tesseract.
5. **Claims the intervals do not support**: README rows for the competitors stated as wins.

---

### Task 1: HTML tables

**Files:** `bench/inkgrid_bench/html_tables.py`, `bench/tests/test_html_tables.py`.

- [ ] HT1, HT2, HT3 (FAIL); implement `cells_from_html(html: str) -> list[NCell]` with the standard
  library's `html.parser`; run (PASS); commit `feat(bench): read HTML tables as normalized cells`.

### Task 2: The tools' outputs

**Files:** `bench/inkgrid_bench/heavy.py`, `bench/tests/test_heavy.py`.

- [ ] DC1, MK1, US1 (FAIL); implement `docling_tables(doc: dict, heights: dict[int, float])`,
  `marker_tables(rendered: dict)`, `unstructured_tables(elements: list[dict], sizes: dict[int,
  tuple[float, float]])`, each `-> list[NTable]`, over plain data each adapter extracts; run (PASS);
  commit `feat(bench): normalize Docling, marker, and unstructured tables`.

### Task 3: Batch mode

**Files:** `bench/inkgrid_bench/adapters/_cli.py`, `bench/inkgrid_bench/run.py`,
`bench/tests/test_run.py`.

- [ ] BM1, BM2, BM3 (FAIL, with a fake adapter script); implement `_cli.batch(read)` (manifest of
  `pdf\tout` lines, `done N` after each), `run.deadline(pages: int) -> float`, and
  `run.read_batch(cmd, docs, *, tool, version) -> Iterator[tuple[Doc, NDocument]]` (restart after a
  timeout or a dead process; skip documents already read); run (PASS); commit
  `feat(bench): run a heavy tool's documents in one process`.

### Task 4: Tesseract and the ablation

**Files:** `bench/sources.toml`, `bench/inkgrid_bench/fetch.py`, `bench/inkgrid_bench/run.py`,
`bench/inkgrid_bench/ablation.py`, `bench/inkgrid_bench/adapters/inkgrid_ocr.py`,
`bench/tests/test_ablation.py`.

- [ ] AB1, AB2 (FAIL); implement `words_from_tsv(tsv: str, page: int, scale: float, first_id: int) ->
  list[Word]` and `ocr_reading(reading, ocr: Callable[[bytes, int], str]) -> Reading`; pin micromamba
  2.3.2 (URL, SHA-256) and `tesseract=5.5.3` in `sources.toml`; `prepare` creates the prefix; run
  (PASS); commit `feat(bench): feed inkgrid's gridders Tesseract's words`.

### Task 5: The adapters and the report

**Files:** `bench/inkgrid_bench/adapters/{docling_tables,marker_tables,unstructured_tables}.py`,
`bench/inkgrid_bench/run.py`, `bench/inkgrid_bench/report.py`, `bench/tests/test_report.py`.

- [ ] RP1 (FAIL); add the five tools to `tools()` and `report.TOOLS`, the adapters (thin: the tool's
  call, then `heavy.py`), and the report's paragraph on OCR; run (PASS); probe each adapter on one
  document per dataset (scored nothing); commit `feat(bench): add the heavy competitors and the
  ablation`.

### Task 6: Acceptance

**Files:** `docs/specs/{12-benchmark,15-heavy-competitors}.md`, `README.md`, `CHANGELOG.md`,
`bench/README.md`, `bench/results/`.

- [ ] `scripts/dev.sh` passes; the final review and its fixes; then the full run, one document at a
  time; commit `bench/results/<date>-<commit>-tuned/`, `latest.md`, README's rows and what they
  support, the spec amendments, and the CHANGELOG.
