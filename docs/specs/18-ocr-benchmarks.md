# 18 · OCR benchmarks on born-digital text and tables (M7a)

**Implements:** the owner's decision of 2026-10-08: compare inkgrid with OCR and document-parsing tools
on recognised OCR benchmarks, but only on what a text-layer reader can fairly be tested on, namely
born-digital PDF pages with a text layer and the benchmarks' text and table tests. Scans, photos,
handwriting, charts and math formulas are left out. The benchmarks are olmOCR-bench and OmniDocBench,
plus ParseBench and DP-Bench. This spec pre-registers the datasets, the census that decides which
pages count, the tools, their output, the scorers, the statistics and how improvements are measured.
It records inkgrid's untuned baseline (DR-0023); any fix made after looking at these benchmarks' failures
is labelled tuned and is measured on a held-out half (§ 7).
**Modules:** `bench/inkgrid_bench/census.py` (new, pure core plus a PyMuPDF shell; § 2),
`bench/inkgrid_bench/page_markdown.py` (new, pure; § 3), the adapters in `bench/inkgrid_bench/adapters/`
(§ 3), `bench/inkgrid_bench/scores/{olmocr_pages,omnidocbench,parsebench,dpbench}.py` (new; § 4),
`bench/inkgrid_bench/ocr_run.py` (new; `run.py --datasets ocr`; §§ 5, 6), `bench/sources.toml` and the
manifests beside it.

---

## 0 · What was measured first

On 2026-10-08 a research sweep vetted 15 document-parsing benchmarks from their primary sources. The four
chosen here are the ones whose inputs include born-digital PDFs and whose licences permit evaluation:

| Benchmark | Revision | Licence | Inputs | Scorer |
|---|---|---|---|---|
| olmOCR-bench v1 (AI2) | HF `allenai/olmOCR-bench` @ `54a96a6` | ODC-BY-1.0 | 1,403 one-page PDFs | `olmocr[bench]==0.4.27` (Apache-2.0), already pinned |
| OmniDocBench v1.0 (OpenDataLab) | HF `opendatalab/OmniDocBench` branch `v1_0` @ `f5f559b`; evaluation code `opendatalab/OmniDocBench` branch `v1_0` @ `337cc26` | data: research use; code: Apache-2.0 | 981 page slices of the original PDFs (`ori_pdfs/`), metadata intact | `pdf_validation.py --config` end-to-end |
| ParseBench (LlamaIndex, 2026) | HF `llamaindex/ParseBench` @ `2805a1d`; scorer `parse-bench==1.0.4` (repo `cbd57f2`) | Apache-2.0 | 503 one-page table PDFs, 506 text documents | `parse-bench` evaluation |
| DP-Bench (Upstage) | HF `upstage/dp-bench` @ `24702c6`; Markdown truth and scorer from `opendataloader-project/opendataloader-bench` @ `7af1d8f` | MIT; Apache-2.0 | 200 one-page PDFs | opendataloader-bench `src/evaluator.py` |

- **OmniDocBench's current release is page images only.** Its `v1_0` branch alone carries `ori_pdfs/`,
  "PDF pages extracted directly from the original PDFs", and the evaluation code keeps a matching
  `v1_0` branch. Its card warns that 368 pages had areas masked in the evaluated images (special graphics
  in headers and footers) and 22 had unparseable areas, listed in `with_mask.json`, which the original
  PDFs do not mask (§ 2).
- **Not chosen this round** (owner, 2026-10-08): READoc, FinTabNet (whose official IBM copy does still
  exist, under CDLA-Permissive-1.0, contrary to DR-0024's premise), Table-BRGM. ParseBench's table track
  includes 19 pages that originate in FinTabNet; they are part of ParseBench's own Apache-2.0 release and
  are kept.
- **Published numbers are context, never a comparison.** Leaderboards run each tool at another version,
  on other hardware, on all pages including scans and math. A published figure is quoted only with its
  source, conditions and date, and never set beside this run's numbers as if paired.

## 1 · Datasets, what is fetched, what is scored

Everything is fetched by pinned revision into `~/.cache/inkgrid-bench/` and checked against SHA-256
manifests committed beside `sources.toml`; nothing downloaded is committed or executed. A benchmark
on Hugging Face has a listing (`bench/ocr/<benchmark>.sha256`) of every file the run uses, each hash
checked against the Hub's own at the pinned revision when it was written (2,748 files, none
differing); DP-Bench is opendataloader-bench's repository, cloned at its pinned commit, and its PDFs
are pinned by the census.

