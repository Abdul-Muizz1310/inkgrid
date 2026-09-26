# M2a (Ruled tables) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ruled tables come back as `Table` blocks with explicit grids: cells and spans from Camelot's
lattice, header and banner rows, and Markdown, HTML, and dense-row exports.

**Architecture:** The shell reads Camelot page by page and hands the core unrotated cell rectangles
(`RuledGrid`). The core turns them into its reading frame, derives bands and spans, claims words by centre
before prose runs, and assembles `Table` blocks whose grids record their frame.

**Tech Stack:** Python 3.12+, Camelot 2.0 (lattice), PyMuPDF 1.28, pydantic v2, pytest 9.

**Spec:** `docs/specs/06-ruled-tables.md`, with the model change in `docs/specs/01-model.md` (Grid.frame,
invariant 15, D47). Parent: `docs/specs/00-design.md` § 4.3 stage 3 and § 5.2.

## Global Constraints

- Only `read/camelot_reader.py` imports camelot; only `read/pymupdf_reader.py` imports pymupdf; `core/`
  imports only `model`, `errors`, and the stdlib.
- Never read `Table.df`, never pass `copy_text`, never assign `Cell.text` (L1, L13).
- Dependencies: `camelot-py>=2.0.0,<3`, `opencv-python-headless>=4.14.0.94,!=5.0.0.93`.
- The lattice default stays `combined` (DR-0022); `vector` and `raster` are allowed.
- ASCII-only source, `\uXXXX` escapes for non-ASCII test data; tests named `test_<CaseId>_<slug>`.
- Every `src/` file keeps 80% branch coverage; Ruff, `ruff format`, and `mypy --strict` stay clean.
- Commits: Conventional Commits, subject at most 72 characters, no emoji, no `Co-Authored-By` trailer.

## Review Focus

1. A ruled grid around furniture or a single paragraph: never a table, words never lost (LT2, TP3, TP6).
2. Camelot raising on one page: the other pages keep their tables, and the failure is a finding (CM6).
3. Offset MediaBox, inset CropBox, and every `/Rotate`: cells land where the words are (CM2–CM5).
4. A word on a shared cell edge: in exactly one cell (LT3); spans never duplicate a value in exports (EX1, EX3).
5. Non-rectangular merged groups from inconsistent edge flags: kept as single cells (CM7).

---

### Task 1: Value classification
**Files:** `src/inkgrid/core/lexicon.py`, `tests/test_lexicon.py` · **Produces:** `is_value(text: str) -> bool`.
- [ ] Write VL1–VL4 (escapes for non-ASCII); run `uv run pytest tests/test_lexicon.py -k VL -q --no-cov` → FAIL.
- [ ] Implement the grammar of spec 06 § 1 as precompiled regexes; run → PASS. Commit `feat(core): classify value cells`.

### Task 2: Turned frames in the model
**Files:** `src/inkgrid/model/geometry.py`, `src/inkgrid/model/document.py`, `src/inkgrid/model/invariants.py`,
`src/inkgrid/core/view.py`, `tests/test_document.py`, `tests/support/doc_builder.py` ·
**Produces:** `turn_point(x, y, rotation, width, height) -> tuple[float, float]`, `turn_rect(rect, rotation,
width, height) -> Rect`, `Grid.frame: Literal[0, 90, 180, 270] = 0`.
- [ ] Write D47 (doc_builder table with `frame=90`); run → FAIL. Move `_turn` from `core/view.py` to the model,
  add `Grid.frame`, turn centres in the invariant-15 check; run the suite → PASS; regenerate schemas.
  Commit `feat(model): record the frame a table grid is measured in`.

### Task 3: Lattice types and page frames
**Files:** `src/inkgrid/model/lattice.py`, `src/inkgrid/read/pymupdf_reader.py`, `typings/pymupdf/__init__.pyi`,
`tests/test_lattice_model.py`, `tests/test_reader_pages.py` · **Produces:** `PageFrame`, `RuledGrid`,
`LatticeReading` (spec 06 § 2); `page_frames(data: bytes, password: str | None) -> tuple[PageFrame, ...]`.
- [ ] Write tests: a `RuledGrid` with no cells or a zero-size cell is rejected; `page_frames` on
  `offset_mediabox` and `cropbox` reports their boxes. Run → FAIL. Implement; run → PASS. Commit.

