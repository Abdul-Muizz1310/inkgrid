# 12 · The benchmark: datasets, tools, metrics, and the baseline (M5b)

**Implements:** `00-design.md` § 11.2–11.3 for the first datasets and the text-layer peers, § 2 success
criteria 1–2, and M5's exit criterion in part: results with confidence intervals committed, README claims
matching them. It records inkgrid's **baseline**: its reading as of M4 (`DR-0023`, knowledge graph).
**Everything in §§ 1–5 is fixed on 2026-09-28, before any tool is scored on these datasets.** The only
earlier runs on them were inkgrid's verifier (spec 11), which scores nothing.
**Modules** (all under `bench/`, in the repo, in neither the wheel nor the sdist):
- `bench/sources.toml`: every dataset, tool, and scorer, pinned by version, URL, and SHA-256;
- `bench/inkgrid_bench/fetch.py`: downloads into `~/.cache/inkgrid-bench/`, verifying each hash;
- `bench/inkgrid_bench/tables.py`: the normalized table every adapter writes (§ 3.1);
- `bench/inkgrid_bench/adapters/`: one module per tool, run inside that tool's own pinned environment;
- `bench/inkgrid_bench/render.py`: normalized tables as each scorer's input (§ 3.2);
- `bench/inkgrid_bench/scores/`: `icdar.py`, `soric.py`, `olmocr.py`, `binding.py` (§ 4);
- `bench/inkgrid_bench/stats.py`: the clustered bootstrap (§ 5);
- `bench/inkgrid_bench/run.py`, `report.py`: the run and its report; `bench/results/`: committed results.

---

## 0 · What was measured first (L19)

