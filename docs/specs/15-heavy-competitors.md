# 15 · The heavy competitors and the text-layer ablation (M5d-1)

**Implements:** `00-design.md` § 11.2's CPU competitors that spec 12 left out (Docling by default and
with forced OCR, marker on the text layer only, and unstructured `hi_res` with Tesseract) and its
ablation (inkgrid's gridders fed Tesseract's words against its own), on spec 12's three datasets and
metrics. It amends `12-benchmark.md` § 2 (tools) and § 7 (the run), and adds rows to every report.
**Everything in §§ 1–5 is fixed on 2026-10-01, before any of these tools is scored.** The only earlier
runs of them were the probes of § 0, which scored nothing.
**Modules:**
- `bench/sources.toml`: the new tools, their environment, and Tesseract, pinned;
- `bench/inkgrid_bench/html_tables.py` (new, pure): an HTML table to normalized cells (§ 2.1);
- `bench/inkgrid_bench/adapters/{docling_tables,marker_tables,unstructured_tables,inkgrid_ocr}.py`;
- `bench/inkgrid_bench/adapters/_cli.py`: the batch mode (§ 3); `bench/inkgrid_bench/run.py`: the batch
  runner and the tools; `bench/inkgrid_bench/report.py`: the new rows.

**Not in M5d-1:** plain Tesseract (it finds no tables, so it is scored only by cell character error
rate, which needs the glyph-verified sample of M5d-2); FinTabNet.c (its source needs the user's
decision); the held-out fee set (M5d-2, hand-verified); GPU or paid services (none here).

---

## 0 · What was measured first (L19)

Probes on 2026-10-01, on competition eu-001 (3 pages), practice us-008 (2 pages), and olmOCR
`66aa22ac…_pg6` (1 page), CPU only (16 threads, 22 GB), each tool in its own environment
(`uv run --isolated`, Python 3.12, PyTorch from its CPU index):

| Tool | Version | First document (models loading) | Then | Peak memory | Tables as |
|---|---|---|---|---|---|
| Docling | 2.131.0 (2.132.0 was released that day) | 50 s/page (first download), 21.5 s/page | 11 to 14 s/page | 3.0 GB | cells with anchors, spans, boxes, and column-header flags |
| marker | 2.0.0, `--disable_ocr` | 31.5 s for 3 pages, models included | | | HTML (`<th>`, spans) and the table's box, no cell boxes |
| unstructured | 0.27.10, `hi_res`, `infer_table_structure` | 34 s/page | 7 s/page | 2.0 GB | HTML and the table's box in pixel space |
| Tesseract | 5.5.3 (conda-forge `h7618cdf_0`) | | | | words with boxes (TSV) |

- **Docling's defaults** read the text layer and OCR only bitmap regions (`OcrAutoOptions`, which
  picks RapidOCR 3.9.2), with TableFormer `accurate` and cell matching. Forced OCR is the same pipeline
  with `force_full_page_ocr=True`. Starting a process costs 5 s; loading its models costs about as
  much as a page, once per process.
- **marker** found all 7 of eu-001's tables from the text layer, merging the two header rows of each
  into one cell (`THRESHOLD FOR RELEASES to air to water to land kg/year …`).
- **unstructured** OCRs table cells with Tesseract even on a text-layer PDF: eu-001's cells read
  `C—“*‘“‘“*S*STSC“‘<‘ia‘CCDSCT` and `kg ear` where the page prints `kg/year`.
- **Tesseract** has no user-space package on PyPI and no system package here (no sudo). conda-forge's
  build installs into a prefix under the cache through micromamba 2.3.2 (a static binary, SHA-256
  `5512233c…`), 500 MB with 125 languages. poppler's `pdftoppm`, which unstructured renders with, is
  on the system.
- **Page counts:** competition 67 documents, 238 pages (median 3, longest 15); practice 58, 170 (median
  3, longest 11); olmOCR 188, one page each. At up to 35 s a page, spec 12's 300 s per document
  would time out a long document that would otherwise finish.

---

## 1 · Tools

