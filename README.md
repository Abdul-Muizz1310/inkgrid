<p align="center"><em>A demo GIF of the inspector (<code>inkgrid read --inspector</code>) is still to be recorded.</em></p>

<h1 align="center">inkgrid</h1>

<p align="center">Exact tables and text from born-digital PDFs, read from the text layer and the drawn rules, and checked by a second PDF engine.</p>

<p align="center">
  <a href="WHY.md">Why</a> •
  <a href="docs/ARCHITECTURE.md">Architecture</a> •
  <a href="docs/DEMO.md">Demo Script</a> •
  <a href="docs/specs/00-design.md">Design</a>
</p>

<p align="center">
  <a href="https://github.com/Abdul-Muizz1310/inkgrid/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/Abdul-Muizz1310/inkgrid/ci.yml?branch=main&label=ci"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
</p>

> **Status: pre-alpha (milestone M4 of M6 complete).** Today inkgrid reads a PDF into a validated
> `Document`: every word in exactly one block, in reading order, with running headers and footers set
> apart, tables, ruled or not, as explicit cell grids, glossaries as definitions, and footnote calls
> linked to their notes. Tables and sentences that run onto the next page are joined. `inkgrid.verify`
> then grades the document against its PDF with a second engine, PDFium. The roadmap is in
> [`docs/specs/00-design.md`](docs/specs/00-design.md) § 14.

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
  furniture, line by line.
- **Typed blocks:** headings with their section numbers and levels, paragraphs, list items, and
  footnotes, with every line-end hyphen join recorded so it can be undone.
- **Ruled tables as cell grids.** Camelot's lattice parser reads the pages whose rules run both ways,
  through its cell edge flags, never its DataFrame. A merged cell is one cell with a span, so a value
  is never copied into the positions it covers. Leading value-free rows become header rows, and
  full-width rows become banner rows. A box around a paragraph, a furniture label, or a frame ruled
  around columns of running text is not a table.
  Tables export as GFM Markdown, HTML with `colspan`/`rowspan`, and dense rows that flag every
  repeated value.
- **Unruled tables from whitespace.** Tables set without column rules (SIX, LSE, Euronext) come from
  the whitespace between the value rows' cells, which stays put however a column is aligned. Every row
  votes on where each boundary sits, wrapped lines join their row, a drawn row rule ends a row, and two
  values never share a cell: rows that could only be read by fusing two values stay text, with a
  `table_left_as_text` warning.
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
  inkgrid's own errors: [`docs/specs/11-verify-on-public-corpora.md`](docs/specs/11-verify-on-public-corpora.md) § 5 lists them.
- **The full output contract,** `inkgrid.document/1`, with its invariants enforced: every word owned
  exactly once, cells that tile their grid exactly, and block text spelled from its own words in
  their order.

### Known limitations

- **Text is judged hidden from the text layer alone.** Text covered by an opaque shape or image,
  white text on a white page, and text too small to read all read as visible. The verifier reads the
  text layer too, so it does not catch them either.
- **Errors the verifier finds on public corpora.** On ICDAR-2013 and olmOCR-bench, inkgrid reads
  identical overprinted text twice (fake bold), drops Type 3 glyphs coded as control characters,
  lets some ruled grids reach over page frames and charts, and takes repeated table titles for
  running headers. They are listed with their documents, and fixed after the benchmark records its
  baseline, so the benchmark is not tuned on its own test documents.
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
   (`docs/specs/10-verify.md` § 0).
4. **Never silent.** Anything degraded becomes a typed finding on the result.

Whether this beats OCR and vision parsers at *table structure* is an open question, and the public
evidence so far favors the vision hybrids. The benchmark in milestone M5 decides it, and this README
will claim only what those numbers support.

## Quick start

inkgrid is not on PyPI yet. From a clone:

```bash
uv sync --all-groups
uv run inkgrid read path/to/file.pdf -o doc.json --markdown out.md --inspector out.html
uv run inkgrid verify path/to/file.pdf doc.json --inspector checked.html   # exit 1 on any defect
uv run inkgrid words path/to/file.pdf --pretty    # the raw page model, for debugging a reading
```

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

None yet. The benchmark runs in milestone M5, on ICDAR-2013, FinTabNet.c, and olmOCR-bench's table
tests, plus a held-out set of fee schedules. It compares inkgrid against OCR, vision, and hybrid
parsers, and adds a metric for values filed under the wrong row or column. The method is fixed in
advance in [`docs/specs/00-design.md`](docs/specs/00-design.md) § 11.

## Architecture

A pure core sits between two thin shells. Only `inkgrid.read` touches MuPDF and Camelot, and only
`inkgrid.verify`'s reader touches PDFium; a test enforces the layer table on the import graph. The
verifier cannot import the code that builds the output, so its independence is structural. Details:
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Tech stack

Python 3.12+, PyMuPDF 1.28 (text layer and drawings), Pydantic v2 (frozen, validated models), uv
with the `uv_build` backend, Ruff, mypy `--strict`, pytest 9 with Hypothesis, and GitHub Actions.
Camelot 2.0 reads ruled tables. The default engine is `lattice="combined"`, because it never fused or
split a cell across 42 measured fee schedules. `"vector"` is about twice as fast end to end, but it
malformed cells on 3% of their ruled pages, mostly tables drawn as Word draws borders. `"raster"` is
also available. pypdfium2 5.13 (PDFium) powers the independent verifier.

## Deployment

inkgrid is a library, so there is nothing to deploy. Releases will publish to PyPI from version tags
through Trusted Publishing, with attestations and no stored tokens (milestone M6).

## License

inkgrid's own code is MIT; see [LICENSE](LICENSE).

**Read this before you ship inkgrid in a product.** inkgrid requires
[PyMuPDF](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright), which Artifex
dual-licenses under the GNU AGPL-3.0 or a commercial license. Software distributed or served over a
network with inkgrid must meet the AGPL's terms for the combined work, unless you hold Artifex's
commercial license. This is not legal advice.

The other dependencies are permissively licensed: Camelot (MIT), Pydantic (MIT), OpenCV (Apache-2.0),
pypdfium2 (Apache-2.0 or BSD-3-Clause), pandas and NumPy (BSD-3-Clause). OpenCV is pinned away from
5.0.0.93, whose bundled FFmpeg lacks the CVE-2026-8461 fix.
