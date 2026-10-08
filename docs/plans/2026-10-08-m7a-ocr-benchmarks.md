# M7a OCR Benchmarks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this
> plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** inkgrid's untuned baseline against OCR and text-layer tools on the born-digital text and table
parts of olmOCR-bench, OmniDocBench, ParseBench and DP-Bench, with intervals.

**Architecture:** a census (pure classification over PyMuPDF page statistics) fixes the scored
documents and a dev/test split; every tool writes one Markdown file per document (tables as HTML where
the tool offers it); one driver per benchmark feeds each pinned, unmodified scorer and reads per-document
values back; `ocr_run.py` runs it all one document at a time and reports with spec 12's statistics.

**Tech Stack:** PyMuPDF census; olmocr 0.4.27; OmniDocBench v1_0 evaluation; parse-bench 1.0.4;
opendataloader-bench's evaluator; spec 15's heavy-tool environments; pymupdf4llm 1.28.2, MarkItDown
0.1.8, LiteParse 2.15.1.

**Spec:** `docs/specs/18-ocr-benchmarks.md`

## Global Constraints

- The census manifests are committed before any benchmarked tool reads a page (spec 18 § 2).
- `src/inkgrid` is not changed in M7a: the baseline is 0.1.0's reading.
- Nothing downloaded is committed or executed; every download is checked against a pinned SHA-256.
- One document at a time, niced; heavy tools batched with spec 15's deadlines.
- ASCII-only source; Conventional Commits, a subject of at most 72 characters, no trailer.

## Review Focus

1. **A scorer fed differently per tool**: a converter applied to one tool's tables and not another's,
   or furniture dropped for one tool by the harness rather than by the tool.
2. **Documents silently missing from a score**: a crashed tool's document absent instead of empty, or a
   scorer that skips documents without a prediction.
3. **The census leaking**: a scan, OCR layer or image-backed page scored, or a born-digital page dropped
   by a scorer's own filter.
4. **Per-document values that do not reproduce the scorer's own aggregate** (a pooled metric
   bootstrapped as a mean, or the reverse).
5. **Claims beyond the intervals**, or an "Overall" quoted for a subset.

---

### Task 1: Census and split

**Files:** `bench/inkgrid_bench/census.py`, `bench/tests/test_census.py`, manifests under `bench/ocr/`.

- [ ] CS1, CS2, CS3, SP1 (FAIL); implement `classify(stats) -> PageClass`, `document_class`,
  `page_stats(page)`, `split(benchmark, doc_id)`; run (PASS); run the census over the fetched data and
  commit the manifests; commit `feat(bench): classify benchmark pages before scoring them`.

### Task 2: Page Markdown

**Files:** `bench/inkgrid_bench/page_markdown.py`, `bench/tests/test_page_markdown.py`.

- [ ] MD1, MD2 (FAIL); implement `pipe_to_html(markdown) -> str`, `inkgrid_markdown(doc) -> str`; run
  (PASS); commit `feat(bench): write each tool's page as Markdown with HTML tables`.

### Task 3: Adapters

**Files:** `bench/inkgrid_bench/tables.py` (`NDocument.markdown`), `bench/inkgrid_bench/heavy.py`, the
adapters, `bench/inkgrid_bench/run.py` (`tools()`), `bench/sources.toml`.

- [ ] AD1, AD2, AD3 (FAIL); Docling and unstructured converters, marker's HTML tables, the three
  text-layer converters as tools; inkgrid and inkgrid on Tesseract's words write Markdown; run (PASS);
  commit `feat(bench): read whole pages with every tool`.

### Task 4: Scorer drivers

**Files:** `bench/inkgrid_bench/scores/{olmocr_pages,omnidocbench,parsebench,dpbench}.py`, tests.

- [ ] SC1–SC4 (FAIL); implement each driver against its pinned scorer; run (PASS); check each driver
  reproduces its scorer's published number for one committed competitor output where one exists
  (opendataloader-bench's committed engines); commit `feat(bench): score the OCR benchmarks' pages`.

### Task 5: The run and the report

**Files:** `bench/inkgrid_bench/ocr_run.py`, `bench/inkgrid_bench/run.py`, `bench/inkgrid_bench/report.py`.

- [ ] RP1, RN1 (FAIL); implement; run (PASS); commit `feat(bench): run the OCR benchmarks`.

### Task 6: The baseline run

- [ ] Final review and its fixes; the run in a clean checkout, one document at a time; commit the results
  and the README's numbers labelled baseline, born-digital text and tables only.