| Benchmark | Fetched | Scored (before the census) |
|---|---|---|
| olmOCR-bench | `bench_data/{headers_footers,multi_column,long_tiny_text}.jsonl` and their PDFs (266, 231, 62), beside the 188 table PDFs already cached | headers_footers (753 absent + 7 baseline tests), multi_column (884 order), tables (1,020 table + 2 baseline), long_tiny_text (442 present); not arxiv_math, old_scans, old_scans_math |
| OmniDocBench v1.0 | `OmniDocBench.json`, `with_mask.json`, `ori_pdfs/*` | text blocks (Edit distance), tables (TEDS, Edit distance), reading order (Edit distance); not display formulas |
| ParseBench | `table.jsonl`, `text_content.jsonl`, `docs/table/*`, `docs/text/*` | the table group (GTRM headline, GriTS-Con, TableRecordMatch); text_content's six text-layer tags (`text_simple`, `text_multicolumns`, `text_multilang`, `text_misc`, `text_dense`, `text_sparse`): Content Faithfulness; not `text_ocr`, `text_handwritting`, charts, layout, formatting |
| DP-Bench | the 200 PDFs, `ground-truth/` and the 14 engines' committed outputs from opendataloader-bench; `reference.json` from Upstage | NID (text in reading order), TEDS (tables), MHS (headings) |

## 2 · The census: which pages count

**Every page of every fetched PDF is classified before any benchmarked tool reads it**, by PyMuPDF's text
trace and image placements (no benchmarked tool is involved), and the classes are committed as
manifests. A page is:

- **`no_text`** when it holds fewer than 50 visible non-whitespace characters (a visible character is one
  drawn with a text render mode other than invisible, 3, and with non-zero opacity);
- **`ocr_layer`** when it is not `no_text` and its invisible characters are at least as many as its
  visible ones (a scan carrying an OCR text layer);
- **`image_backed`** when it is neither and one raster image covers at least 90% of the page's area
  (its text may sit over a scanned page);
- **`born_digital`** otherwise.

A document is born-digital when every page is. **Only born-digital documents are scored.** Each
benchmark's report states how many documents each class holds and lists the excluded ones by class.

**The census, run on 2026-10-08 before any benchmarked tool read a page** (`bench/ocr/census-*.json`):

| Benchmark | Documents | Born-digital | No text | Image-backed | OCR layer | Scored | Dev / test |
|---|---|---|---|---|---|---|---|
| olmOCR-bench | 747 | 603 | 125 | 14 | 5 | headers_footers 231, multi_column 194, tables 162, long_tiny_text 16 | 283 / 320 |
| OmniDocBench v1.0 | 981 | 620 | 264 | 97 | 0 | 393 primary (born-digital, no mask: 190 English, 195 Chinese, 8 mixed); 620 in all | 203 / 190 (primary) |
| ParseBench | 1,009 | 827 | 159 | 22 | 1 | tables 495; text 324 (simple 158, multi-column 87, multilingual 38, misc 23, dense 12, sparse 6) | 393 / 426 |
| DP-Bench | 200 | 196 | 1 | 3 | 0 | 196 | 94 / 102 |

**Further strata, fixed here:**
- OmniDocBench: the primary stratum is born-digital pages **not** listed in `with_mask.json` (where the
  original PDF equals the evaluated page); all born-digital pages are reported as a second stratum. Text
  results are reported for English pages and for simplified Chinese pages separately, as OmniDocBench
  v1.0 reports them by its `language` attribute; pages in mixed English and Chinese count in neither
  language's text, and in the tables and reading order.
- ParseBench: `text_multilang` is reported apart from the other five text tags.
- olmOCR-bench: long_tiny_text is reported apart; it is not in the headline.

**The dev / test split.** Each benchmark's born-digital documents are split once by
`sha256("inkgrid-m7:" + benchmark + ":" + document id)`: a first hex digit 0–7 puts the document in
**dev**, 8–f in **test**. Only dev documents' failures may be looked at when designing a fix (§ 7).

## 3 · The tools and what they output

