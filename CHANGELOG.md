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
- `Document.to_markdown()`, the HTML inspector, and the `inkgrid read` command with `--markdown`,
  `--inspector`, and `--strict`.
- A layer-table test on the import graph, and CI across Linux, Windows, and macOS.
