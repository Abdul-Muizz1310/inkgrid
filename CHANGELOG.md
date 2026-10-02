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
- The benchmark (M5b): `bench/`, a harness in the repository but not the package. It reads ICDAR-2013
  (competition and practice) and olmOCR-bench's table pages with inkgrid, pdfplumber, PyMuPDF, and
  Camelot, each in its own pinned environment. It scores them with the competition's jar, Soric et
  al.'s evaluator, olmOCR-bench's scorer, and a binding metric over the practice set's access paths,
  and reports clustered-bootstrap intervals and paired differences. inkgrid's baseline is in
  `bench/results/`, and beside it the run after M5c's fixes, labelled as tuned on these documents
  (`run.py --label tuned`).
- The benchmark's OCR and vision competitors (M5d-1): Docling by default and on an image-only copy of
  each PDF, marker on the text layer, and unstructured `hi_res` with Tesseract, each batched in its
  own pinned CPU environment; and the ablation `inkgrid-ocr`, inkgrid fed Tesseract's words, which
  measures what the text layer gives inkgrid's own gridders. Their run on the three public sets,
  inkgrid tuned on them, is in `bench/results/`.
- The held-out fee set (M5d-2): 11 exchange fee schedules no fix has seen, chosen by a rule fixed
  before any tool read them, with ground truth drafted from each page's rendering and verified by hand,
  table by table and over 200 cells glyph by glyph. `run.py --datasets heldout` scores every tool on
  them, adding a cell character error rate over the checked cells; its results are the README's
  headline.
- `Document.to_markdown()`, the HTML inspector, and the `inkgrid read` command with `--markdown`,
  `--inspector`, and `--strict`.
- A layer-table test on the import graph, and CI across Linux, Windows, and macOS.

### Fixed

- The text layer on public corpora (M5c-1, tuned on ICDAR-2013 and olmOCR-bench):
  - text drawn twice at one place (a banner painted twice, stroke then fill, a WordArt shadow) is
    read once, counted in `overprinted_chars` with an `overprinted_text` finding; the verifier
    accepts the copies PDFium still shows, up to that count;
  - a control code in a Type 3 font (a digit glyph named `/1`) reads U+FFFD instead of vanishing;
  - a glyph named outside the Adobe Glyph List by digits (`a71`), in a font whose encoding or
    character set names it, reads by the ZapfDingbats list in a Dingbats font and as U+FFFD
    elsewhere, not as a letter made from its digits;
  - a CropBox reaching past the MediaBox is clipped to it;
  - a raised mark glued to a value stays on the value's line.
- Tables and furniture on public corpora (M5c-2, tuned on ICDAR-2013 and olmOCR-bench):
  - a filled rectangle up to 3.5 pt thick is a rule, so column rules drawn as grey fills separate
    their columns; the page's thicker fills are read as `PageModel.fills`;
  - an accepted ruled grid splits its cells at the page's own drawn rules that divide their words
    (at a rule the verifier also reads, only where it would report one dividing a cell; a fill
    3.0 to 3.5 pt thick it reads as shading), and a drawn vertical rule ends an unruled table's
    piece;
  - a grid over a table already read (a page panel, a page-scale grid, an open frame) is no table,
    and a page-border frame reads as its core (`RuledGrid.core`), leaving the headings and prose
    around the table as prose;
  - an unruled table's extent holds no other block's word (a diagonal watermark is none);
  - a chart (bars each carrying a number in one proportion to it, or a numeric axis ticked at every
    label) is no table in either gridder, and its labels stay text with a `chart_left_as_text`
    finding; a table's in-cell data bars and its sub-row rules are no chart;
  - a diagonal word (`Word.diagonal`, a watermark) is claimed by no cell;
  - a line inside a ruled table the table stage reads is never furniture, unless the table is a
    running box repeated page after page, and furniture runs from the page's edge, so a table's
    spanning header or stub banner in the page band stays in its table.