| Tool | Version (pin) | Reads | Tables written as |
|---|---|---|---|
| inkgrid | the commit measured | text layer | `Table.to_html()` (spans, `<thead>`) |
| Docling | 2.131.0 (spec 15's environment) | text layer + layout/table models; OCR where a page has no text | `TableItem.export_to_html()` |
| Docling, image-only | as above, on an image-only copy | OCR on every page | as above |
| marker | 2.0.0, OCR off | text layer + layout models | HTML (`html_tables_in_markdown`) |
| unstructured | 0.27.10 `hi_res`, Tesseract 5.5.3 | layout model + OCR | `text_as_html` |
| inkgrid on Tesseract's words | the commit measured | OCR | `Table.to_html()` |
| pymupdf4llm | 1.28.2, OCR off (`use_ocr=False`) | text layer (with PyMuPDF Layout) | HTML (`table_output="html"`) |
| MarkItDown | 0.1.8 (`[pdf]`) | text layer (pdfminer) | its own output, converted as below |
| LiteParse | 2.15.1, no OCR | text layer (PDFium) | its own output, converted as below |

- **One Markdown file per document**, the tool's whole reading of it, in its reading order. A crash or
  timeout writes an empty file and is listed; it scores as the scorer scores empty output.
- **Furniture:** what a tool recognises as page headers, footers and page numbers is left out:
  inkgrid, Docling and marker do so by default; pymupdf4llm labels them but keeps them by default, so
  it is called with its own `header=False, footer=False`; unstructured's elements labelled `Header`,
  `Footer` or `PageNumber` are left out, and so are its `Image` elements (the text inside a picture,
  which Docling's Markdown leaves out too); MarkItDown and LiteParse recognise none.
- **Tables:** where a scorer reads only HTML tables (ParseBench), a GFM pipe table in any tool's output is
  converted by one shared converter (`page_markdown.pipe_to_html`: first row `<thead>`/`<th>`, no spans),
  applied to every tool alike. olmOCR-bench, OmniDocBench and opendataloader-bench read Markdown and HTML
  tables themselves and get each tool's output unchanged.
- The heavy tools run batched (spec 15) with spec 15's deadlines; every tool runs one document at a
  time, niced, from pinned isolated environments (the new ones resolved with `--exclude-newer
  2026-10-08T00:00:00Z`).

## 4 · Scorers and metrics

| Benchmark | Reported | Per-document value | Pooling |
|---|---|---|---|
| olmOCR-bench | pass rate per category (headers_footers, multi_column, tables, long_tiny_text); the automatic baseline tests as their own group; a **born-digital macro** over headers_footers, multi_column and tables | tests passed, tests | pooled over tests, per category |
| OmniDocBench | text Edit distance (lower is better), table TEDS and table Edit distance, reading-order Edit distance | the scorer's per-page value (a page's TEDS is the mean over its tables) | mean over pages, as the scorer's page averages (`ALL_page_avg`; `page.TEDS.ALL`), which each run's pages must reproduce |
| ParseBench | tables: GTRM (headline), GriTS-Con and TableRecordMatch; text: Content Faithfulness, with its text-correctness and order parts | the scorer's per-document value | mean over documents |
| DP-Bench | NID, TEDS (documents with tables), MHS (documents with headings) | the scorer's per-document value | mean over documents |

- Each scorer runs unmodified at its pin, in its own environment, on CPU. A driver writes the
  predictions where the scorer expects them, restricts it to the scored documents where the scorer
  allows (otherwise filters its per-document output), and reads back per-document values. ParseBench's
  run goes through a registered provider that returns the saved Markdown.
- **Each pinned scorer was checked against its source before use** (2026-10-08): re-scoring
  opendataloader-bench's committed Docling outputs gives every one of its committed metrics exactly;
  OmniDocBench's evaluation of its own demo predictions gives its committed demo results exactly;
  ParseBench's built-in PyMuPDF text pipeline gives Content Faithfulness 68.19 where the leaderboard
  lists 68.28 (its PyMuPDF and parse-bench versions are not stated); and the saved-Markdown provider,
  fed that pipeline's own outputs, gives its per-document scores exactly (506 of 506).
- **Every scorer's output is kept** beside its inputs in the run's directory, and a scorer gets four
  hours a tool and benchmark. OmniDocBench falls back to a simpler text match when a page's match
  passes 30 s, so a page's match can depend on the machine's load: the pages it prints as falling
  back are marked and listed in the report, and a page it prints as unpredicted is refused.
- **Never an "Overall".** A benchmark's official overall averages parts excluded here (scans, math,
  charts); no number in this run is called one.
