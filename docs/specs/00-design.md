# 00 · inkgrid design

**Status:** approved 2026-09-26 (section by section, then as a written spec).
**Scope:** the whole library. Each milestone (§ 14) gets its own spec, `docs/specs/NN-<unit>.md`,
with enumerated pass and fail cases written before any code (Spec-TDD).

inkgrid reads born-digital PDFs through their text layer and their drawn vector rules. It returns a
typed, verified account of every page: every word placed in exactly one block, in reading order;
tables as explicit cell grids; and the relationships the page itself prints. It never recognizes
characters from pixels, so it never misreads one.

---

## 0 · Context

inkgrid is a clean-slate rebuild of the text-layer segmenter from **FeeLedger**, a pre-processing
pipeline for stock-exchange fee schedules. FeeLedger read each page twice: once from the text layer
(PyMuPDF, Camelot, and a whitespace-corridor gridder) and once with a vision model, then merged the
two in a "hybrid" pass. inkgrid takes only the text-layer reader. It generalizes that reader beyond fee
documents and rebuilds it as a typed, tested library. The vision reader and the hybrid pass stay out.

FeeLedger's segmenter was a prototype. It built chunks early, then ran fourteen passes that repaired
them: carving tables out of prose, splitting tables, dissolving glossaries, re-placing stray words,
and rejoining prose across page breaks. Each repair moved words between chunks and needed its own
guard against losing or duplicating them. inkgrid keeps what the prototype **measured** (§ 3) as
design constraints and discards its code shape.

A second project, a domain-agnostic annotation backend, will consume inkgrid's output. The seam is
deliberate: **inkgrid produces layout blocks; that project produces semantic chunks.**

---

## 1 · Goals, guarantees, non-goals

### What inkgrid does

Given a born-digital PDF, inkgrid returns a typed, deterministic reading of every page:

- every word of the text layer in exactly one **block**: heading, paragraph, list item, footnote,
  definition, table, or furniture (running headers, footers, page numbers), in reading order, with
  exact coordinates;
- **tables as explicit cell grids**: row and column bands, merged cells as spans, header rows carried
  across page breaks and flagged as carried;
- **the relationships the page prints**: footnote calls to their notes, and table and paragraph
  continuation across pages. Glossary entries arrive split into term and definition. Linking a term's
  *uses* elsewhere in the text is semantic work and belongs to the annotation backend.

### The guarantees (what "better than OCR" means)

| # | Guarantee | Enforced by |
|---|---|---|
| G1 | **No invented text.** Every output character is a codepoint the PDF encodes. Nothing is recognized, paraphrased, or copied; a merged cell is one span, never a duplicated value. | Text is rendered only from words (§ 8.4); the verifier's INVENTED check (§ 10) |
| G2 | **No lost or doubled text.** Every document carries a proof that each word is owned exactly once. A failed proof is a bug and raises; it is never a warning. | The partition proof in `assemble` (§ 4.4) and the model validators (§ 8.3) |
| G3 | **Independently verified structure.** A verifier re-reads the PDF through a different PDF engine and checks every table: no orphaned or doubled word, cell text equal to the ink inside it, no span across a drawn rule. | `inkgrid.verify` over PDFium (§ 10); the verifier cannot import the builder (§ 4.2) |
| G4 | **Never silent.** Anything degraded (a page without a text layer, a lattice failure, a PDF engine warning, an unresolved footnote call) becomes a typed finding on the result. | The `Finding` model (§ 9) |

### Non-goals for v0.1

- OCR of scanned or image-only pages. They are reported per page (`no_text_layer`), never guessed.
- Vision or layout models of any kind.
- Semantic classification (what a block *means*). That belongs to the annotation backend.
- Chart and figure content, math reconstruction, and form fields.

---

## 2 · Success criteria

1. G1–G4 hold on every document in the benchmark and in the FeeLedger look-back corpus: the
   verification report is clean, or every defect in it is explained in the results.
2. The benchmark (§ 11) reports inkgrid against OCR, vision, and hybrid parsers with confidence
   intervals, and the README claims only what those numbers support.
3. Speed is measured, not promised. M2 records a pages-per-second baseline (Camelot's page render is
   the expected cost), and later milestones may not regress it without saying so in the changelog.

---

## 3 · Lessons from the prototype (binding constraints)

Each row is something FeeLedger measured on real documents. A rebuild that breaks one repeats a
failure that already happened.