| Tool | Version | Configuration |
|---|---|---|
| `docling` | 2.131.0 | `DocumentConverter()` with its defaults: every `TableItem` |
| `docling-ocr` | 2.131.0 | the same, with `OcrAutoOptions(force_full_page_ocr=True)` |
| `marker` | marker-pdf 2.0.0 | `PdfConverter` with `disable_ocr`, `disable_image_extraction`, JSON output: every `Table` block |
| `unstructured` | 0.27.10, `[pdf]` | `partition_pdf(strategy="hi_res", infer_table_structure=True)`, Tesseract 5.5.3 for OCR: every `Table` element |
| `inkgrid-ocr` | this commit | inkgrid with each page's words replaced by Tesseract's (§ 4) |

- Each runs in its own isolated environment on Python 3.12 with PyTorch from
  `https://download.pytorch.org/whl/cpu` (`--index-strategy unsafe-best-match`); `inkgrid-ocr` runs in
  inkgrid's own. Model weights are each tool's own defaults at its pinned version, downloaded on first
  use into the user's cache; the run records each tool's resolved package versions.
- Tesseract is `tesseract=5.5.3` from conda-forge, created by micromamba 2.3.2 into
  `~/.cache/inkgrid-bench/tools/tesseract/`, with English (`eng`) as its language for every document,
  its default: the datasets' table text is English but for a handful of olmOCR pages.
- Threads are each library's default; nothing else runs during the run.

## 2 · Outputs

Every adapter writes spec 12 § 3.1's normalized tables: page, box in PDF points from the page box's
top-left corner, and cells with anchors, spans, text, and the header flag.

### 2.1 HTML tables (`html_tables.py`, pure)

`cells_from_html(html) -> list[NCell]`: the rows of `<table>` (in `<thead>`, `<tbody>`, or neither) in
order; each `<td>` or `<th>` at the first free column of its row, spanning `rowspan` × `colspan`
(missing, non-numeric, or below 1 means 1); its text is its descendants' text with tags removed,
entities decoded, and whitespace runs collapsed to one space; a `<th>` is a header cell. A cell
reaching past the rows the table has is clipped to them, and a span that would cover a position an
earlier cell holds stops before it (HTML lets them overlap; a normalized table may not). A table with
no cell is none.

### 2.2 Per tool

- **Docling:** each cell's `start_row_offset_idx`, `start_col_offset_idx`, `row_span`, `col_span`,
  `text`, and `column_header`; the table's box from its first provenance, whose origin is the page's
  bottom-left, turned to the top-left by the page's height. A table on two pages is its first page's.
- **marker:** each `Table` block's `html` through § 2.1, its `bbox` (top-left origin, points), and its
  page from the block's id (`/page/N/Table/M`, 0-based).
- **unstructured:** each `Table` element's `text_as_html` through § 2.1; its box is the extent of its
  coordinate points scaled from their pixel space to the page's size. An element without
  `text_as_html` (its structure not inferred) has no cells.
