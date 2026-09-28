# M5b The Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Score inkgrid's baseline and three text-layer peers on ICDAR-2013 (competition and practice)
and olmOCR-bench's table tests with the pre-registered metrics of spec 12, and commit the results with
confidence intervals.

**Architecture:** `bench/inkgrid_bench` is a stdlib-plus-inkgrid package in the repo (not shipped).
Adapters run inside each tool's pinned, isolated environment and write a normalized table JSON; renderers
turn it into each scorer's input; third-party scorers (the ICDAR jar, Soric et al.'s evaluator, olmOCR's
scorer) run as subprocesses in their own environments; a pure bootstrap turns per-document results into
intervals; `run.py` orchestrates and `report.py` writes `bench/results/`.

**Tech Stack:** Python 3.12+, uv, pytest 9, Hypothesis, Ruff, mypy `--strict`; Temurin 17 JRE;
pdfplumber 0.11.10 (a `bench` dependency group, never a runtime dependency).

**Spec:** `docs/specs/12-benchmark.md`

## Global Constraints

- Spec 12 §§ 1–5 are frozen: no metric, dataset, tool version, or output rule changes after a tool is
  scored. A needed change is a ruling in the ledger and a dated amendment in the spec, and the run is
  repeated in full.
- Runs are sequential, one document at a time, niced; data and tools live in `~/.cache/inkgrid-bench/`.
- `bench/` imports inkgrid's public API only, and ships in neither the wheel nor the sdist.
- Spec-TDD for every bench module; ASCII-only source; Conventional Commits, no trailer.

## Review Focus

1. **Unit mistakes in coordinates**: top-left against bottom-left origin, CropBox offsets, Soric et al.'s
   pixel scale (RD3), rotated pages.
2. **A metric computed differently for inkgrid than for a peer**: every tool goes through the same
   normalized table and the same renderers.
3. **Bootstrap clustering**: resampling documents, not tables or tests; the same resample for paired
   differences.
4. **Silent drops**: a crash, timeout, or missing output must count as no tables, never as a skipped
   document.
5. **Undefined precision** (no detected table in a document) handled as the spec says (SC2).

---

### Task 1: Scaffold, sources, fetch, and the normalized table

**Files:** `bench/sources.toml`, `bench/inkgrid_bench/{__init__,fetch,tables}.py`, `bench/tests/test_tables.py`,
`bench/tests/test_fetch.py`; `pyproject.toml` (pytest testpaths and pythonpath, mypy files, ruff src,
a `bench` dependency group with `pdfplumber==0.11.10`); `bench/README.md`.

- [ ] NT1, NT2, and fetch's hash check (a mismatch raises and deletes the file) as tests (FAIL);
  implement; run (PASS); commit `feat(bench): add sources, fetch, and the normalized table`.

### Task 2: Renderers

**Files:** `bench/inkgrid_bench/render.py`, `bench/tests/test_render.py`.

- [ ] RD1 (skipped without the cached JRE and jar), RD2, RD3 as tests (FAIL); implement ICDAR `-str`/`-reg`
  XML, Soric predictions, olmOCR page HTML; run (PASS); commit `feat(bench): render tables for each scorer`.

### Task 3: Adapters

**Files:** `bench/inkgrid_bench/adapters/{inkgrid,pdfplumber,pymupdf,camelot}.py`, `bench/tests/test_adapters.py`.

- [ ] Each adapter on `ruled_grid` and `unruled_table` fixtures: tables found, spans as drawn (FAIL);
  implement; run (PASS); commit `feat(bench): add tool adapters`.

### Task 4: Scores

**Files:** `bench/inkgrid_bench/scores/{icdar,soric,olmocr,binding}.py`, `bench/tests/test_scores.py`.

- [ ] SC1, SC2, BD1–BD4 as tests (FAIL); implement (the jar's output parser and per-document
  aggregation; Soric et al.'s predictions writer and result reader; olmOCR candidate writer and result
  reader; binding); run (PASS); commit `feat(bench): add the scorers`.

### Task 5: Statistics

**Files:** `bench/inkgrid_bench/stats.py`, `bench/tests/test_stats.py`.

- [ ] BS1–BS3 and a property (the interval contains the point estimate) as tests (FAIL); implement;
  run (PASS); commit `feat(bench): add the clustered bootstrap`.

### Task 6: The run and the results

**Files:** `bench/inkgrid_bench/{run,report}.py`, `bench/results/`, `README.md`, `CHANGELOG.md`,
`docs/specs/12-benchmark.md` § 0.

- [ ] Run everything, one document at a time; commit `bench/results/<date>-<commit>/` and `latest.md`;
  check Soric et al.'s reproduction row; update README (the baseline table, only claims the intervals
  support) and CHANGELOG; `scripts/dev.sh` passes; commit `feat(bench): record the M5b baseline`.