| # | Lesson | Evidence | How inkgrid applies it |
|---|---|---|---|
| L1 | **A value is never copied into a merged span.** Copying a fee into each row a merged cell covers invents a second fee that nothing downstream can tell from a real one. | Camelot's `copy_text` duplicated a spanned `$0.23` into two values | Cells carry `row_span`/`col_span`; no code path writes text into a position it does not print. `to_rows()` expands spans only on request and flags each copy |
| L2 | **A recall gate cannot see fusion.** Two wrongly merged cells still contain every value. | A band gridder reported 913/913 values while fusing header rows; fixing the structure exposed 935 | Structure is checked cell by cell (§ 10); value recall is reported but never used as proof of structure |
| L3 | **Word ownership must be proved across blocks, not per block.** | A table carved out of prose twice left two residuals; 32 values were duplicated while every per-chunk check passed | Ownership is decided once (§ 4.4), and `assemble` proves the partition over the whole document |
| L4 | **Conservation can pass vacuously.** A ledger that files everything as content satisfies "nothing unassigned." | 13 of 42 documents reported zero furniture; some genuinely had none, which had to be confirmed, not assumed | The ledger carries non-degeneracy companions and a `no_furniture_long_document` finding (§ 9) |
| L5 | **The text layer cannot verify label-to-value binding.** Two text engines agree to within 0.000 pt, so they share every wrong decision about which row a value belongs to. | Mean \|dx\| = 0.000 pt across five documents; row-level cross-checks flagged 71% of tables as noise | The verifier checks structure and text, and does not claim binding. Binding is measured against ground truth in the benchmark (§ 11) |
| L6 | **Superscripts fuse into the preceding word** in whitespace word extraction (`$0.40` + marker `2` → `$0.402`). | Reproduced on a synthetic PDF with PyMuPDF 1.28.2 | Words are rebuilt from characters, split wherever the superscript flag changes (§ 5.1) |
| L7 | **Footnote calls come in several co-equal forms.** Geometric superscripts resolved 0% of one document family, which writes `(1)(3)(4)` at body size. A parenthesized number is admitted only by the document's own note register and rejected by named drafting conventions (`five (5)`, `; (2) if`, `Section 202(a)(11)`). | 16 of 42 documents had unresolvable calls with superscripts alone, 0 of 42 with all classes; register membership alone admitted 48 false calls on one document | Call detection keeps all forms and the named rejection conventions; every rejection is recorded, not dropped (§ 4.3, stage 6) |
| L8 | **Furniture is detected by digit-masked frequency, never position alone**, with page numbers (arabic and roman) stripped from the key. It is detected and removed at the same granularity. | A footer whose page number moved between head and tail produced four keys below threshold and survived on 36 pages | § 4.3, stage 1 |
| L9 | **Content is never retyped as furniture by majority.** | A table title and its eight footnote calls vanished when a mixed block was retyped at 60% chrome | Furniture is decided per line; a mixed region is split at lines, never absorbed |
| L10 | **Geometric thresholds scale with each page.** | One document sets table rows 3 pt apart, another 11 pt; a fixed 6 pt threshold broke one of them either way | The Profile expresses tolerances as ratios of per-page measurements (§ 6.2) |
| L11 | **Unruled columns come from whitespace corridors, derived from data rows, clustered per line and then merged**, and a cell's extent covers its own words. | Numeric columns are centered or right-aligned, so a header and its data row differ by 8–15 pt at the left edge; a spanning header erased a corridor; wrap words bridged two columns | The corridor gridder (§ 4.3, stage 3) |
| L12 | **Continuation must be strict.** Sharing a column count is not enough, and adjacency is judged by the lowest *block* on the page, not the lowest text (the footer is furniture). | Column geometry alone produced 11 candidate pairs on one document, all false | § 4.3, stage 5 |
| L13 | **Camelot is read through its cell edge flags, never its DataFrame**; its coordinates are y-up; it finds nothing on unruled tables. | 62% of words lost when lattice parsing ran on an unruled document | § 5.2 |
| L14 | **Unicode spaces are normalized on both sides of any comparison**, and every text transform is symmetric with the verifier. | U+202F and U+00A0 made identical cells read as different; rejoining hyphenated wraps broke word conservation until chunk text was built from cells | § 8.4 and § 10 |
| L15 | **The verifier needs its own correctness review.** | An inclusive boundary test double-counted every word on a shared edge; a fixed y-band scrambled lines 0.07 pt apart | Half-open intervals everywhere; lines clustered by vertical overlap; the verifier has its own spec and tests |
| L16 | **What counts as a "value" decides what counts as a table.** The prototype's value pattern could not see whole numbers (`2,950`, `800`) or one-decimal numbers (`12.3`), so tables of such numbers went undetected. | 780 whole-number amounts in 150 tables were invisible to the pattern | The Lexicon is generic, versioned, and a measured component (§ 6.1) |
| L17 | **Header-row choice dominates binding disagreements.** | It caused more disagreements between two independent readers than every other cause combined | Header rows are an explicit, measured part of the grid (§ 8.2) and are scored by the binding metric (§ 11) |
| L18 | **Silent degradation is a defect.** | A Camelot exception returned no tables for a whole document, visible only in a counter | Every degradation becomes a finding (G4) |
| L19 | **Measure the problem before building the fix.** | Every ranked work item in the prototype's handoff turned out to be something other than its description once measured | Each milestone spec starts from a measurement; the benchmark runs per commit (§ 11) |

---

## 4 · Architecture

### 4.1 Shape: pure core, imperative shell

