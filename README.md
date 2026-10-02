<h1 align="center">inkgrid</h1>

<p align="center">Exact tables and text from born-digital PDFs, read from the text layer and the drawn rules, and checked by a second PDF engine.</p>

<p align="center">
  <a href="https://github.com/Abdul-Muizz1310/inkgrid/blob/v0.1.0/WHY.md">Why</a> •
  <a href="https://github.com/Abdul-Muizz1310/inkgrid/blob/v0.1.0/docs/ARCHITECTURE.md">Architecture</a> •
  <a href="https://github.com/Abdul-Muizz1310/inkgrid/blob/v0.1.0/docs/DEMO.md">Demo Script</a> •
  <a href="https://github.com/Abdul-Muizz1310/inkgrid/blob/v0.1.0/docs/specs/00-design.md">Design</a>
</p>

<p align="center">
  <a href="https://github.com/Abdul-Muizz1310/inkgrid/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/Abdul-Muizz1310/inkgrid/ci.yml?branch=main&label=ci"></a>
  <a href="https://github.com/Abdul-Muizz1310/inkgrid/blob/v0.1.0/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
</p>

> **Status: alpha, 0.1.0 (milestones M0 to M6 complete).**
> Today inkgrid reads a PDF into a validated `Document`: every word in exactly one block, in reading
> order, with running headers and footers set apart, tables, ruled or not, as explicit cell grids,
> glossaries as definitions, and footnote calls linked to their notes. Tables and sentences that run
> onto the next page are joined. `inkgrid.verify` then grades the document against its PDF with a
> second engine, PDFium. The roadmap is in
> [`docs/specs/00-design.md`](https://github.com/Abdul-Muizz1310/inkgrid/blob/v0.1.0/docs/specs/00-design.md) § 14.

## What it does

inkgrid reads born-digital PDFs, the kind produced by a word processor or a report generator, through
their text layer and their vector drawings. It never recognizes characters from pixels, so it never
misreads one.

When complete, it returns every word of a document in exactly one block (heading, paragraph, list
item, footnote, definition, table, or page furniture), in reading order. Tables come back as explicit
cell grids, with merged cells as spans and headers carried across page breaks, marked as carried.
Links record the relationships the page prints: footnote calls to their notes, and tables that
continue onto the next page.

Shipped so far (M0 to M4):

- **Words rebuilt from characters.** A superscript marker printed tight against a value stays its own
  word (`$0.40` and `2`, never `$0.402`). A font change in the middle of a word keeps it one word.
- **Drawn rules** from the page's vector paths, including cell outlines drawn as rectangles.
- **Nothing degraded silently.** Each of these comes back as a typed finding:
  - image-only pages, and pages MuPDF cannot load or decode;
  - text a clip path or the CropBox hides;
  - glyphs with no Unicode mapping, and Type 3 fonts, whose glyphs are pictures;
  - text in the layer that the page never shows: render modes 3 and 7, or fully transparent text.
    That is the shape of an OCR layer, or of hidden prompt injection.
- **Reading order across columns.** Two prose columns read left column, then right. A gutter alone
  does not make columns, because the narrowest table columns sit as close as a label and its text:
  columns need a gutter that persists over several lines and prose on both sides. Tables and
  hanging-indent lists keep row order.
- **Running headers, footers, and page numbers** found by recurrence across pages and set apart as
  furniture, line by line. A line inside a ruled table is never furniture, and furniture runs from
  the page's edge, so a table's spanning header or stub banner in the page band stays in its table.
- **Typed blocks:** headings with their section numbers and levels, paragraphs, list items, and
  footnotes, with every line-end hyphen join recorded so it can be undone.
- **Ruled tables as cell grids.** Camelot's lattice parser reads the pages whose rules run both ways,
  through its cell edge flags, never its DataFrame. A merged cell is one cell with a span, so a value
  is never copied into the positions it covers. Leading value-free rows become header rows, and
  full-width rows become banner rows. A box around a paragraph, a furniture label, or a frame ruled
  around columns of running text is not a table. Nor is a grid over a table already read (a page
  panel, an open frame), and a page border around a table reads as the table alone. The page's own
  drawn rules, thin grey fills included, split a cell they divide.
  Tables export as GFM Markdown, HTML with `colspan`/`rowspan`, and dense rows that flag every
  repeated value.
- **Unruled tables from whitespace.** Tables set without column rules (SIX, LSE, Euronext) come from
  the whitespace between the value rows' cells, which stays put however a column is aligned. Every row
  votes on where each boundary sits, wrapped lines join their row, a drawn rule ends a row or a cell,
  and two values never share a cell: rows that could only be read by fusing two values stay text,
  with a `table_left_as_text` warning.
- **Charts are not tables.** Bars whose lengths are in one proportion to the numbers they carry, or a
  numeric axis with a tick at every label, keep a chart's labels as text (`chart_left_as_text`),
  in either table reader. A diagonal watermark is no cell's.
- **Glossaries and note lists.** Inside a definitions section, an entry that opens with a term becomes
  a definition block with its `term` and `body`: a quoted term (`“ABBO” means …`), a bold one
  (`Available for Distribution:`), or one set in a column of its own (SIX's glossary). Outside such a
  section only a quoted term with a defining verb counts. A two-column grid of note labels beside prose
  becomes footnotes (`X2 | Connection rebate: …`, where a table prints `EMDI^X2`), and inside a
  section, or under its own `Legend` banner, a grid of terms beside prose becomes definitions.
- **Footnote calls linked to their notes.** Notes are found in every form the measured documents print
  them: small type opening with a number, a number or mark opening its note at the text's own size
  (`^ Contra to …`, `2 Each month …`), a raised number glued to its first word (`1A surcharge`), and
  ruled tables titled `Footnotes`. A note must be called somewhere in the document, so numbered
  clauses are never read as notes. Calls come as superscripts, as parenthesised numbers at body size
  (`Customer (2)(8)(9)`), and as named references (`see footnote 27`). Each call ends resolved to its
  note, unresolved (with a `call_unresolved` warning), or rejected by a named drafting convention:
  `five (5)`, `Section 202(a)(11)`, `except (1)`, and `; (2) if …` are never calls.
- **Tables and sentences across pages.** A table that runs onto the next page without its header
  carries the header as cells that own no words, linked to the part it continues. A reprinted header
  links the parts without carrying. A sentence broken by the page joins into one paragraph with a
  region on each page.
- **Markdown and an HTML inspector.** The inspector draws every block over its rendered page, for
  looking at a reading rather than trusting it, and a verification report's defects over the page.
- **An independent verifier.** `inkgrid verify` re-reads the PDF with PDFium and grades the document
  character by character: nothing lost, invented, or doubled; every cell holding the ink inside it;
  no drawn rule dividing a cell; every value bound to one cell. It exits 1 on any defect. On the 42
  measured fee schedules it accounts for all 1,817,075 characters and reports 8 cells, among them two
  values from two columns read as one word, and a note mark in the column after its word. On
  ICDAR-2013 and olmOCR-bench's table pages it names the ways the two engines read a page
  differently (ligatures, unmappable glyphs, overprinted titles), so what it still reports there is
  inkgrid's own errors: [`docs/specs/11-verify-on-public-corpora.md`](https://github.com/Abdul-Muizz1310/inkgrid/blob/v0.1.0/docs/specs/11-verify-on-public-corpora.md) § 5 lists them.
- **The full output contract,** `inkgrid.document/1`, with its invariants enforced: every word owned
  exactly once, cells that tile their grid exactly, and block text spelled from its own words in
  their order.

### Known limitations

- **Text is judged hidden from the text layer alone.** Text covered by an opaque shape or image,
  white text on a white page, and text too small to read all read as visible. The verifier reads the
  text layer too, so it does not catch them either.
- **Errors the verifier finds on public corpora.** On the 31 ICDAR-2013 and olmOCR-bench documents
  where the verifier found inkgrid's own errors, 25 defects remain of the baseline's 316. One is a
  table title straddling Camelot's header-row edge (practice us-008). The other 24 are places where
  the two engines read the text layer differently and the verifier has no benign class for yet: a
  symbol font's glyphs, dashes and tildes on one old page, a word PDFium does not show, a run of
  digits it reads as one value. The baseline run above counts all 316. The fixes since it
  (overprinted text, Type 3 and Dingbats glyphs, thin rules drawn as fills, grids over frames and
  charts, table text taken as furniture) were designed while looking at those documents, so the run
  after them is labelled as tuned on them.
- **Left-to-right scripts only.** Right-to-left and bidirectional text is not reordered in v0.1.
- **Unruled tables have no row spans.** A label centred beside several rows splits across them
  (`Charge per` / `executed order`), and a label whose value is centred beside it needs the rows to be
  set apart by more than the label's own line pitch. A fee set on two lines around a one-line label
  (`€10 per million on the value` / `above €20,000`) splits from it, never into another fee's cell.
- **A table needs a value.** A table of text alone with no ruled grid reads as paragraphs, and a
  caption set directly above a table can join it as its first row.
- **A table beside a prose column can come apart.** Lines are grouped across the whole page before
  columns are found, so on a two-column page a prose line level with two table rows can chain them
  into one line. Those rows read as interleaved text, and the unruled stage reports them with
  `table_left_as_text`.
- **A call resolves forward only**, and a label the document prints on several notes resolves only
  on its own page or the next (for a table that continues, from its last part). A note printed before
  its call, or far from a numbering that restarts, leaves the call unresolved, with a warning. A
  parenthesised number anchored on a capitalised noun is a call by the drafting conventions, so an
  in-text reference like `Criteria (2)` can link to note 2.
- **Only page breaks join.** A paragraph continued in the next column, and list items or notes that
  continue on the next page, stay separate blocks.
- **Lists set in the Symbol font read as paragraphs.** Their bullet is a private-use character, which
  the reader drops as invisible.
- **Untrusted PDFs belong in a separate process.** MuPDF parses in memory, and a library cannot bound
  its memory or time. Read hostile input in a worker process with resource limits.

## The unique angle

Vision and OCR parsers read pixels, so they can misread a glyph or drop a value, and nothing downstream
can tell. inkgrid commits to four guarantees instead:

1. **No invented text.** Every output character is a codepoint the PDF encodes.
2. **No lost or doubled text.** Each document carries a proof that every word is owned exactly once.
3. **Independently verified structure.** A verifier re-reads the PDF with a different engine,
   PDFium, without importing the code that built the document. Every character PDFium reads must
   belong to exactly one word that holds it, every cell must hold the ink inside its rectangle, no
   drawn rule may divide a cell, and every value must be bound to one cell. On the 42 fee schedules
   of the look-back corpus, all 1,817,075 characters are accounted for, and 8 cells are reported
   (`docs/specs/10-verify.md` § 0); re-checked for 0.1.0 on 2026-10-02, with the same result.
4. **Never silent.** Anything degraded becomes a typed finding on the result.

Whether this beats OCR and vision parsers at *table structure* was an open question, and the public
evidence favored the vision hybrids. The benchmark (below) bears that out for Docling, the strongest
hybrid measured. On 11 fee schedules no fix has seen, no difference between inkgrid's table structure
and Docling's is distinguishable from 0, but Docling places tables better, finds more of their values,
and misreads fewer glyphs; on the public sets, where inkgrid is tuned, Docling is ahead on every
headline score. inkgrid is ahead of unstructured on both, of marker on the held-out set, and of the
other text-layer readers on the scores the tables below mark. It does not beat Docling; what it offers
instead is the four guarantees, in a 20th to a 35th of Docling's time per page.

## Quick start

```bash
pip install inkgrid              # or, in a uv project: uv add inkgrid
inkgrid read path/to/file.pdf -o doc.json --markdown out.md --inspector out.html
inkgrid verify path/to/file.pdf doc.json --inspector checked.html   # exit 1 on any defect
inkgrid words path/to/file.pdf --pretty    # the raw page model, for debugging a reading
```

To work on inkgrid itself, from a clone: `uv sync --all-groups`, then the same commands under
`uv run`.

From Python:

```python
import inkgrid

doc = inkgrid.read("fees.pdf")                  # a path, bytes, or a binary stream
for block in doc.blocks:
    print(block.id, block.kind, block.text)
for finding in doc.findings:
    print(finding.severity, finding.code, finding.detail)
print(doc.to_markdown())

doc = inkgrid.read("fees.pdf", strict=True)     # raises StrictModeError on an error finding

report = inkgrid.verify(doc, "fees.pdf")        # PDFium's reading against the document's
for defect in report.defects:                   # lost, invented, text, vrule, value, ...
    print(defect.page, defect.code, defect.block, defect.cell, defect.detail)
print(report.ok)
```

`inkgrid.read_pages()` returns the raw page model (words, rules, measurements) for debugging. An
encrypted PDF takes `password=`. On the command line, the password is read from stdin with
`--password-stdin`, never from arguments, because arguments show up in the process list.

## Benchmarks / Evals

**The headline: 11 fee schedules no fix has seen** (M5d). Fee schedules from 11 exchange groups that
none of inkgrid's 42 tuning documents comes from, chosen by a rule fixed before any tool read them,
three seeded pages each: 31 pages and 53 tables. Each table's grid was drafted from the page's
rendering, never from any tool's reading; each cell's text is the PDF's own words; and every table,
with 200 cells glyph by glyph, was checked by hand. inkgrid reads them as it read the tuned run below.
Every tool reads each whole document (146 pages); only its tables on the scored pages count. Eleven
documents give wide intervals. The protocol:
[`docs/specs/16-held-out-fee-set.md`](https://github.com/Abdul-Muizz1310/inkgrid/blob/v0.1.0/docs/specs/16-held-out-fee-set.md); the full report, with every
metric and paired difference:
[`bench/results/2026-10-01-fb58b0a-heldout/report.md`](https://github.com/Abdul-Muizz1310/inkgrid/blob/v0.1.0/bench/results/2026-10-01-fb58b0a-heldout/report.md).

| Tool | Structure F | Table regions F | Values bound to all labels | Values found | Cell CER (lower is better) | Seconds per page |
|---|---|---|---|---|---|---|
| **inkgrid** | 0.647 [0.418, 0.849] | 0.818 [0.655, 0.945] | 0.579 [0.363, 0.793] | 0.704 [0.451, 0.899] | 0.098 [0.029, 0.240] | 0.294 [0.211, 0.434] |
| Docling | 0.708 [0.521, 0.867] | 0.895 [0.747, 1.000] † | 0.743 [0.593, 0.865] | 0.932 [0.834, 0.988] † | 0.024 [0.003, 0.055] † | 10.158 [9.054, 11.836] † |
| Docling, image-only (OCR) | 0.707 [0.519, 0.862] | 0.862 [0.661, 1.000] | 0.772 [0.592, 0.892] | 0.923 [0.817, 0.983] † | 0.035 [0.011, 0.083] | 18.404 [12.969, 22.064] † |
| marker | 0.234 [0.114, 0.364] † | 0.850 [0.709, 0.953] | 0.153 [0.047, 0.272] † | 0.459 [0.249, 0.647] | 0.465 [0.273, 0.618] † | 0.566 [0.489, 0.732] † |
| unstructured `hi_res` (OCR) | 0.336 [0.206, 0.473] † | 0.905 [0.839, 0.962] | 0.082 [0.017, 0.175] † | 0.612 [0.388, 0.810] | 0.259 [0.147, 0.352] | 5.327 [4.824, 6.194] † |
| Camelot | 0.476 [0.202, 0.725] | 0.725 [0.496, 0.900] | 0.350 [0.114, 0.627] † | 0.357 [0.115, 0.641] † | 0.308 [0.097, 0.635] † | 0.284 [0.263, 0.326] |
| PyMuPDF | 0.490 [0.259, 0.711] | 0.776 [0.558, 0.939] | 0.320 [0.105, 0.592] † | 0.343 [0.113, 0.622] † | 0.477 [0.222, 0.703] † | 0.070 [0.058, 0.086] † |
| pdfplumber | 0.498 [0.263, 0.711] | 0.714 [0.480, 0.900] | 0.320 [0.105, 0.592] † | 0.343 [0.113, 0.622] † | 0.520 [0.241, 0.760] † | 0.096 [0.080, 0.113] † |
| inkgrid on Tesseract's words | 0.368 [0.218, 0.532] † | 0.809 [0.673, 0.928] | 0.136 [0.028, 0.305] † | 0.468 [0.291, 0.650] † | 0.144 [0.071, 0.265] | 1.681 [1.575, 1.912] † |

A † marks a tool whose paired difference from inkgrid on that metric has an interval excluding 0.
"Values bound to all labels" and "values found" score the truth's access paths (each value with its row
and column labels); cell CER counts glyph errors on the 200 checked cells, each against the closest
cell of the tool's matching table, so a missed table costs all its glyphs. Docling reads the text layer
through its layout and table models, with OCR only where a page has none; its image-only run, and
unstructured, read every page with OCR; marker reads with OCR off. The heavy tools' seconds are a warm
process's on a 16-thread CPU, their models loaded.

- **Against the other text-layer readers** (Camelot, PyMuPDF, pdfplumber): inkgrid files more values
  under all their labels (0.579 against 0.320 to 0.350) and finds more of them (0.704 against 0.343 to
  0.357), misreads fewer glyphs (0.098 against 0.308 to 0.520), and its structure recall is higher
  (0.628 against 0.402 to 0.443). Its structure F and table regions are not distinguishable from theirs.
- **Against Docling:** no difference in structure (F 0.647 against 0.708) or in values bound to all
  their labels (0.579 against 0.743) is distinguishable from 0. Docling places tables better (regions F
  0.895 against 0.818), finds more values (0.932 against 0.704), and misreads fewer glyphs (0.024
  against 0.098), at 10.2 seconds a page to inkgrid's 0.29. On the image-only copy, Docling finds more
  values (0.923); no other difference from inkgrid is distinguishable, at 18.4 seconds a page.
- **Against marker and unstructured `hi_res`:** inkgrid's structure (F 0.647 against 0.234 and 0.336)
  and values bound to all their labels (0.579 against 0.153 and 0.082) are higher, and marker misreads
  more glyphs (0.465); no difference in table regions is distinguishable.
- **What the text layer gives inkgrid:** fed Tesseract's words instead of the PDF's, inkgrid's
  structure F falls from 0.647 to 0.368 and its values bound to all their labels from 0.579 to 0.136,
  and it runs 5.7 times slower.
- **Where inkgrid fails:** on three of the 11 documents (Borsa Istanbul's data fees, JPX's participant
  fees, LuxSE's listing fees) it binds no value to all its labels and gets few of the tables' cell
  relations right; they hold 283 of its 407 misread glyphs.
- **The verifier** reports 8 cells on these documents, all on one (PSX's trading fees, pages 3 and 4),
  each a word inkgrid's grid cuts in two. **Camelot refuses one document** whose permissions forbid
  text extraction (SET's TFEX fees), scored as no tables; every other tool reads all 11.
- **The truth shares the text layer:** its cell text is the characters inkgrid and the other
  text-layer readers also read, so an OCR tool can misread a glyph where they cannot. Values found and
  cell CER compare the two kinds of tool on those terms.

**Two runs against other text-layer readers** (pdfplumber 0.11.10, PyMuPDF 1.28.2's
`find_tables()`, and Camelot 2.0.0's lattice, each with its defaults). The **baseline** is inkgrid's
reading before any fix for the reading errors its verifier found on these same documents; the one
change since M4 stops a crash on a Camelot table with no cells. The **tuned** run is its reading after
the M5c fixes, which were designed while looking at those errors, so it overstates how inkgrid reads
documents no fix has seen (DR-0023). The peers are measured again in each run, and their numbers are
identical. Each number is a point estimate with its 95% interval from 10,000 resamples of documents.
The protocol was fixed before anything was scored:
[`docs/specs/12-benchmark.md`](https://github.com/Abdul-Muizz1310/inkgrid/blob/v0.1.0/docs/specs/12-benchmark.md). The full reports, with every metric and
every paired difference, are [`bench/results/latest.md`](https://github.com/Abdul-Muizz1310/inkgrid/blob/v0.1.0/bench/results/latest.md) (tuned, with the
heavy tools below) and
[`bench/results/2026-09-29-b33b3cb/report.md`](https://github.com/Abdul-Muizz1310/inkgrid/blob/v0.1.0/bench/results/2026-09-29-b33b3cb/report.md) (baseline).

| Dataset (documents) | Metric | inkgrid, tuned | inkgrid, baseline | Camelot | PyMuPDF | pdfplumber |
|---|---|---|---|---|---|---|
| ICDAR-2013 competition (67) | Structure F, the competition's scorer | **0.788** [0.711, 0.861] | **0.777** [0.700, 0.850] | 0.637 [0.531, 0.735] | 0.611 [0.512, 0.702] | 0.591 [0.493, 0.683] |
| ICDAR-2013 competition (67) | F1-TEDS, Soric et al.'s protocol | 0.628 [0.466, 0.788] | 0.612 [0.455, 0.767] | 0.624 [0.494, 0.735] | 0.519 [0.384, 0.639] | 0.416 [0.287, 0.545] |
| ICDAR-2013 practice (58) | Structure F, the competition's scorer | **0.688** [0.596, 0.776] | **0.664** [0.569, 0.756] | 0.499 [0.381, 0.611] | 0.457 [0.346, 0.568] | 0.420 [0.314, 0.527] |
| ICDAR-2013 practice (58) | Values filed under their labels | **0.323** [0.199, 0.488] | **0.309** [0.188, 0.469] | 0.251 [0.142, 0.393] | 0.239 [0.135, 0.382] | 0.172 [0.093, 0.280] |
| olmOCR-bench tables (188) | Table tests passed | **0.486** [0.415, 0.558] | **0.481** [0.410, 0.552] | 0.273 [0.213, 0.338] | 0.321 [0.256, 0.390] | 0.294 [0.231, 0.361] |

A bold number is ahead of all three peers in its run, with every paired difference's interval
excluding 0.

- **Where inkgrid is ahead, in both runs:** table structure by the ICDAR competition's own scorer, on
  both sets, mostly through recall; the olmOCR-bench table tests, on all 188 PDFs and on the 173 with
  a text layer; and values filed under their row and column labels (the practice set's 5,603
  checkable access paths). That last metric tops out at 0.868 even when the ground truth itself is
  read as a tool, partly because some labels sit outside the value's row and column.
- **Where it is not:** under Soric et al.'s protocol no difference from Camelot or PyMuPDF is
  distinguishable from 0 in either run, and inkgrid is ahead of pdfplumber on the three structure
  scores but not on table boxes. At the baseline, its pooled structure precision on the competition
  set was below Camelot's (0.794 against 0.934), and so was its region precision on the practice set
  (0.873 against 0.940); in the tuned run neither difference is distinguishable from 0 (0.802, and
  0.895).
- **Tuned against baseline:** every tuned number in the table is higher, but the two runs are not
  paired here and each row's intervals overlap, so this benchmark does not show that the fixes
  raised these scores. What they did remove, by design, is what the verifier finds on these
  documents: 323 defects on 34 of the 313 at the baseline, 32 on 7 in the tuned run.
- **It is the slowest:** 0.35 to 0.53 seconds per page in the tuned run (0.34 to 0.55 at the
  baseline), against 0.28 to 0.36 for Camelot and 0.07 to 0.12 for PyMuPDF and pdfplumber (timings
  move about 10% between two runs of the same code). inkgrid runs Camelot's lattice for ruled grids,
  so its comparison with Camelot measures what inkgrid adds on top of it.
- **No tool crashed** on any of the 313 documents in either run. Soric et al.'s own released
  predictions, re-scored here with their evaluator, reproduce their results within 0.01 on 15 of 16
  numbers (PyMuPDF's F1-TEDS misses by 0.00002).

**OCR, vision, and hybrid parsers on the public sets** (M5d-1). The tuned run again, at `bea4c95`,
with Docling (by default and on an image-only copy of each PDF), marker (OCR off), unstructured
`hi_res` (Tesseract), and inkgrid on Tesseract's words added; inkgrid's and the three peers' counts are
identical to the first tuned run's. inkgrid is tuned on these documents and the heavy tools are not,
so the comparison flatters inkgrid. A † marks a tool whose paired difference from inkgrid has an
interval excluding 0. The full report is [`bench/results/latest.md`](https://github.com/Abdul-Muizz1310/inkgrid/blob/v0.1.0/bench/results/latest.md).

| Dataset (documents) | Metric | inkgrid, tuned | Docling | Docling, image-only (OCR) | marker | unstructured `hi_res` (OCR) | inkgrid on Tesseract's words |
|---|---|---|---|---|---|---|---|
| ICDAR-2013 competition (67) | Structure F, the competition's scorer | 0.788 [0.711, 0.861] | 0.901 [0.857, 0.937] † | 0.880 [0.827, 0.924] † | 0.768 [0.697, 0.833] | 0.467 [0.398, 0.534] † | 0.354 [0.280, 0.428] † |
| ICDAR-2013 competition (67) | F1-TEDS, Soric et al.'s protocol | 0.628 [0.466, 0.788] | 0.894 [0.846, 0.934] † | 0.881 [0.829, 0.923] † | 0.759 [0.682, 0.827] | 0.585 [0.510, 0.654] | 0.341 [0.245, 0.446] † |
| ICDAR-2013 practice (58) | Structure F, the competition's scorer | 0.688 [0.596, 0.776] | 0.847 [0.775, 0.910] † | 0.829 [0.763, 0.888] † | 0.783 [0.708, 0.850] † | 0.468 [0.397, 0.541] † | 0.328 [0.253, 0.404] † |
| ICDAR-2013 practice (58) | Values filed under their labels | 0.323 [0.199, 0.488] | 0.494 [0.329, 0.708] † | 0.473 [0.314, 0.672] † | 0.303 [0.183, 0.464] | 0.074 [0.035, 0.131] † | 0.065 [0.024, 0.126] † |
| olmOCR-bench tables (188) | Table tests passed | 0.486 [0.415, 0.558] | 0.744 [0.692, 0.792] † | 0.736 [0.683, 0.787] † | 0.460 [0.397, 0.521] | 0.413 [0.359, 0.468] | 0.303 [0.252, 0.358] † |
| ICDAR-2013 practice (58) | Seconds per page | 0.427 [0.374, 0.486] | 8.254 [6.876, 9.904] † | 13.525 [12.634, 14.583] † | 0.451 [0.440, 0.464] | 5.186 [4.962, 5.443] † | 2.226 [2.070, 2.391] † |

- **Docling is ahead of inkgrid on every one of these**, in both its runs: structure F by 0.09 to
  0.16, F1-TEDS by 0.25 to 0.27, values filed under their labels by 0.15 to 0.17, and olmOCR-bench's
  table tests by 0.25 to 0.26, at 8.3 and 13.5 seconds a page on the practice set to inkgrid's 0.43.
- **marker** is ahead on the practice set's structure (0.783 against 0.688); no other difference
  from inkgrid is distinguishable, its speed included. On the held-out fee set it is far behind.
- **unstructured `hi_res`** trails inkgrid on structure, on both sets, and on values filed under
  their labels; on F1-TEDS and olmOCR-bench no difference is distinguishable.
- **On Tesseract's words**, inkgrid trails itself on every metric (structure F 0.354 and 0.328,
  against 0.788 and 0.688): the text layer, not the gridders alone, is what puts inkgrid where it is.
- No heavy tool crashed or timed out on any of the 313 documents.

Not measured: FinTabNet, of which no official source of the PDFs remains.

## Architecture

A pure core sits between two thin shells. Only `inkgrid.read` touches MuPDF and Camelot, and only
`inkgrid.verify`'s reader touches PDFium; a test enforces the layer table on the import graph. The
verifier cannot import the code that builds the output, so its independence is structural. Details:
[`docs/ARCHITECTURE.md`](https://github.com/Abdul-Muizz1310/inkgrid/blob/v0.1.0/docs/ARCHITECTURE.md).

## Tech stack

Python 3.12+, PyMuPDF 1.28 (text layer and drawings), Pydantic v2 (frozen, validated models), uv
with the `uv_build` backend, Ruff, mypy `--strict`, pytest 9 with Hypothesis, and GitHub Actions.
Camelot 2.0 reads ruled tables. The default engine is `lattice="combined"`, because it never fused or
split a cell across 42 measured fee schedules. `"vector"` is about twice as fast end to end, but it
malformed cells on 3% of their ruled pages, mostly tables drawn as Word draws borders. `"raster"` is
also available. pypdfium2 5.13 (PDFium) powers the independent verifier.

## Deployment

inkgrid is a library, so there is nothing to deploy. A release is a version tag: `release.yml` checks
that the tag is the project's final version with a dated changelog section, runs the lint, type, and
test gates and the distribution smoke tests on Linux (CI on `main` covers the other platforms), builds
the sdist and wheel, and uploads those files to PyPI with the repository's API token; a `testpypi-v`
tag rehearses the same on TestPyPI (`docs/specs/17-release.md`). Versions are bumped with
`uv version --bump`.

## License

inkgrid's own code is MIT; see [LICENSE](https://github.com/Abdul-Muizz1310/inkgrid/blob/v0.1.0/LICENSE).

**Read this before you ship inkgrid in a product.** inkgrid requires
[PyMuPDF](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright), which Artifex
dual-licenses under the GNU AGPL-3.0 or a commercial license. Software distributed or served over a
network with inkgrid must meet the AGPL's terms for the combined work, unless you hold Artifex's
commercial license. This is not legal advice.

The other dependencies are permissively licensed: Camelot (MIT), Pydantic (MIT), OpenCV (Apache-2.0),
pypdfium2 (Apache-2.0 or BSD-3-Clause), pandas and NumPy (BSD-3-Clause). OpenCV is pinned away from
5.0.0.93, whose bundled FFmpeg lacks the CVE-2026-8461 fix.
