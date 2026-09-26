# M2b (Unruled tables) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tables drawn without lines come back as `Table` blocks whose grids come from whitespace
corridors, with the same header, banner, and export behaviour as ruled tables.

**Architecture:** After layout, a pure corridor stage takes each run of adjacent `rows` regions, folds
lines into rows, finds size runs and value rows, derives columns and boundaries from the whitespace,
builds `ProtoTable`s (source `corridor`), and hands the other lines back as regions for prose.

**Tech Stack:** Python 3.12+, pydantic v2, pytest 9, Hypothesis.

**Spec:** `docs/specs/07-unruled-tables.md`; shared parts in `docs/specs/06-ruled-tables.md` § 5–7.

## Global Constraints

- `core/` imports only `model`, `errors`, and the stdlib; ASCII-only source with `\uXXXX` escapes.
- Tests named `test_<CaseId>_<slug>`; 80% branch coverage per `src/` file; Ruff, format, mypy strict clean.
- Never fuse two values into one cell (L2); never copy a value into a span (L1).
- Commits: Conventional Commits, subject at most 72 characters, no emoji, no `Co-Authored-By` trailer.

## Review Focus

1. Prose that happens to hold money (hanging lists, sentences with fees): never a table (NT1, NT3).
2. A table straddling two layout regions, or two tables in one region: found whole, and apart (EX7, EX8).
3. Values stacked in one ruled cell (Euronext): one row each, never one cell (RW2, CG4).
4. Headings and intro sentences next to a table: stay out of it (EX1, EX3).
5. Corridor and ruled tables on one page, and on turned pages: both placed and valid (CP3, CP4).

---

### Task 1: Shared proto tables and value pieces
**Files:** create `src/inkgrid/core/tables/proto.py`, `src/inkgrid/core/tables/corridor.py`,
`tests/test_corridor.py`; modify `core/tables/lattice.py`, `core/tables/grid.py`, `core/assemble.py`,
`core/pipeline.py`, tests that import `ProtoTable`.
**Produces:** `ProtoTable(page, shape, cells, header_rows, banner_rows, frame, source)`,
`cell_lines(words, profile)`, `table_roles(cells, n_rows) -> (header_rows, banner_rows, text_only)`;
`is_value_piece(words) -> bool`, `is_value_like(words) -> bool`.
- [ ] Write VP1–VP3; run → FAIL. Move the shared types (suite stays green), add `source`, implement the
  two predicates; run the suite → PASS. Commit.

### Task 2: Rows
**Produces:** `Row` (lines; `size`, `top`, `bottom`, `pieces`), `fold_rows(lines) -> tuple[Row, ...]`.
- [ ] Write RW1–RW5 with `layout_builder`; run → FAIL; implement § 2; run → PASS. Commit.

### Task 3: Columns, boundaries, cells
**Produces:** `columns(rows) -> tuple[tuple[float, float], ...]`, `boundaries(columns, rows) -> tuple[float, ...]`,
`corridor_table(rows, value_rows, profile, *, page, frame) -> ProtoTable | None`.
- [ ] Write CB1–CB3, CG1–CG4; run → FAIL; implement § 4–5; run → PASS. Commit.

### Task 4: Extent and acceptance
**Produces:** `CorridorStage(tables, regions)`, `corridor_tables(regions, profile, *, page, frame) -> CorridorStage`.
- [ ] Write EX1–EX9, NT1–NT4; run → FAIL; implement § 3 and § 6; run → PASS. Commit.

### Task 5: Pipeline, fixtures, and documents
**Files:** `core/pipeline.py`, `tests/support/pdf_factory.py` (`unruled_table`, `centred_values`,
`ruled_and_unruled`, `unruled_landscape`), `tests/test_corridor_pipeline.py`, `tests/test_document.py` (CG5).
- [ ] Write CG5, CP1–CP5; run → FAIL; wire the stage (§ 7); run the suite → PASS. Commit.

### Task 6: Docs and the corpus
**Files:** `README.md`, `docs/ARCHITECTURE.md`, `CHANGELOG.md`.
- [ ] Update the docs; run `scripts/dev.sh` and the slow tests; read the seven fee schedules, render a
  sample of corridor tables in the inspector, and compare with spec § 0. Commit.