```
          shell: the only code that touches PDFs or third-party PDF libraries
PDF ──► read/pymupdf ──► PageModel    words (from characters, superscripts split), fonts,
    │                                drawn rules (incl. `qu` rectangles), page geometry, findings
    └─► read/camelot ──► RuledGrids   lattice cells from Camelot, converted to y-down once, here
                  │
          core: pure functions over typed values; no I/O; deterministic
                  ▼
 1 furniture      document-wide line keys → furniture words
 2 layout         lines at per-page rhythm → regions by whitespace → reading order
 3 tables         ruled regions: Camelot lattice; unruled: whitespace corridors
                  → one Grid type with explicit spans; note lists and glossaries are
                  recognized here and become footnote and definition blocks
 4 prose          remaining words → heading, paragraph, list item, footnote, definition
 5 joins          table continuation (carried headers), paragraph continuation
 6 links          footnote register and calls
 7 assemble       ids and keys, text rendered from words, ledger, partition proof
                  ▼
          Document (typed, versioned) ──► verify/  PDFium re-read with its own rules
                          │          └──► render/  inspector HTML (page renders)
                          └── model/export: Markdown / HTML / CSV / dense rows (pure)
          cli.py drives all of it: read, verify, inspect, words
```

### 4.2 Package layout and import rules

```
src/inkgrid/
├── __init__.py        public API re-exports
├── api.py             read() and verify(): the only place the shell meets the core
├── errors.py          InkgridError and subclasses
├── model/             typed values; imports nothing else from inkgrid
│   ├── geometry.py    Rect, half-open Interval
│   ├── page.py        Word, Rule, PageGeometry, PageModel, RuledGrid
│   ├── document.py    Document, Block kinds, Grid, Cell, Link, Finding, Ledger
│   ├── canonical.py   quantization, canonical JSON, content keys
│   └── export.py      pure Markdown / HTML / CSV / dense-row rendering of blocks and tables
├── read/              the only modules that import pymupdf or camelot
│   ├── pymupdf_reader.py
│   └── camelot_reader.py
├── core/              the pipeline; imports model only
│   ├── lexicon.py  profile.py  furniture.py  lines.py  layout.py
│   ├── tables/        regions.py  lattice.py  corridor.py  grid.py  headers.py
│   │                  lists.py (note lists and glossaries in grid form)
│   ├── prose.py  definitions.py (the term/definition tests both forms share)
│   ├── joins.py  links.py
│   └── assemble.py
├── verify/            imports model and pypdfium2 only; never core, never read
│   ├── pdfium_reader.py  checks.py  report.py
├── render/            inspector.py (page renders come through read/)
└── cli.py
typings/               local .pyi stubs for the untyped parts of pymupdf, camelot, pypdfium2
```

The import rules are **tested**, not documented and hoped for. A unit test walks the import graph
with `ast` and fails on any edge not in this table:

| module | may import |
|---|---|
| `model` | stdlib, pydantic |
| `core` | `model` |
| `read` | `model`, pymupdf, camelot |
| `verify` | `model`, pypdfium2 |
| `render` | `model`, `read` |
| `api` | `model`, `core`, `read`, `verify` |
| `cli` | `api`, `render`, `model` |

Because `verify` cannot import `core`, the verifier cannot share the builder's reasoning. Its
independence is a property of the import graph.

### 4.3 The pipeline stages

Every stage is a pure function from typed input to typed output. Stages 1, 3, and 4 **claim** words;
no other stage does.

1. **Furniture** (document-wide). Group each page's words into lines. Key each line by masking digit
   runs and stripping leading and trailing page numbers (arabic or roman) when the line carries real
   words. Count keys over lines in each page's top and bottom content band. A key seen on at least a
   configured share of pages is furniture. A numeric-only key (a bare page number) must also sit at a
   consistent x position, because a lone number is also how a footnote enumerator renders. An
   alphabetic key is furniture wherever it occurs on the page. Decisions are per line (L8, L9).
2. **Layout** (per page). Build lines at the page's own rhythm (L10). Split the page into regions
   along whitespace: horizontal cuts at full-width gaps, vertical cuts at whitespace rivers that run
   through most of a region's lines (a recursive XY-cut). Order regions for reading. A region whose
   lines align row by row across its rivers, with short cells, is a table candidate for stage 3; the
   rest is prose. Telling two-column prose from an unruled table is the main open problem of this
   stage, and M1 measures it (§ 15).
3. **Tables** (per page).
   - *Ruled.* Our own reading of the drawn rules marks pages with ruled regions. Camelot runs only on
     those pages. Its lattice gives row and column edges and, through cell edge flags, the spans.
   - *Unruled.* Whitespace corridors over the candidate region's value rows (L11).
   - Both produce one `Grid` type. A word belongs to the cell whose half-open rectangle contains its
     center, so assignment is a partition by construction. A span never crosses a drawn rule. Leading
     value-free rows become header rows; full-width value-free rows become banner rows.
   - A two-column grid of (number, prose) is a **note list**: each row becomes a footnote block. A
     two-column grid of (short term, prose) is a **glossary**: each row becomes a definition block.
4. **Prose** (per page, on the remaining words). Lines become blocks at rhythm, size, weight, and
   bullet boundaries. Blocks are typed heading, paragraph, list item, or footnote (small type,
   opening with an enumerator), or definition (a hanging-indent glossary entry). A heading records its
   printed section number, if any, and its type-size rank within the document.
