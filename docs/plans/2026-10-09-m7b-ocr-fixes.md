# M7b OCR Benchmark Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this
> plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** inkgrid finds a one-page document's furniture, reads prose columns it now reads across
(Chinese text, newspapers, margin strays), and takes a table's header set in other type, measured as
a tuned run whose test half no fix has seen.

**Architecture:** three pure-core rules, each behind its own spec 19 section:
- S3 in `core/furniture.py` runs only on a document of one page;
- a prose-column test and a section rule that lays a remainder out again in `core/layout.py`;
- H1 in `core/tables/corridor.py`'s size runs.

The OCR run (spec 18) then measures them as `tuned`, carrying every other tool's readings over from
the baseline at `00cc5ca`.

**Tech Stack:** Python 3.12, pydantic models, PyMuPDF fixtures (`tests/support/pdf_factory.py`), pytest,
Hypothesis; the bench harness of spec 18.

**Spec:** `docs/specs/19-ocr-benchmark-fixes.md`

## Global Constraints

- Source in `src/`, `tests/`, `scripts/` and `typings/` is ASCII only: write `\uXXXX` escapes.
- Never loosen a check to make a document pass; the four guarantees hold (design § 1).
- New thresholds are module constants. The `Profile` and its id `default/1` do not change.
- `core` imports only `model` and other `core` modules (`tests/test_architecture.py`).
- Each case's test is named `test_<CaseId>_<slug>` and fails before its code.
- Conventional Commits, imperative, a subject of at most 72 characters, no emoji, no trailer.
- Gates as CI runs them: `scripts/dev.sh` (ruff, format, mypy, pytest with coverage floors), and
  `uv run pytest -m heavy --no-cov` before the tuned run.

## Review Focus

1. **A rule firing on multi-page documents.** S3 must leave every document of two or more pages
   exactly as § 3 reads it: FP15 pins it, and the fee schedules' look-back diff is the proof.
2. **A table split into prose columns.** A wordy column beside value columns must keep the whole
   section as `rows`: PC4 and PC5 pin it, and olmOCR's dev table rate is the check.
3. **A footnote taken as furniture.** FP11 and FP12 pin the two shapes, and `assemble` AS11 is the
   existing case.
4. **Recursion that never ends.** A remainder laid out again could find the same gutter: `MAX_DEPTH`
   bounds it, and PC7's wide column is laid out once more, no deeper.
5. **A header run swallowing a heading or caption.** HR2 to HR6 pin the refusals; `07` EX1 and EX10
   keep passing.

---

### Task 1: One-page furniture (S3)

**Files:**
- Modify: `src/inkgrid/core/furniture.py`
- Modify: `tests/test_furniture.py` (FP1–FP15, FU4 amended); `tests/support/pdf_factory.py`
  (`one_page_furnished`); `tests/test_pipeline.py` (FP16)