### Task 4: The Camelot reader
**Files:** `pyproject.toml`, `uv.lock`, `src/inkgrid/read/camelot_reader.py`, `typings/camelot/__init__.pyi`,
`tests/test_camelot_reader.py`, `tests/support/pdf_factory.py` (`ruled_grid`, `ruled_landscape`, variants),
`tests/test_architecture.py` (AP4) · **Produces:** `read_lattice(data, frames, pages, *, engine, password) ->
LatticeReading`.
- [ ] Add the dependencies (`uv add`), write CM1–CM8 and AP4; run → FAIL. Implement per § 2 (merged groups by
  union-find over undrawn edges; frame by `pdf_size` and `/Rotate`); run → PASS. Commit.

### Task 5: Pages and grid shapes
**Files:** `src/inkgrid/core/tables/__init__.py`, `pages.py`, `shape.py`, `tests/test_table_shape.py` ·
**Produces:** `lattice_pages(reading: Reading) -> tuple[int, ...]`; `grid_shape(cells: Sequence[Rect]) ->
GridShape | None` with `GridShape(row_edges, col_edges, cells: tuple[ShapeCell(row, col, row_span, col_span,
rect), ...])`.
- [ ] Write LP1, GS1–GS3; run → FAIL; implement; run → PASS. Commit.

### Task 6: The table stage
**Files:** `src/inkgrid/core/tables/lattice.py`, `tests/test_lattice_tables.py` · **Produces:**
`lattice_tables(page, grids, words, lexicon, profile) -> TableStage(tables: tuple[ProtoTable, ...],
claimed: frozenset[int], findings)`, `ProtoTable(shape, cells: tuple[ProtoCell(shape_cell, lines), ...],
header_rows, banner_rows, bbox, frame)`.
- [ ] Write LT1–LT9 (hand-built pages with `layout_builder` and `RuledGrid`s); run → FAIL; implement § 5;
  run → PASS. Commit.

### Task 7: Tables in the pipeline
**Files:** `src/inkgrid/core/pipeline.py`, `src/inkgrid/core/assemble.py`, `src/inkgrid/core/view.py`,
`tests/test_table_pipeline.py`, `tests/support/pdf_factory.py` (`table_between_paragraphs`,
`boxed_paragraph`, `labelled_page`) · **Produces:** `build_document(reading, *, lexicon, profile, lattice,
grids: LatticeReading | None = None)`.
- [ ] Write TP1–TP6; run → FAIL; implement § 6 (turn grids for upright pages; claim before layout; insert by
  top; build `Grid`/`Cell`/`Table`); run the suite → PASS. Commit.

### Task 8: Exports and the inspector
**Files:** `src/inkgrid/model/export.py`, `src/inkgrid/model/document.py`, `src/inkgrid/render/inspector.py`,
`tests/test_export.py`, `tests/test_inspector.py` · **Produces:** `Table.to_markdown()`, `Table.to_html()`,
`Table.to_rows() -> tuple[tuple[DenseCell, ...], ...]`.
- [ ] Write EX1–EX5; run → FAIL; implement § 7; run → PASS. Commit.

### Task 9: API, CLI, docs, and the corpus
**Files:** `src/inkgrid/api.py`, `src/inkgrid/cli.py`, `src/inkgrid/model/document.py` (Lattice adds `vector`),
`tests/test_api.py`, `tests/test_cli.py`, `README.md`, `docs/ARCHITECTURE.md`, `CHANGELOG.md` ·
- [ ] Write AP1–AP3; run → FAIL; wire `read` and `--lattice`; update docs; run `scripts/dev.sh` and the slow
  tests → all gates pass; read the seven fee schedules and compare with spec 06 § 0. Commit.