5. **Joins** (document-wide).
   - *Table continuation.* A table continues onto the next page only when the parent is the lowest
     block on its page, the child is the highest on the next, the child has no header of its own, and
     their column edges align (L12). The child receives the parent's header cells as `carried` cells,
     which own no words. A header strip at the foot of a page with no data rows attaches forward to the
     table it heads.
   - *Paragraph continuation.* A paragraph that ends without terminal punctuation, followed by one
     that opens in lower case at the top of the next region, joins backward into one block with one
     region per page.
   - Joins create relationships and unions of blocks. They never move a word between two blocks.
6. **Links** (document-wide). The note register maps each footnote block's label to the block, scoped
   to the table or page run that numbers it, because documents restart their numbering per table. Calls
   come from superscript markers, from parenthesized numbers admitted by the register and not
   rejected by a named drafting convention (L7), and from named references (`see footnote 27`). A call
   resolves forward within a page window, never backward, because documents restart their numbering
   per table. Every candidate ends resolved, unresolved, or rejected with its reason.
7. **Assemble.** Number blocks in reading order, derive content keys (§ 8.2), render text from words
   (§ 8.4), build the ledger, and prove the partition: every word belongs to exactly one block. A
   failed proof raises `InvariantError` carrying the offending word ids.

### 4.4 The ownership rule

A word's owner is decided exactly once, by stage 1 (furniture), then stage 3 (a table cell, footnote,
or definition), then stage 4 (a prose block), in that order of precedence. No later stage moves a word
from one block to another. A paragraph join replaces two blocks with their union; a table join adds a
link and carried header cells, which own no words. The prototype needed a guard in every pass that
re-homed words (L3); inkgrid has no such passes, and one proof at the end replaces all the guards.

---

## 5 · Reading the PDF (the adapter boundary)

These are the facts, verified on PyMuPDF 1.28.2 and Camelot 2.0.0, that the two reader modules
absorb so the core never sees them.

### 5.1 PyMuPDF (`read/pymupdf_reader.py`)

- **Words** come from `page.get_text("rawdict")` characters. A word is a maximal run of non-whitespace
  characters within one span, rejoined across font changes only when the superscript state is equal,
  the two sit on one line, and the gap is at most a fraction of a point (L6).
- **Superscript** is span `flags & 1`. It is MuPDF's heuristic: a character whose origin sits more than
  0.1 × size above the line's first character. A marker that opens a line is therefore never flagged,
  and subscripts never are. Parenthesized and named calls cover the rest (L7).
- **Bold** is span `flags & 16`, or `"Bold"` in the font name, or the character-level bold bit
  (`char_flags & 8`). Fonts often misreport style, so no single signal is trusted alone. Fake bold
  (overprinting) is invisible to all three unless `TEXT_COLLECT_STYLES` is set; M0 measures whether it
  matters.
- **Font metrics per word** come from the span with the largest overlap.
- **Rules** come from `page.get_drawings()`: `l` line items, `re` rectangle items (which carry an
  orientation element), and axis-aligned `qu` quads, which is how a closed four-segment path comes back.
  Curves are not rules. A thin rectangle is a rule; a thick one is a cell background.
- **Coordinates** are PDF points in the unrotated page with origin top-left and y down. Page numbers
  are 1-based in the output.
- **Default extraction drops clipped text** (`TEXT_CLIP`). The reader counts what clipping removed and
  reports it (`clipped_text`), because the verifier's engine may still see it.
- **Glyphless and unmapped text**: zero-width and private-use codepoints go to an `invisible` ledger
  bucket. Characters without a Unicode mapping raise `partial_text_layer`. Text drawn invisibly over an
  image (render mode 3, which marks an OCR layer) raises `ocr_text_layer`, because the exactness
  guarantees do not hold for text that was itself produced by OCR. M0 specifies the detection.
- **PyMuPDF writes to stdout**: MuPDF errors, a layout-package recommendation, and a deprecation
  warning for the legacy `fitz` name. The reader routes messages away from stdout, turns MuPDF's
  collected warnings into findings, imports only `pymupdf`, and never imports `pymupdf4llm` or
  `pymupdf.layout`, which change `find_tables()` behavior for the whole process.
- **`find_tables()` is not used.** It writes a content stream into the document while it runs and
  returns rotated coordinates on rotated pages. Our own rule reading covers its line strategy.
- **Threads**: PyMuPDF is not thread-safe. inkgrid parallelizes across processes only, and says so.

### 5.2 Camelot (`read/camelot_reader.py`)

- Call `camelot.read_pdf(<bytes>, pages=<pages flagged ruled>, flavor="lattice", engine=<setting>)`.
  The engine is an explicit setting. The default is `combined` (raster detection plus the PDF's vector
  rules), the engine the prototype was running when it reported 100% cell fidelity on its base
  document. `raster` stays available as a rule reader independent of the vector paths.
- Read `Table.cells` edge flags (`left`, `right`, `top`, `bottom`), `Table.rows`, and `Table.cols`.
  Never read `Table.df` and never pass `copy_text` (L1, L13). `Cell.text` appends on assignment, so the
  reader never writes to it.
- Convert coordinates once: `x = x_camelot`, `y = mediabox_height − y_camelot`. Camelot's origin is the
  bottom-left of the MediaBox after rotation, so an offset MediaBox and a rotated page both get fixtures.
