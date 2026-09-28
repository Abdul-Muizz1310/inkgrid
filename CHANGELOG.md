# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- The page model (`Reading`, schema `inkgrid.reading/1`): words rebuilt from characters with
  superscript markers split from their values, drawn rules from vector paths, and per-page
  measurements of hidden, clipped, unmapped, and invisible text.
- Findings for degraded input: `no_text_layer`, `blank_page`, `partial_text_layer`,
  `ocr_text_layer`, `hidden_text`, `clipped_text`, `type3_font`, `unreadable_page`, and
  `pdf_engine_warning`.
- The output contract (`Document`, schema `inkgrid.document/1`) with validator-enforced
  invariants, and JSON Schemas for both contracts in `docs/schema/`.
- `inkgrid.read_pages()`, and the `inkgrid words` command.
- `inkgrid.read()`, which builds a validated `Document`: running headers, footers, and page numbers
  as furniture; column-aware reading order; headings, paragraphs, list items, and footnotes; and the
  partition proof. `strict=True` raises `StrictModeError` on an error-severity finding.
- `Profile` and `Lexicon`, the versioned configuration a `Document` records.
- Ruled tables (M2a): Camelot lattice grids read through their edge flags, merged cells as spans,
  header and banner rows, and the findings `lattice_failed`, `lattice_disagrees`,
  `word_crosses_rule`, and `header_not_found`. `Table.to_markdown()`, `Table.to_html()`, and
  `Table.to_rows()`; `lattice="vector"` alongside `combined` and `raster`; `inkgrid read --lattice`.
- Unruled tables (M2b): whitespace-corridor grids with voted boundaries, header and banner rows,
  `header_not_found`, and `table_left_as_text` for rows no grid holds without fusing two values; currency codes are now the ISO 4217 list, so `LPS2` or `SEC 31` is no value.
- Glossaries and note lists (M2c): definition blocks from quoted, bold, and hanging terms in
  definitions sections, and from quoted terms with a defining verb anywhere; two-column grids of note
  labels or terms beside prose read as footnotes and definitions.
- Footnotes and continuation (M3): note openers, glued note numbers (split by the reader), and titled
  note tables as footnote blocks; superscript, parenthetical, and named footnote calls, each resolved
  forward, left unresolved with `call_unresolved`, or rejected by a named drafting convention, as
  `footnote_call` links; `continuation` links between the parts of a table across a page, carrying
  the header as carried cells; and paragraphs broken by a page joined into one block.
  `header_not_found` is now raised after continuation.
- Verification (M4): `inkgrid.verify(doc, pdf)` and `inkgrid verify in.pdf doc.json` re-read the PDF
  with PDFium and report, as a typed `VerificationReport` (schema `inkgrid.verification/1`), every
  lost, invented, or doubled character, table cells whose ink disagrees with them or that a drawn
  rule divides, values bound to two cells, and pages that cannot be compared; the command exits 1 on
  any defect, and `--inspector` draws the defects over the pages. `SourceMismatch` for a PDF that is
  not the document's. pypdfium2 is now a direct dependency.
- The verifier on public corpora (M5a): PDFium's map-error and control-code glyphs read as
  unmapped, surrogate pairs joined, ligatures, glyphs at the page edge or with disagreeing boxes,
  greedy ownership repaired, value tokens split at gaps, diagonal overlays counted, clips inside
  scaled Form XObjects placed through the form's matrix, and a new `decode` defect for a glyph the
  two engines decode differently. A Camelot table with no cells is skipped with `lattice_failed`
  instead of crashing the read.
- `Document.to_markdown()`, the HTML inspector, and the `inkgrid read` command with `--markdown`,
  `--inspector`, and `--strict`.
- A layer-table test on the import graph, and CI across Linux, Windows, and macOS.
