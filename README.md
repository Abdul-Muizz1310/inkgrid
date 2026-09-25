<p align="center"><em>The demo GIF arrives with the M1 inspector, which renders each page beside its blocks.</em></p>

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

> **Status: pre-alpha (milestone M0 of M6).** Today inkgrid reads a PDF into a validated page
> model: words, drawn rules, and page measurements. Blocks and reading order arrive in M1, tables in
> M2, and independent verification in M4. The roadmap is in
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

M0 ships the foundation that everything else builds on:

- **Words rebuilt from characters.** A superscript marker printed tight against a value stays its own
  word (`$0.40` and `2`, never `$0.402`). A font change in the middle of a word keeps it one word.
- **Drawn rules** from the page's vector paths, including cell outlines drawn as rectangles.
- **Nothing degraded silently.** Image-only pages, text a clip path hides, glyphs with no Unicode
  mapping, and text in the layer that is never drawn (the shape of an OCR layer, or of hidden prompt
  injection) all come back as typed findings.
- **The full output contract,** `inkgrid.document/1`, with its invariants enforced: every word owned
  exactly once, cells that tile their grid, and block text made only of the characters of its own
  words.

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
uv run inkgrid words path/to/file.pdf --pretty
```

From Python:

```python
import inkgrid

reading = inkgrid.read_pages("fees.pdf")        # a path, bytes, or a binary stream
for word in reading.words():
    print(word.page, word.text, word.bbox, word.superscript)
for finding in reading.findings:
    print(finding.severity, finding.code, finding.detail)
```

An encrypted PDF takes `password=`. On the command line, the password is read from stdin with
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