- Camelot's `resolution` argument is ignored in 2.0.0 (it always renders at 300 DPI), and grids that
  are at least 90% empty are dropped silently. When our rule reading calls a page ruled and Camelot
  returns no grid there, the reader raises `lattice_disagrees` and the page falls back to the rule
  grid, then to corridors.
- Any Camelot exception becomes `lattice_failed` for that page only. A document never loses its ruled
  tables silently (L18).
- Camelot infers rotation from text direction rather than `/Rotate`, so rotated pages are a fixture.

### 5.3 pypdfium2 (verifier only, `verify/pdfium_reader.py`)

pypdfium2 is PDFium, a different PDF engine from MuPDF, and Camelot 2.0 already depends on it, so the
verifier adds no dependency. Character boxes come from `get_charbox`. Path segments are local to their
object, so the object's matrix is applied before any rule is compared. It ships no type hints, so it
gets local stubs.

---

## 6 · Configuration

### 6.1 Lexicon: what a token is

The Lexicon classifies tokens. It never decides structure.

- **Classes:** number, money, percent, basis points, range, placeholder (`—`, `–`, `n/a`), marker
  candidate, enumerator, bullet.
- **Numbers** are locale-aware: `1,234.5`, `1.234,5`, `1 234`, and `1'234` all read correctly. So do
  signs, including U+2212, and parenthesized values.
- **Money** takes currency symbols and ISO codes, prefixed or suffixed (`€0.13`, `0.13 EUR`,
  `20,000 €`).
- **Context belongs to the core, not the Lexicon.** Whether `(47)` is a footnote marker or an
  accounting negative, or whether `2026` in a header row is a label or a value, depends on the column
  and the row, so the table and link stages decide it.
- **The default is `generic/1`.** Users can extend it with currencies, units, and patterns, and any
  change produces a new version id, which the output records.

### 6.2 Profile: geometry

Tolerances are ratios of per-page measurements (median word height, line pitch, inter-word gap, body
type size), not fixed points (L10). A profile may pin absolute values for one publisher's typesetting.
It holds geometry only; rules about what a header, footnote, or value *is* stay in code.

---

## 7 · Public API

```python
import inkgrid

doc = inkgrid.read("fees.pdf")                          # -> inkgrid.Document
doc = inkgrid.read(
    data,                                               # path, bytes, or binary file object
    password=None,
    lexicon=inkgrid.Lexicon.default(),
    profile=inkgrid.Profile.default(),
    lattice="combined",                                 # or "vector", "raster"
    strict=False,                                       # True: error-severity findings raise
)
report = inkgrid.verify(doc, "fees.pdf")                # -> inkgrid.VerificationReport

for table in doc.tables():
    table.to_markdown()
    table.to_html()
    table.to_rows()                                     # dense rows; span copies are flagged
doc.to_markdown()

text = doc.model_dump_json()                            # canonical, byte-stable
same = inkgrid.Document.model_validate_json(text)       # round-trips and re-checks invariants
```

The command line:

```
inkgrid read in.pdf -o out.json [--inspector out.html] [--markdown out.md] [--strict]
inkgrid verify in.pdf out.json          # exit 1 on any defect
inkgrid inspect in.pdf out.json -o out.html
inkgrid words in.pdf                    # the raw page model, for debugging a reading
```

`Document.tables()`, `Table.to_markdown()`, and the other export methods delegate to the pure
functions in `model/export.py`, so the convenience methods add no import edge.

---

## 8 · The output contract (`inkgrid.document/1`)

Frozen Pydantic v2 models with a published JSON Schema. Coordinates are PDF points in the unrotated
page, origin top-left, y down, quantized to 0.01 pt. Page numbers are 1-based.

### 8.1 Fields

```
Document    schema = "inkgrid.document/1"
            source    {sha256, pages, file_name?}
            producer  {inkgrid, pymupdf, camelot, pypdfium2 versions; lexicon id; profile id;
                       lattice engine}
            pages     [{number, width, height, rotation, text_layer: full | partial | none}]
            words     [Word]
            blocks    [Block]        (reading order)
            links     [Link]
            findings  [Finding]
            ledger    Ledger

Word        id · page · bbox · text · size · font · bold · italic · superscript

Block       id · key · kind · regions [{page, bbox}] · word_ids · text · markers ·
            hyphen_joins [(word_id, word_id)]
  heading     level (type-size rank; 1 = the document's largest heading size) ·
              number? (printed section number)
  paragraph
  list_item   label (the bullet or enumerator)
  footnote    label
  definition  term · body
  table       grid
  furniture   role: header | footer | page_number

Grid        n_rows · n_cols · col_bands · row_bands · header_rows · banner_rows ·
            source: lattice | corridor · cells [Cell]
Cell        row · col · row_span · col_span · text · word_ids · carried · markers

Link        kind: footnote_call | continuation
            from {block, cell?} · to? · label? · method?: superscript | parenthetical |
            named · status: resolved | unresolved | rejected · reason?
            (continuation: from = the continuing table, to = the part it continues;
            footnote_call: label and method are required)

Finding     code (closed enum, § 9) · severity: info | warning | error · page? · block? · detail

Ledger      characters per disposition (content, furniture, invisible, clipped) ·
            partition: proved · non-degeneracy flags
```