- **Speed:** seconds per page, warm, as spec 15 defines it.

## 5 · Statistics and the report

- Every number has a 95% interval from 10,000 clustered resamples of documents (seed 20260928, as spec
  12); inkgrid's paired difference from each tool has its own interval, and only a difference whose
  interval excludes 0 is a finding.
- The report (`bench/results/<date>-<commit>-ocr/report.md`) states in its title and first paragraph
  that only born-digital pages and text and table tests are scored, whether inkgrid's numbers are the
  baseline or tuned, and each benchmark's census counts. Sections per benchmark; dev and test halves are
  reported apart once a tuned run exists.

## 6 · The run

`run.py --datasets ocr [stages]` reads every tool on every scored document, scores, and reports, one
document at a time, niced, in resumable pieces (stages `prepare`, `read`, `score`, `report`). It
refuses to start unless the census manifests and the data hashes match the pinned ones, and a run
labelled baseline refuses an `src/inkgrid` other than v0.1.0's. `prepare` builds every tool's and
scorer's environment, so the read stage runs offline (`UV_OFFLINE=1`): a tool that cannot start fails
there, never as a document's reading. Each reading is written whole or not at all. With
`--readings-from COMMIT`, the read stage first carries over the readings of the run at that commit
for every tool this commit would read alike: none if the reading code (the adapters and the modules
they use, `run.py` included) or a tool's pin changed, all but inkgrid and inkgrid on Tesseract's words
if `src/inkgrid` or `uv.lock` changed, every tool otherwise; the report names the tools carried
over. A run's results go to `bench/results/<date>-<commit>-ocr/`; the
baseline is labelled `baseline`, later runs `tuned` (`--label tuned`).

## 7 · Improvements (M7b)

1. The baseline run (§ 6) is recorded first, with every tool.
2. Only inkgrid's failures on **dev** documents are examined. Each fix is specified (spec 19), tested
   first, and reviewed. No fix may loosen a check, drop text, or invent any.
