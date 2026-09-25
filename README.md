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

> **Status: pre-alpha (milestone M1 of M6).** Today inkgrid reads a PDF into a validated `Document`:
> every word in exactly one block, in reading order, with running headers and footers set apart.
> Tables arrive in M2, footnote links and table continuation in M3, and independent verification in
> M4. The roadmap is in
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

Shipped so far (M0 and M1):

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
- **Markdown and an HTML inspector.** The inspector draws every block over its rendered page, for
  looking at a reading rather than trusting it.
- **The full output contract,** `inkgrid.document/1`, with its invariants enforced: every word owned
  exactly once, cells that tile their grid exactly, and block text spelled from its own words in
  their order.

### Known limitations

- **Text is judged hidden from the text layer alone.** Text covered by an opaque shape or image,
  white text on a white page, and text too small to read all read as visible. The independent
  verifier (M4) is where those checks belong.
- **Left-to-right scripts only.** Right-to-left and bidirectional text is not reordered in v0.1.
- **No tables yet.** Until M2, a table reads as rows of text, in row order.
- **Lists set in the Symbol font read as paragraphs.** Their bullet is a private-use character, which
  the reader drops as invisible.
- **Untrusted PDFs belong in a separate process.** MuPDF parses in memory, and a library cannot bound
  its memory or time. Read hostile input in a worker process with resource limits.

## The unique angle

Vision and OCR parsers read pixels, so they can misread a glyph or drop a value, and nothing downstream
can tell. inkgrid commits to four guarantees instead:

1. **No invented text.** Every output character is a codepoint the PDF encodes.
2. **No lost or doubled text.** Each document carries a proof that every word is owned exactly once.
3. **Independently verified structure.** A verifier re-reads the PDF with a different engine (PDFium)
   and checks every table cell by cell (milestone M4).
4. **Never silent.** Anything degraded becomes a typed finding on the result.

Whether this beats OCR and vision parsers at *table structure* is an open question, and the public
evidence so far favors the vision hybrids. The benchmark in milestone M5 decides it, and this README
will claim only what those numbers support.

## Quick start

inkgrid is not on PyPI yet. From a clone:

```bash
uv sync --all-groups
uv run inkgrid read path/to/file.pdf --pretty --markdown out.md --inspector out.html
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

A pure core sits between two thin shells. Only `inkgrid.read` touches PDF libraries, and a test
enforces the layer table on the import graph. The verifier (M4) cannot import the code that builds
the output, so its independence is structural. Details:
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Tech stack

Python 3.12+, PyMuPDF 1.28 (text layer and drawings), Pydantic v2 (frozen, validated models), uv
with the `uv_build` backend, Ruff, mypy `--strict`, pytest 9 with Hypothesis, and GitHub Actions. From
M2, Camelot 2.0 reads ruled tables; from M4, pypdfium2 powers the independent verifier.

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