### 8.2 Identity

- `id` is the block's position in reading order (`b1`, `b2`, …), stable for one document read by one
  inkgrid version.
- `key` is content-derived: a hash of the block kind and its normalized text, with `:2`, `:3` suffixes
  for identical twins in reading order. It leaves out the page number, so it survives page shifts
  across editions. A consumer that annotates blocks keys on it.
- `source.sha256` names the exact file read. Words ship inside the document, so no consumer
  re-derives word ids from the PDF.

### 8.3 Invariants the validators enforce

A `Document` that exists satisfies all of these. Construction and parsing reject violations, which
makes illegal states unrepresentable:

- every word id belongs to exactly one block (the partition);
- every block owns at least one word (carried header cells own none, but the table that holds them
  always owns its body words);
- cells tile their grid: every span is at least 1, stays within bounds, and no position is covered
  twice;
- a `carried` cell owns no words; every other cell's words belong to its table;
- bands are monotonic and non-overlapping;
- links point at blocks that exist, and a `resolved` link has a target;
- every finding code comes from the closed enum.

### 8.4 Text rendering

Block text is rendered from words by one deterministic function that applies exactly two transforms:
whitespace normalization (all Unicode space separators become one ASCII space) and joining a
line-final hyphenated fragment to a lower-case continuation. Every hyphen join is recorded on the block
so a consumer can undo it. No other transform exists anywhere, and the verifier applies the same two
(L14).

---

## 9 · Errors and findings

Three tiers, never mixed:

1. **Bad input raises at the boundary:** `PdfOpenError` (not a PDF or unreadable), `PasswordRequired`,
   `WrongPassword`.
2. **Degradation is a `Finding` on the result**, never an exception. `doc.complete` is true when no
   finding has severity `error`. With `strict=True`, error-severity findings raise `StrictModeError`.
3. **A broken invariant is a bug:** `InvariantError` carries the failed proof and is never swallowed.

Every exception subclasses `InkgridError`.

The initial finding codes (the enum grows only in a versioned, documented way):

| code | severity | meaning |
|---|---|---|
| `no_text_layer` | error | a page has no extractable text (an image-only page) |
| `partial_text_layer` | warning | characters without a Unicode mapping, or Type 3 glyphs |
| `ocr_text_layer` | warning | the page's text is drawn invisibly over an image: it is OCR output, and G1 does not hold for it |
| `clipped_text` | info | characters removed by clip paths |
| `pdf_engine_warning` | info | a warning from MuPDF |
| `lattice_failed` | warning | Camelot raised on a page; that page fell back to the rule grid or corridors |
| `lattice_disagrees` | warning | our rule reading saw a ruled region where Camelot returned no grid |
| `word_crosses_rule` | warning | a word's box crosses a drawn cell boundary |
| `header_not_found` | info | a table has no header rows the document prints |
| `table_left_as_text` | warning | rows that read as an unruled table are left as text, because no grid holds them safely (added in M2b) |
| `call_unresolved` | warning | a footnote call with no note found |
| `no_furniture_long_document` | info | more than 8 pages and no furniture at all: confirm, do not assume |

---

## 10 · Verification

`inkgrid.verify(doc, pdf)` re-reads the PDF with PDFium and grades the document without importing
any of the code that built it.

- **Its own extraction**: characters and boxes from PDFium; rules from path objects with their
  matrices applied, using thresholds that deliberately differ from the reader's; its own reading
  sequence, with lines clustered by vertical overlap (L15).
- **Comparison happens at the character level**, so a difference in word grouping between the two
  engines cannot fake a defect. Half-open containment is used everywhere.
- **Per table**:
  - ORPHAN: a character inside the table extent that no cell rectangle contains;
  - DOUBLE: a character inside two cell rectangles;
  - TEXT: a cell's characters differ from the ink inside its rectangle;
  - ORDER: same characters in a different order. This one is advisory, because two stacked labels in
    one cell have no unambiguous order;
  - VRULE and HRULE: a span crosses a drawn rule.
- **Per document**:
  - LOST: characters PDFium sees that no block owns, net of the reader's `clipped_text` and
    `invisible` counts;
  - DOUBLED: characters owned twice;
  - INVENTED: block characters that are not on the page.
- **Value fidelity**: every value token on the page reaches exactly one block and, inside a table,
  exactly one cell.

The report is typed; `inkgrid verify` exits 1 on any defect. A defect is never auto-fixed and a
check is never loosened to make a document pass. If a disagreement is benign, the report classifies
it; the check stays as strict as it was.

---

## 11 · Evaluation: how "beats OCR" gets measured

### 11.1 What the evidence says today