3. After the fixes, inkgrid (and inkgrid on Tesseract's words) are run again, labelled tuned; dev and
   test halves are reported apart, and the **test half** is the measure of whether the fixes carry.
4. Before any release: the fixture suite, the 42 look-back fee schedules (every block and defect diffed
   against the last run), the ICDAR-2013 and olmOCR table sets, and the held-out fee set are run again;
   a change in any is explained.

## 8 · Cases

| Case | Input | Expected |
|---|---|---|
| DS1 | each benchmark's files, laid out as fetched (test files or truth listing their PDFs) | every document once, with its id (the benchmark's own) and group (olmOCR category, OmniDocBench language, ParseBench track or text tag); a referenced PDF that is missing is refused |
| DS2 | spec 12's olmOCR-bench folder after this spec's categories are fetched beside its table tests | spec 12 scores in a view of it holding only `table_tests.jsonl` and `pdfs/tables/`, so olmOCR's command line and spec 12's driver see the table tests and the 188 table PDFs and nothing else |
| SL1 | documents of every class and group, with their census entries | the scored ones are the born-digital documents in a scored group (olmOCR's four categories, every OmniDocBench language, ParseBench's table track and six text tags, DP-Bench's pages); a document the census never classified, or a group this spec does not name, is refused |
| CS1 | page statistics at each threshold's edge: 49 and 50 visible characters; invisible equal to visible; one image covering 89% and 90% | `no_text`; `born_digital`; `ocr_layer`; `born_digital`; `image_backed` |
| CS2 | a document with one `image_backed` page among born-digital ones | not born-digital |
| CS3 | a PDF built with visible text, invisible text, and a page-size image | the census shell's counts match what was drawn |
| CS4 | a benchmark's documents and their PDFs | a manifest holding, per document id, the PDF's SHA-256, its page classes, its class and its half, and the benchmark's pinned revision |
| SP1 | any document ids, in any order (property) | the same split every time; dev exactly when the first hex digit is 0–7 |
| MD1 | GFM pipe tables (header row, escaped pipes, ragged rows), and text around them | each table becomes HTML with the first row in `<thead>`, every cell's text kept, the text around it unchanged |
| MD2 | an inkgrid `Document` with a heading, paragraphs, a table and furniture; one with a table that repeats another's pipe table, and one whose pipe table begins another's | its Markdown with each table as its own `Table.to_html()`, in its own place, and no furniture |
| AD0 | a reading with Markdown; a reading written before readings had Markdown | written and read back unchanged; the older one reads with empty Markdown |
| AD1 | inkgrid's adapter on a page with paragraphs and a table | its tables as before, and its Markdown equal to `page_markdown.inkgrid_markdown` of the same reading |
| AD2 | unstructured elements: Title, NarrativeText, ListItem, Table with `text_as_html`, Header, Footer, PageNumber, Image | Markdown in element order: `#` title, paragraph, `- ` item, the table's HTML; no header, footer, page number or image |
| AD3 | *heavy:* each text-layer converter (pymupdf4llm, MarkItDown, LiteParse) on that page, in its pinned environment | Markdown holding both paragraphs |
| AD4 | *heavy:* Docling and marker on that page, in their pinned environments | their tables as before, and Markdown holding both paragraphs and the table as HTML |
| AD5 | *heavy:* inkgrid on Tesseract's words on that page | Markdown holding both paragraphs as Tesseract reads them, and any table it finds written as HTML |
| AD6 | *heavy:* pymupdf4llm on a five-page document with a running header and page numbers | Markdown holding the body and neither the header nor a page number |
| SC1 | an olmOCR category restricted to born-digital PDFs, a tool missing one PDF's output; a reading holding a lone surrogate | an empty file written for it; per-PDF tests and passes read back; every scorer's file holds U+FFFD for the surrogate |
| SC2 | OmniDocBench's per-page Edit and TEDS files for a subset, and its own averages | per-page values keyed by page, with each page's language; their means reproduce the scorer's page averages (overall, and English and simplified Chinese text), and a difference is refused |
| SC3 | a ParseBench run through the saved-Markdown provider; documents ParseBench could not evaluate | the provider returns exactly the saved Markdown; per-document values read back; a document ParseBench could not evaluate counts as ParseBench's own aggregates count it (an error of its evaluation harness leaves it out, any other failure scores 0), and the report lists it |
| SC4 | an opendataloader-bench `evaluation.json` | per-document NID, TEDS and MHS, missing where the document has no table or heading |
| SC5 | *heavy:* inkgrid's pages of two scored documents of each benchmark, scored as the run scores them | each pinned scorer, in its environment, returns values for exactly those documents |
| RP1 | a report of baseline counts; of tuned counts | its title and first paragraph say born-digital text and table tests only, baseline or tuned, and how many fetched documents the census found born-digital and how many are scored; each benchmark's strata and parts as § 2 fixes them; a tuned report's dev and test halves apart; every document left out, by class; the documents a scorer left out, scored 0 on failure, or matched the simple way; no "Overall"; tools covering different documents refused |
| RN1 | a census manifest or data hash that does not match the pin; a census over other documents; a scorer's or a benchmark's clone at another commit or with changed files | the run refuses, naming the file |
| RR1 | the readings of a run at another commit; that commit's reading code, tool pins or `src/inkgrid` changed since | every tool's readings are linked when nothing changed, all but inkgrid's and inkgrid on Tesseract's words when `src/inkgrid` changed, a reading already made here kept; a change to the reading code or a pin is refused; `--readings-from` only with `--datasets ocr`; the report names the tools carried over |
| RD1 | the read stage; prepare | tools read with `UV_OFFLINE=1`, restored after; a half-written reading never stands as one; prepare builds every tool's and scorer's environment and refuses one that does not start |
| RN2 | a run labelled baseline whose `src/inkgrid` differs from v0.1.0's | its read and report stages refuse: the baseline is 0.1.0's reading, and a run after a fix is labelled tuned |

## 9 · Acceptance

- *Heavy* cases need a tool's pinned environment or the pinned Tesseract; they run with
  `pytest -m heavy` before the baseline run, not in CI, and their run is recorded.

- Every case above has a test named `test_<CaseId>_<slug>`, and it failed before its code.
- The census manifests are committed before any benchmarked tool reads a page.
- The baseline run completes for every tool on every benchmark; crashes and timeouts are listed; the
  results are committed; the README states them as measured on born-digital text and tables only, and
  claims only what the intervals support.