- **ICDAR-2013** (`tamirhassan.com`, 2013): the competition set (67 PDFs, 238 pages; 71 structure files,
  four of them second ground truths for another file's PDF) and the practice set (58 PDFs, 170 pages).
  The competition's own scorer, `dataset-tools-20180206.jar` (6,005,793 bytes), runs under Temurin 17's
  JRE; ground truth scored against itself gives 1.0 for every table.
- **The practice set's access paths** (`-fnc.csv`): 91 tables, 5,772 paths. Each path is a value and its
  labels along each of the table's dimensions (`Country`, `AT` | `Gross sample *`, `Number` | `848`),
  dimensions separated by empty fields. Mapped to the structure ground truth by table order, 5,053
  paths (87.5%) have a value that appears exactly among that table's cells; the other 719 are
  ground-truth inconsistencies (a path with no value, `3,6` against `3.6`). *Corrected 2026-09-29,
  after the first scoring:* those counts came from a parser that misread four files: eu-020
  separates its fields with semicolons, and us-007, us-008, and us-009 pad their table ids with empty
  fields (`,,,,,"0",,,,,`). Read correctly there are 92 tables (each file matching its structure
  ground truth) and 5,767 paths, of which 5,603 (97.2%) are checkable; the other 164 are the
  ground-truth inconsistencies.
- **Soric et al.** (KDD '26): their evaluator (v1.0.0) runs here on CPU from their released predictions.
  It reproduces their box scores and matching exactly. The per-table structure scores differ on 12 of
  Camelot's 130 matched tables, so F1-TEDS comes out 0.4931 here against their published 0.4983:
  their loader appears to pair tables in file-listing order.
- **olmOCR-bench tables**: 1,020 table tests on 188 single-page PDFs, 173 with a text layer; 308 of the
  tests are heading tests (`top_heading` 170, `left_heading` 138). Its scorer (`olmocr` 0.4.27) parses
  Markdown and HTML tables, honours spans, and treats `<th>`, `<thead>`, and, in Markdown, row 0 and
  column 0 as headings.
- **The peers** read one ICDAR page in 0.1 s (pdfplumber, PyMuPDF) to 0.4 s (Camelot). pdfplumber and
  PyMuPDF return cells with boxes and `None` for a merged cell's covered positions; PyMuPDF also marks a
  header. Camelot returns its grid, per-cell edges, and span flags.

**Measured while building the harness** (after §§ 1–5 were fixed; none of it changes a metric):

- **The jar's region mode** reads the PDF and crashes without three libraries it does not bundle:
  JAI 1.1.3's core, FontBox 1.8.2, and Commons Collections 3.2.2 (all pinned in `sources.toml`). With
  them, eu-001's regions scored against themselves are 7 of 7 complete and pure. It pairs each
  ground-truth region with one result region; every other result region is a false positive, and its
  characters count as detected wrongly. Structure mode prints each ground-truth table's counts
  against the result table matched to it, and no size for an unmatched one (the size comes from
  scoring the ground truth against itself); it then lists every result table matched to none, whose
  relations count as detected and none as correct.
- **Soric et al.'s evaluator** accepts only its own model names; every tool here is written as its
  `pymu` model, the name selecting only how each box's HTML is unpacked. Their loader pairs each imaged
  page's boxes with its HTML files, 156 tables over 67 documents.
- **The reproduction gap is not file-listing order**, as first guessed above: their evaluator gives
  the same numbers here with a sorted listing and under two hash seeds, with their own environment's
  library pins. Box scores reproduce exactly; of the 16 F1s of their four released predictions, 15
  reproduce within 0.01 of their released results, and PyMuPDF's F1-TEDS misses by 0.00002 (0.4798
  here against 0.4898, a gap of 0.01002). The cause is not found.
- **The baseline** (`bench/results/2026-09-29-b33b3cb/`): no tool crashed or timed out on any of the
  313 documents; the verifier's defects on inkgrid's readings are spec 11's 74, 114, and 135. The
  first scoring (`2026-09-29-9107c84/`, kept and marked superseded) had turned pages in the wrong
  frame and four access-path files misread (§§ 0, 3.2); the run was repeated in full after both fixes.
  Of its structure and olmOCR numbers, none moved; Soric et al.'s F1s rose by 0.01 to 0.03 for every
  tool, and one finding fell away (inkgrid's practice region precision over pdfplumber's).
- **olmOCR-bench's scorer** (0.4.27) imports numpy without declaring it (pinned beside it), and its
  `--output_failed` skips a candidate with any error. Per-test results come from its own
  `evaluate_candidate`, checked against the score its command line prints.
- **The text-layer stratum** is the 173 PDFs outside `bench/olmocr-no-text-layer.txt`: the 15 on which
  poppler's `pdftotext` 26.01 finds fewer than 100 non-whitespace characters (12 find none), 84 tests,
  as first measured.
- **Binding's ceiling:** the ICDAR ground truth read as a tool binds 86.8% of the 5,603 checkable
  paths and leaf-binds 92.5%. A label outside the value's row and column (a caption, a note) never
  binds.

---

## 1 · Datasets

| Dataset | Documents | Scored as | Ground truth |
|---|---|---|---|
| ICDAR-2013 competition | 67 PDFs; the 67 structure files that have their own PDF (156 tables, as Soric et al.) | structure (DAR), regions, Soric et al.'s four F1s | the competition's `-str`/`-reg`; Soric et al.'s corrected HTML |
| ICDAR-2013 practice | 58 PDFs | structure (DAR), regions, binding | `-str`/`-reg`; `-fnc` access paths |
| olmOCR-bench tables | 188 PDFs (strata: 173 with a text layer, 15 without) | the 1,020 table tests | the tests (ODC-BY-1.0; cite arXiv 2502.18443) |

Every file is fetched by `bench/inkgrid_bench/fetch.py` from `sources.toml`, verified by SHA-256, and never
committed.

## 2 · Tools

| Tool | Version | Tables from |
|---|---|---|
| inkgrid | this commit (reading as of M4, `11871a7`, and M5a's fix for a crash on a Camelot table with no cells, `4a6a751`) | `inkgrid.read(pdf)`: every `Table` block |
| pdfplumber | 0.11.10 | `page.find_tables()` with its defaults |
| PyMuPDF | 1.28.2 | `page.find_tables()` with its defaults |
| Camelot | 2.0.0 | `camelot.read_pdf(pages="all", flavor="lattice")` with its defaults |

Each runs in its own isolated, pinned environment (`uv run --isolated --with ...`), one document at a
time, with a timeout of 300 s per document. *Added 2026-10-01:* spec 15 adds the heavy competitors
(Docling, by default and on an image-only copy, marker, and unstructured `hi_res` with Tesseract) and
the text-layer ablation (`inkgrid-ocr`), the heavy ones batched with deadlines of 120 s a page; these
four tools are unchanged. A timeout or an exception is recorded as that document's
crash and scores as no tables. Soric et al.'s released predictions for Camelot, PyMuPDF, pdfplumber,
and Docling (their versions) are also scored, as a reproduction row.

## 3 · Outputs

### 3.1 The normalized table

Every adapter writes, per document, the tables it finds: the page (1-based), the box in PDF points with
the origin at the page box's top-left corner, and the cells, each an anchor (row, column), a span (rows,
columns), its text, and whether the tool marks it a header. Spans come from the tool where it states them
(inkgrid, Camelot's edges); for pdfplumber and PyMuPDF, a cell spans the grid lines its box covers, the
grid lines being every distinct cell edge of the table. *Amended 2026-09-28, before any tool was scored:* a
span stops before another cell's anchor. pdfplumber and PyMuPDF return boxes that contain another
cell's box (on 32 and 21 of the 313 documents); such a cell's rows end at the first later row holding
another anchor within its columns, then its columns at the first later column holding another anchor
within those rows. Any other overlap is the adapter's crash. A header flag comes from inkgrid's header rows
and PyMuPDF's header; the others mark none.

### 3.2 What each scorer reads

- **ICDAR structure and regions:** `-str.xml` and `-reg.xml` in the competition's schema (one region
  per table, page 1-based, boxes in PDF points with the origin at the bottom left, cells with their
  start and end rows and columns and their content). *Amended 2026-09-29, after the first scoring:*
  a page turned by `/Rotate` goes in the frame it displays in, as the ground truth measures it
  (practice eu-015's cells reach x = 745 on a page 595 points wide); the first scoring used the
  unrotated frame on the five turned pages (competition eu-015, practice eu-014, eu-015, eu-018).
- **Soric et al.:** their predictions file: per page image (`<doc>_<page index>.jpg`), the table boxes
  in image pixels and one HTML table per box. *Amended 2026-09-29:* the image shows the page as it
  displays, 1,000 pixels tall, so a box is turned into the displayed frame and scaled by 1,000 / the
  displayed height (not the longer side: us-015 page 4 and us-033 page 1 are wider than tall and
  their images 1,000 pixels tall).
- **olmOCR-bench:** one `.md` per page, `<stem>_pg1_repeat1.md`, holding every table as HTML:
  `<table>`, `<tr>`, `<td>` with `rowspan` and `colspan`, and the tool's header rows in `<thead>` as
  `<th>`. HTML keeps spans, and for every tool the same writer. inkgrid's prose is omitted, so only
  tables are compared.

## 4 · Metrics

### 4.1 ICDAR-2013 structure (DAR) and regions

The competition's jar scores each document's `-str.xml` against its ground truth with its default
normalization, and prints per ground-truth table its relation counts: in the ground truth, detected,
and correct. A document's precision is its correct over its detected relations, and its recall its
correct over its ground-truth relations, summed over its tables. **The headline** is the mean of the
documents' precisions and recalls, and their harmonic mean (the competition's convention). **Pooled**
precision and recall, over all relations, are reported beside it. Regions come from the jar's `-reg`
mode, reported the same way.

### 4.2 Soric et al.'s protocol

Their evaluator at v1.0.0, on their ground truth, in the environment of § 0: tables matched per page by
the Hungarian method on box IoU, a match counting at IoU ≥ 0.5; F1-bbox; and F1-GriTS-Top, F1-GriTS-Con
and F1-TEDS, each 2 × (the sum of the score over matched tables) / (predicted tables + ground-truth
tables).

### 4.3 olmOCR-bench

The official scorer (`olmocr` 0.4.27, `python -m olmocr.bench.benchmark --skip_baseline`) on the table
tests: the pass rate over all 1,020, over the 308 heading tests, and over the 712 neighbour tests, and
each over the 173 PDFs with a text layer.

### 4.4 Binding (the practice set)

A tool's table is **matched** to a ground-truth table when it is the tool's table on the same page with
the largest intersection with the ground-truth region; a path of an unmatched table is not bound.
Texts compare after NFKC, casefolding, and removing all whitespace. For a path of value `v` and
dimensions `D1 … Dk`, each a list of labels:

- the **value cells** are the matched table's cells whose text is `v`;
- a cell is **aligned** with a value cell when it lies entirely above it in a column the value cell
  covers, or entirely left of it in a row it covers;
- a dimension `D = (l1 … lm)` is **leaf-bound** when a cell aligned with the value cell holds `lm`, and
  **bound** when, in addition, each of `l1 … lm-1` is held by a cell aligned with that leaf cell or with
  a cell holding a later label of `D`. *Clarified 2026-09-29:* "a cell holding a later label" is the
  cell already bound for that label on the leaf's chain, not any cell with its text (otherwise a
  `Gross sample *` column label binds a value under `Net sample **` through the other column's
  `Number`).