- A table with no cell after normalization is dropped, as spec 12's adapters do.
- **Turned pages.** All three report a `/Rotate` page as it displays (measured on olmOCR
  `58feed…_pg42`, `/Rotate 90`: each gave a 792 × 612 page and the table where inkgrid's box displays).
  Each box's corners are turned back by the page's frame (`NPage.from_shown`), so every table is placed
  in the unrotated page as spec 12 § 3.1 says. The runner computes the frames, as it already does for
  every reading, and hands them to the adapter, so no tool's environment needs pypdfium2.
- The input each conversion takes is the tool's own export (Docling's `export_to_dict()`, marker's
  JSON output, unstructured's `Element.to_dict()`), parsed field by field: a missing or mistyped field
  is the document's error, never a guess.

## 3 · Running them (`_cli.py`, `run.py`)

- **Batch mode.** A heavy tool's adapter reads a manifest of documents (each with its output path and
  its pages' frames) in one process, one at a time:
  its models load once, before the first document's clock starts. After each document it writes that
  document's output and prints `done N`; a document whose read raises gets the error as its output and
  the batch goes on.
- **Deadlines.** A document's deadline is 120 s per page, and never less than spec 12's 300 s; the
  first document of each process also gets 600 s for the process to start and load its models. A
  document past its deadline is killed with its process group, recorded as a timeout, and scored as no
  tables; the batch restarts after it. A process that dies records its current document as a crash.
- Seconds per page, crashes, and timeouts are reported as for spec 12's tools.
- spec 12's four tools keep their one-process-per-document mode, unchanged.

## 4 · The ablation (`inkgrid_ocr.py`)

- Each page is rendered at 300 DPI (pypdfium2, as the verifier renders) and read by Tesseract (`tsv`,
  page segmentation mode 3, its default).
- Each Tesseract word (level 5, with a non-blank text) becomes a `Word`: its box scaled from pixels to
  points, its text stripped of whitespace and control characters (a word left empty is dropped), its
  size the box's height, horizontal, not bold, not a superscript, font `tesseract`. Ids run from 0 over
  the document in page and reading order.
- The page keeps its own rules, fills, size, and rotation; its text layer is `full` with words, else
  `none`, and its character counts are zero. Camelot reads the ruled pages exactly as for inkgrid, and
  the pipeline builds the document unchanged.
- Its tables are normalized as inkgrid's are. The paired difference `inkgrid − inkgrid-ocr` is the
  text layer's effect on inkgrid's own gridders.

## 5 · Reporting

- Every dataset's tables gain the five tools; inkgrid's paired differences cover each.
- The report's first paragraph names the run's label and says which tools ran with OCR.
- The README states only what the intervals support, labelled as tuned for inkgrid (DR-0023).

---

## 6 · Cases

| Case | Input | Expected |
|---|---|---|
| HT1 | `<table><thead><tr><th colspan=2>Fees</th></tr></thead><tbody><tr><td rowspan=2>A</td><td>1</td></tr><tr><td>2</td></tr></tbody></table>` | `Fees` (0,0) 1×2 header; `A` (1,0) 2×1; `1` (1,1); `2` (2,1) |
| HT2 | entities, nested `<b>`, `<br>`, runs of spaces; `rowspan="x"`, `colspan="0"` | `a & b`, one space; spans 1 |
| HT3 | a cell spanning past the last row; a `colspan` running into a `rowspan` from above; an empty table; no `<table>` | clipped; stopped before it; none; none |
| HT4 | property: any table of `<td>` and `<th>` with spans from 0 to 4 | its cells never cover a position twice |
| DC1 | a Docling table dict: a bottom-left box on a 792 pt page, a spanning column header | the top-left box; anchors, spans, the header flag |
| DC2 | the same table on a `/Rotate 90` page, displayed 792 × 612 | the box turned back to the unrotated page |
| DC3 | a cell without `row_span`; a box whose origin is neither corner | the document's error |
| MK1 | a marker JSON page with two `Table` blocks and other blocks | two tables on the id's page, boxes as given |
| MK2 | a marker `Table` on a `/Rotate 90` page | the box turned back |
| US1 | an unstructured `Table` element in a pixel space twice a 595 × 842 page's size | the box scaled to points |
| US2 | an unstructured `Table` in a pixel space twice the size of a `/Rotate 90` page as it displays | scaled, then turned back |
| BM1 | a batch of three documents: the second raises | three outputs, the second its error |
| BM2 | a batch whose second document hangs past its deadline; one whose process dies on its second | killed; a timeout for it, or its crash; the third read by a new process; the first never read again |
| BM3 | deadlines: 1 page, 3 pages, 15 pages | 300 s, 360 s, 1,800 s |
| AB1 | Tesseract TSV rows: a word, a blank, a line row, a word with a control character | two words, in points, ids 0 and 1 |
| AB2 | the ablation on `ruled_grid` with a fake Tesseract (the fixture's own words as TSV) | the same table as inkgrid reads |
| RP1 | a report with the new tools | their rows, and inkgrid's paired difference with each |

## 7 · Acceptance

- [ ] Every case above has a test named `test_<CaseId>_<slug>`, and it failed before its code.
- [ ] The run completes on the three datasets for every tool; crashes and timeouts are listed; the
      results are committed beside the earlier runs.
- [ ] README shows the competitors and the ablation, and claims only what the intervals support.