Public comparisons put text-layer heuristic tools *below* vision and hybrid systems on table
structure. On ICDAR-2013 end to end, one 2026 study measured F1-TEDS of 0.50 for Camelot, 0.49 for
PyMuPDF, and 0.41 for pdfplumber, against 0.90 for Docling ([Soric et al.](https://arxiv.org/abs/2511.16134)).
The strongest competitors are hybrids: Docling, marker, and Table Transformer pipelines use a vision
model for structure and the PDF text layer for cell content. What the text layer clearly wins is
character fidelity. Acrobat scored 65.3 TEDS on PDF input against 53.7 on the same pages as images
([Zhong et al.](https://arxiv.org/abs/1911.10683)), and vision readers are documented misreading
glyphs and dropping values.

Standard metrics also barely see binding errors. In our own run of the official scorers on a toy
table, swapping two values between rows cost TEDS 0.047 and TEDS-Struct 0.000, while moving the
header row from `<thead>` to `<tbody>` cost TEDS 0.176. So the benchmark adds a binding metric.

inkgrid's claim is therefore earned by measurement, never asserted.

### 11.2 The harness (`bench/`, in the repo, not in the wheel)

Datasets are fetched by script and never redistributed.

| | choice |
|---|---|
| **Datasets** | ICDAR-2013 (original, the corrected `.c` annotations, and the practice set's value-to-header access paths): ruled government tables. FinTabNet.c: borderless financial tables, the corridor gridder's test. olmOCR-bench's table tests: third party, already reported by competitors, including 308 header-binding tests |
| **Domain set** | A held-out set of fee schedules the library was never tuned on, published as URL, SHA-256, and hand-verified ground truth, with URLs pointing at the exchanges' own sites |
| **Look-back** | The FeeLedger corpus, used to tune the prototype, so it is never a headline. Its manifest stays local and uncommitted. It shows how the redesign compares with the prototype's published numbers |
| **Metrics** (fixed before any run) | Binding triple F1 (value, row-header path, column-header path; strict and leaf-only); olmOCR heading-test pass rate; GriTS Top and Con; TEDS and TEDS-Struct, with and without header tags; ICDAR adjacency F1 with the official scorer; cell character error rate on a human glyph-verified sample; value recall; pages per second; crash and timeout counts. Structure is scored both given the true table regions and end to end |
| **Competitors** | On CPU: pdfplumber, Camelot alone, PyMuPDF `find_tables`, Docling (default and forced OCR), marker (text layer only), unstructured `hi_res` with Tesseract, and plain Tesseract. GPU and paid services run once, dated and version-pinned |
| **Ablation** | inkgrid's own gridders fed Tesseract words against text-layer words on the same pages. This isolates the text-layer effect directly |
| **Reporting** | One row per dataset and tool, never a pooled score; 95% bootstrap confidence intervals clustered by document, with a paired bootstrap for each difference; strata for ruled and unruled, spanning cells, header depth, and text-layer versus image-only pages; a table of where inkgrid loses and a failure gallery. Results are committed as JSON per commit, so each change shows better or worse than the last |

### 11.3 The claim, as it evolves

- **Now:** every output character comes from the PDF's text layer; deterministic; CPU-only.
- **After M5, and only where the numbers hold:** "cell CER X against Y for the best OCR or vision
  tool; binding F1 A against B on ruled tables and A′ against B′ on borderless tables, on born-digital
  PDFs, with confidence intervals."
- **Always stated:** not for scanned or image-only pages.
- **Falsified if**, on a pre-registered dataset, a local hybrid or vision tool matches or beats
  inkgrid's binding F1 or its cell CER with the paired interval including zero. The advantage must also
  survive glyph-verified ground truth and held-out documents.

---

## 12 · Testing

- **Spec-TDD per milestone:** spec with enumerated pass and fail cases, then failing tests, then code.
  Tests derive from spec cases, never from coverage reports.
- **Unit:** the pure core, exercised with typed `Word` and `Rule` values built in the test; no PDFs.
  The prototype's literal cases carry over where they are facts about documents: the moving-page-number
  footer keys, the twenty footnote-call cases (`five (5)` rejected, `(VIP)(6)(23)` accepted), and
  superscript splitting.
- **Property (Hypothesis):** the partition proof, span tiling, half-open containment, determinism,
  JSON round-trip, and Lexicon rules (a bare `(47)` is never a number on its own; each grouping
  convention reads correctly).
- **Integration, on every pull request:** synthetic PDFs generated inside the test run by a fixture
  factory, each with exact ground truth. Covered: a ruled table with row and column spans, an unruled
  table, two-column prose, a table continuing across a page with its header, superscript markers, a
  running header and footer, a glossary, a footnote list, a rotated page, an offset MediaBox, and an
  image-only page. A probe on 2026-09-25 confirmed the approach: MuPDF flags a synthetic raised marker
  as superscript, whitespace word extraction fuses it into the value exactly as L6 describes, and
  Camelot 2.0 detects a vector-drawn ruled table and reports its merged cell through the edge flags.
- **Look-back, nightly and before each release:** the FeeLedger corpus, fetched into a local cache.
- **Coverage:** at least 80% line and branch coverage, with per-module floors enforced by a small
  script over coverage's JSON report.
- **CI matrix:** Ubuntu on Python 3.12, 3.13, and 3.14; Windows on 3.12; macOS on 3.14; 3.15 allowed to
  fail until its release on 2026-10-01.

---

## 13 · Repository, tooling, release

- **Build:** uv with `uv_build>=0.12.19,<0.13`, `src/` layout, `py.typed`, and PEP 639 metadata:
  `license = "MIT"` with `license-files`, and no license classifiers.
- **Dependencies:** `pymupdf>=1.28.2`, `camelot-py>=2.0.0` (which brings pypdfium2, OpenCV, pandas,
  NumPy, and playa-pdf), and `pydantic>=2`. Development tools live in PEP 735 dependency groups.
- **Lint:** Ruff 0.16 with `extend-select`. Since 0.16, `select` replaces the new, larger default rule
  set instead of adding to it.
- **Types:** `mypy --strict` on `src/`, with local stubs in `typings/` for the untyped calls in
  PyMuPDF (`get_text` and `get_drawings` return `Any`), Camelot, and pypdfium2.
- **Tests:** pytest 9 with `strict = true`, importlib import mode, and warnings as errors.
- **CI:** GitHub Actions pinned by commit SHA (setup-uv has no floating major tag since v8), default
  `permissions: {}`, and Dependabot for uv and Actions.
- **Release:** a version tag publishes to PyPI with the repository's API token, as the owner's other
  packages publish, and a `testpypi-v` tag rehearses on TestPyPI (amended by spec 17 on 2026-10-02;
  the first plan was Trusted Publishing with attestations). The changelog follows Keep a Changelog 1.1.0, and versions
  are bumped with `uv version --bump`.
- **Licensing:** inkgrid's code is MIT. PyMuPDF is dual-licensed, AGPL-3.0 or Artifex commercial, and
  inkgrid requires it. The README's Licensing section says plainly that software distributed or served
  with inkgrid must meet PyMuPDF's AGPL terms unless the user holds Artifex's commercial license.
- **House skeleton:**
  - README in the house style the owner's other packages ship (feathers, slowquery-detective;
    amended 2026-10-08 by DR-0027, replacing a documented section order no README followed);
  - `WHY.md`, `LICENSE`, `CHANGELOG.md`;
  - a pull request template with the Spec-TDD checklist;
  - `docs/ARCHITECTURE.md` with a Mermaid diagram, `docs/DEMO.md`, and `docs/specs/`;
  - `.env.example` stating that the library reads no environment variables;
  - a repo `CLAUDE.md` with the non-negotiables and the commands.

---

## 14 · Milestones

Each milestone runs its own cycle: spec with enumerated cases, failing tests, implementation, review.

| | milestone | delivers | exit criteria |
|---|---|---|---|
| M0 | Foundation | repo, CI, typed model and contract, PyMuPDF reader (words, rules, geometry, findings, stdout routed), fixture factory, import-graph test | `inkgrid words in.pdf` prints a validated page model for every fixture; CI green on the matrix |
| M1 | Text | furniture, lines, multi-column layout and reading order, prose blocks, assemble with ledger and partition proof, inspector v1 | `inkgrid read` emits a valid `Document` for every fixture; the two-column fixture reads in column order |
| M2 | Tables | ruled grids (Camelot) and unruled grids (corridors) with spans, header and banner rows, note lists and glossaries, exports | exact grids on the table fixtures; ICDAR-2013 smoke run completes |
| M3 | Document | table and paragraph continuation, footnote register and calls | the twenty call cases pass; the continuation fixture carries its header |
| M4 | Verify | PDFium reader, table and document checks, value fidelity, `inkgrid verify`, defect overlays in the inspector | zero defects on the fixture suite; the look-back corpus runs and reports |
| M5 | Evaluate | benchmark harness, datasets, competitor adapters, ablation, look-back comparison | results with confidence intervals committed; README claims match them |
| M6 | Release | 0.1.0 on PyPI | a tag publishes to PyPI (spec 17) |

---

## 15 · Risks and open questions

1. **Structure quality against hybrids.** The public evidence says heuristic text-layer tools trail
   vision hybrids on table structure. The benchmark decides; if the gap is real, the options are
   better geometry, or later an optional vision extra such as Camelot's Table Transformer flavor. That
   would be a new decision, because v0.1 excludes vision.
2. **Two-column prose versus unruled tables.** Both are whitespace rivers. M1 measures the
   discriminators: row alignment across the river, cell length, sentence continuity, and value density.
3. **Generic Lexicon calibration.** Year header rows, accounting negatives against footnote markers,
   and dot leaders. It is measured on FinTabNet.c and the fee set.
4. **Camelot speed.** Rendering at 300 DPI dominates, so Camelot runs only on pages with drawn rules,
   and a process pool is an option.
5. **Different visibility rules in the two engines.** PDFium may count clipped text that MuPDF drops.
   The reader's `clipped_text` count makes the verifier's LOST check net of it; M4 confirms on fixtures.
6. **OpenCV pin.** opencv-python-headless 5.0.0.93, the newest by version, bundles an FFmpeg without
   the CVE-2026-8461 fix that 4.14.0.94 carries. inkgrid never touches video, but `pip-audit` will flag
   it. M0 decides the constraint.
7. **Local toolchain.** uv 0.12.5 on the development machine is older than the 0.12.19 floor; run
   `uv self update`.
8. **Python 3.15** goes final on 2026-10-01; it then moves into the required matrix.