A path is **bound** (strict) when every dimension is bound, and **leaf-bound** when every dimension is
leaf-bound, for some value cell. **Binding accuracy** (strict, leaf) is the share of the 5,053 (5,603
read correctly, § 0)
evaluable paths bound; **value recall** is the share with a value cell. The metric needs no header flag
from the tool: values filed under the wrong row or column fail it whichever way the tool labels headers.

### 4.5 Every dataset

Seconds per page (wall clock, the tool's environment already built), crashes and timeouts, and, for
inkgrid, the verifier's defects by class (spec 11 § 5).

## 5 · Statistics

- 95% percentile intervals from a bootstrap of 10,000 resamples of **documents** with replacement,
  seed 20260928; each resample recomputes the metric from its documents' numerators and denominators.
- **Paired differences:** inkgrid minus each tool, on the same resampled documents. A difference is
  stated as a finding only when its interval excludes 0.
- One row per dataset and tool; nothing is pooled across datasets.

## 6 · Cases

| Case | Input | Expected |
|---|---|---|
| NT1 | a 2 × 2 table with a cell spanning both columns of row 0, through the normalized JSON | round-trips; the grid tiles |
| NT2 | pdfplumber-style cells with `None` for a covered position and boxes on 3 x-edges and 3 y-edges | the spans the boxes cover |
| NT3 | a box covering rows 1-2 of three columns, with another box anchored in row 2 inside it (amended) | the outer cell keeps row 1; the grid tiles |
| RD1 | NT1's table as ICDAR `-str.xml` | the jar scores it against itself 1.0 |
| RD2 | NT1's table as HTML | one `<table>`, `colspan="2"` on the spanning cell, header rows in `<thead>` |
| RD3 | a box on a 595 × 842 page, to Soric et al.'s pixels | × 1000 / 842 |
| SC1 | the jar's output for eu-001 against itself | per-table counts parsed; P = R = 1 |
| SC2 | two documents, one with no detected table | its precision undefined and left out of the mean; its recall 0 |
| BD1 | a path `Country, AT | Gross sample *, Number | 848` over a grid with `Country` above `AT` and `Gross sample *` spanning `Number` above `848` | bound, leaf-bound |
| BD2 | the same grid with `848` moved to the next row | neither |
| BD3 | the grid with the `Country` cell removed | leaf-bound, not bound |
| BD4 | a path whose value appears twice, once aligned | bound |
| BS1 | the bootstrap of a constant metric | the interval is the constant |
| BS2 | paired differences of identical per-document results | 0 with a zero-width interval |
| BS3 | the same seed twice | identical intervals |

## 7 · Acceptance

- [x] Every case above has a test named `test_<CaseId>_<slug>`, and it failed before its code.
- [x] The run completes on the three datasets for the four tools; results with intervals are committed
      under `bench/results/<date>-<commit>/`, with `bench/results/latest.md`. A run labelled
      `--label tuned` goes to `<date>-<commit>-tuned/` (spec 14 § 9; the first is
      `2026-09-30-7e607d5-tuned/`, after M5c).
- [ ] Soric et al.'s released predictions reproduce within 0.01 of their published F1s here. *Not
      met:* 15 of 16 do; PyMuPDF's F1-TEDS misses by 0.00002 (§ 0).
- [x] README states only what the intervals support, with the baseline labelled as such.