- Modify: `docs/specs/04-text-pipeline.md` § 3 (FU4's row, a pointer to spec 19 § 1)

**Interfaces:**
- Produces: `page_number_token(token: str) -> bool`; `prints_page_number(line: Line) -> bool`;
  `ONE_PAGE_MIN_LINES = 4`. `find_furniture(pages, profile, *, grids=None)` keeps its signature and,
  for one page, returns S3's lines.

- [ ] **Step 1: Write the failing tests** FP1–FP15 and amend FU4, in `tests/test_furniture.py`, with
  the module's `pages_of`/`header`/`body` helpers. Each asserts `marked(find_furniture(...))`:
  - FP1 `[(1, "footer", "Page 1 of 1")]`; FP2 `[(1, "header", "Journal of Things 12")]`;
  - FP3 `[(1, "page_number", "7")]` and `[(1, "page_number", "- 7 -")]`;
  - FP4 a 7 pt head → `header`; FP8 → only the larger bottom line ending in a page number, `footer`;
  - FP12 the call case (a superscript `P("1", ..., superscript=True)` in the body) → `[]`, and without
    the call → `footer`;
  - FU4's page becomes `Acme Fee Guide`, body size, at y = 750 → `[]`;
  - FP5, FP6, FP7 (grids built as `test_FT1`'s are), FP9, FP10, FP11, FP13, FP14
    and FP15 → `[]`.

  Add `page_number_token` cases: `7`, `xii`, `2/5`, `- 7 -` (as the line) → True; `2020`, `3.`,
  `(4)`, `civil`, `12345` → False.
- [ ] **Step 2: Run** `uv run pytest tests/test_furniture.py --no-cov -q`; expect the new cases to
  fail (S3 does not exist).
- [ ] **Step 3: Implement** in `core/furniture.py`. `_one_page(page, profile, tables) ->
  tuple[FurnitureLine, ...]` applies spec 19 § 1's items 1–6. Item 4's labels come from
  `lexicon.call_parts` over the page's superscript words; its enumerator and mark come from
  `lexicon.enumerator` and `lexicon.is_mark`. `find_furniture` returns it when `len(pages) == 1`,
  with the page's S1 tables, all of them its own on one page.
- [ ] **Step 4: Run** the module's tests, then `uv run pytest tests --no-cov -q`; expect all to pass,
  `assemble` AS11 included.
- [ ] **Step 5: FP16 end to end.** Add `pdf_factory.one_page_furnished()`: one Letter page, a 7 pt
  running head at y = 40, five 10 pt body lines from y = 120, and `- 3 -` at y = 750. Test that
  `inkgrid.read(...)` gives two `furniture` blocks and that `doc.to_markdown()` holds neither text;
  watch it fail with Step 3 reverted, then pass.
- [ ] **Step 6: Commit** `feat(core): find a one-page document's furniture from its own page`.

### Task 2: Prose columns

**Files:**
- Modify: `src/inkgrid/core/lexicon.py` (receives `piece_tokens`, `MAX_QUALIFIED_TOKENS` and
  `is_value_piece` from `corridor.py`, unchanged); `src/inkgrid/core/tables/corridor.py` (imports them)
- Modify: `src/inkgrid/core/layout.py`
- Modify: `tests/test_layout.py` (PC1–PC10); `tests/support/pdf_factory.py` (`chinese_columns`);
  `tests/test_pipeline.py` (PC11)
- Modify: `docs/specs/04-text-pipeline.md` § 4 step 5 (a pointer to spec 19 § 2)

**Interfaces:**
- Consumes: `lexicon.is_value_piece(words: Sequence[Word]) -> bool`.
- Produces: `PROSE_MIN_WIDTH_EM = 10.0`, `PROSE_MIN_FILL = 0.6`, `MAX_BUSY_SHARE = 0.25`,
  `MAX_DEPTH = 4`. `_sections` returns `tuple[list[Region], bool]`, the bool true when a section of
  prose columns was found; `layout(words, profile, body_size)` keeps its signature.

- [ ] **Step 1: Move the value-piece test.** Move `is_value_piece`, its `_tokens` (renamed
  `piece_tokens`) and `MAX_QUALIFIED_TOKENS` into `lexicon.py` (`lexicon` may import `model.page`).
  `corridor.py` imports them, so `corridor.is_value_piece` keeps working. Run
  `uv run pytest tests/test_corridor.py tests/test_architecture.py --no-cov -q`; expect it to pass.
  This is a move with no behaviour, and VP1–VP3 cover it.
- [ ] **Step 2: Write the failing tests** PC1–PC10 in `tests/test_layout.py`, asserting
  `read_order(layout(place(ps), PROFILE, BODY))`.
  - PC1 builds each Chinese line as one word of 20 `中`-style characters (`P(text, x, y)`,
    width 0.5 × size × len). Two columns 105 pt wide (10.5 em), 24 pt apart, 8 lines → two `prose`
    regions.
  - PC9's and PC10's boundary columns are built to the exact quarter and the exact 10 em × 0.6.
  - PC6: the headline spans the remainder's two columns at its fourth line.
  - PC7: three 20-em sub-columns, 1 em apart, beside a 20-em prose column, 2 em apart.
- [ ] **Step 3: Run** `uv run pytest tests/test_layout.py --no-cov -q`; expect PC1, PC3, PC6, PC7,
  PC9 and PC10's prose halves to fail; PC2, PC4, PC5 and PC8 pass and guard what must not change.
- [ ] **Step 4: Implement** spec 19 § 2 in `core/layout.py`:
  - `_prose_column(parts: Sequence[Line], lines: int, busy: int, profile: Profile, body_size: float)
    -> bool`;
  - `_columns(run, gutters, profile, body_size, depth) -> list[Region] | None`, with the stray and
    remainder rules;
  - `_again(lines: Sequence[Line], profile, body_size, depth) -> tuple[list[Region], bool]`: the
    column's rows, with `_free` over its own x-range, through `_sections` at `depth + 1`;
  - `_sections` and `_prose_columns` thread `body_size` and `depth`.

  No module state: the "held columns" answer is `_sections`' bool.
- [ ] **Step 5: Run** `uv run pytest tests --no-cov -q`; expect all to pass, LY1–LY16 included.
- [ ] **Step 6: PC11 end to end.** Add `pdf_factory.chinese_columns()`: two columns of 8 lines of
  `fontname="china-s"` text, 10 pt, each line 20 characters. `inkgrid.read(...).to_markdown()`
  holds the left column's text before the right's; watch it fail on the old code.
- [ ] **Step 7: Commit** `feat(core): read prose columns by their width and fill`.

### Task 3: Header runs (H1)

**Files:**
- Modify: `src/inkgrid/core/tables/corridor.py` (`_size_runs`)
- Modify: `tests/test_corridor.py` (HR1–HR6); `tests/support/pdf_factory.py` (`year_header_table`);
  `tests/test_pipeline.py` (HR7)
- Modify: `docs/specs/07-unruled-tables.md` § 3 (a pointer to spec 19 § 3)

**Interfaces:**
- Produces: `_size_runs(lines, profile) -> list[list[Line]]`, its signature unchanged, with H1's join.

- [ ] **Step 1: Write the failing tests** HR1–HR6 with `stage(...)`, `six_rows(112)` and a new
  `year_row(y, size=8)` helper placing `2025`, `2024`, `2023` centred over Floor, Scale and Cap:
  - HR1 `table.header_rows == 1`, and the table's row 0 holds the years;
  - HR2–HR6: no table row holds the run's text, and `header_rows` is as without it.
- [ ] **Step 2: Run** `uv run pytest tests/test_corridor.py --no-cov -q`; expect HR1 to fail.
- [ ] **Step 3: Implement** H1 in `_size_runs`. A run is held back when it has at most
  `MAX_HEADER_ROWS` lines, none holds a `_holds_value` piece, and its last line's pieces sit side by
  side. It joins the next run when its last line is directly above that run's first line, within the
  taller line's height, and its size is no larger; otherwise it stays a run of its own.
- [ ] **Step 4: Run** `uv run pytest tests --no-cov -q`; expect all to pass, EX1 and EX10 included.
- [ ] **Step 5: HR7 end to end.** Add `pdf_factory.year_header_table()` and test that the table's
  HTML opens with `<thead>` holding `2025`; watch it fail on the old code.
- [ ] **Step 6: Commit** `feat(core): take a table's header set in smaller type`.

### Task 4: Dev numbers and the fee schedules

- [ ] Run the dev harness (each benchmark's pinned scorer on the dev documents, as the run scores
  them) at the branch head. Its numbers equal the prototype's, or the spec says why.
- [ ] Dump the 42 fee schedules (`~/.cache/inkgrid-bench/m6/lookback.py`) and diff them against
  0.1.0's dump in `m6/lookback-c389922/`; explain each changed block in spec 19 § 5.
- [ ] Run `scripts/dev.sh` and `uv run pytest -m heavy --no-cov`; every `OPENABLE` fixture verifies
  with no defect.
- [ ] Fill spec 19 § 0's prototype result and tick § 5; commit
  `docs: record what spec 19's rules do on the dev halves`.

### Task 5: The tuned run

Runs after the baseline at `00cc5ca` has every tool's readings and its report is committed (M7a
Task 6), and after `main` is merged into this branch.

- [ ] `PYTHONPATH=bench nice -n 10 uv run python -m inkgrid_bench.run read --datasets ocr --label
  tuned --readings-from 00cc5ca`, then `score`, then `report`, in a clean worktree at the branch head,
  detached, one document at a time. Every tool but inkgrid and inkgrid on Tesseract's words is carried
  over.
- [ ] Check the crash list for failures of the infrastructure rather than the tool; commit
  `bench/results/<date>-<commit>-ocr/` as `bench: record the tuned OCR benchmarks run`.

### Task 6: Regression gates (spec 18 § 7 item 4)

- [ ] Spec 12's run at the final commit, `--label tuned`. Explain each change in inkgrid's ICDAR-2013
  and olmOCR table numbers against `2026-10-02-bea4c95-tuned`; commit the results.
- [ ] The held-out fee set. `heldout_run.READING` names this tuned run's commit, and spec 16 § 6
  records that M7b's tuned run is now the reading it measures; no M7b fix has seen the set. Run it,
  explain each change against `2026-10-01-fb58b0a-heldout`, and commit the results.
- [ ] Final review: a fresh reviewer on the most capable model over the whole branch; fix what it
  finds, test first.
