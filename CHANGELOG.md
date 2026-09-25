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
  `ocr_text_layer`, `hidden_text`, `clipped_text`, and `pdf_engine_warning`.
- The output contract (`Document`, schema `inkgrid.document/1`) with validator-enforced
  invariants, and JSON Schemas for both contracts in `docs/schema/`.
- `inkgrid.read_pages()`, and the `inkgrid words` command.
- A layer-table test on the import graph, and CI across Linux, Windows, and macOS.
