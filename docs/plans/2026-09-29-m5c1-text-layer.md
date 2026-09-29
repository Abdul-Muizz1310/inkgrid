# M5c-1 The Text Layer on Public Corpora Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the text-layer reading errors spec 11 § 5 left reported (overprinted text, Type 3 control
codes, glyph names, an overhanging CropBox, a raised mark), each test-first, with the verifier's
overprint class bounded by the reader's count.

**Architecture:** Each rule sits at the stage that made the error: words (`read/words.py`), the
reader's page box and glyph names (`read/pymupdf_reader.py`, a new pure `read/glyphs.py`), and lines
(`core/lines.py`). The only verifier change is a benign class bounded by a new reader count, like
clipped characters and soft hyphens.

**Tech Stack:** Python 3.12+, uv, pytest 9, Hypothesis, Ruff, mypy `--strict`; PyMuPDF 1.28.2,
pypdfium2 5.13.

**Spec:** `docs/specs/13-text-layer-fixes.md`

## Global Constraints

- Never loosen a check to make a document pass: the verifier's overprint class accepts no more
  copies than the reader counted.
- The 42 fee schedules read exactly as before: the M5c gate (`~/.cache/inkgrid-bench/m5c/tools/
  gate.py`) diffs full-text dumps against `base-4a900cf`, one document at a time, niced.
- Every `OPENABLE` fixture verifies with no defect; the layer table holds (only
  `read/pymupdf_reader.py` imports pymupdf; `verify` never imports `read` or `core`).
- ASCII-only source (`\uXXXX` escapes); Conventional Commits, no trailer.

## Review Focus

1. **W8 dropping a word that is not a copy**: two different words sharing a place, a hidden word
   under a visible one, U+FFFD pictures. Each must stay (OP4, OP5).
2. **V1 accepting a real loss as a copy**: the copy must match an owned character's code point and
   box, and the count is capped by the reader's (VO2, VO3).
3. **`clipped_chars` with W8**: W8 on both readings, or a copy counts as clipped (OP7).
4. **Type 3 detection**: a span's font matched to the page's Type 3 fonts by PyMuPDF's
   `Type3 (<xref> 0 R)` name; the control-code rule must not fire outside them (T32).
5. **The page box's frames**: `cropbox` is top-left, `mediabox` is PDF coordinates; a rotated page
   with an overhanging CropBox; a disjoint CropBox (CB1–CB3).

---

### Task 1: The counts and the finding

**Files:** `src/inkgrid/model/{page,document,findings,verification,invariants}.py`,
`src/inkgrid/core/assemble.py`, `tests/test_page_model.py`, `tests/test_document.py`, `tests/test_findings.py`,
`tests/test_verification_model.py`, `tests/test_assemble.py`, `docs/schema/`.

- [ ] OP8 and VO4 as tests (FAIL); add `PageInfo.overprinted_chars = 0`, `Ledger.overprinted_chars`
  with the sum invariant, `FindingCode.OVERPRINTED_TEXT` (info), `PageCheck.overprint_chars` in the
  verified sum; run (PASS); regenerate schemas; commit `feat(model): count overprinted characters`.

### Task 2: Overprinted words are read once (W8)

**Files:** `src/inkgrid/read/words.py`, `src/inkgrid/read/pymupdf_reader.py`,
`src/inkgrid/read/page_findings.py`, `tests/test_words.py`, `tests/test_reader_pages.py`,
`tests/support/pdf_factory.py`.

- [ ] OP3, OP4, OP5 (typed) and OP1, OP2, OP7 (fixtures) as tests (FAIL); implement W8 on both
  readings, the count, and the finding; run (PASS); commit `feat(read): read overprinted text once`.

### Task 3: The verifier's overprint copies

**Files:** `src/inkgrid/verify/ownership.py`, `src/inkgrid/verify/report.py`,
`tests/test_ownership.py`, `tests/test_verify_api.py`, `tests/support/pdf_factory.py`.

- [ ] VO1, VO2, VO3 and OP6 (the five-copy shadow, end to end) as tests (FAIL); implement; run
  (PASS); commit `feat(verify): accept overprint copies the reader counted`.

### Task 4: Control codes in Type 3 fonts

**Files:** `src/inkgrid/read/words.py`, `src/inkgrid/read/pymupdf_reader.py`, `tests/test_words.py`,
`tests/test_reader_pages.py`, `tests/support/pdf_factory.py`.

- [ ] T31, T32 as tests (FAIL); implement; run (PASS); commit
  `fix(read): read a Type 3 control code as a glyph without Unicode`.

### Task 5: Glyph names outside the Adobe Glyph List

**Files:** `src/inkgrid/read/glyphs.py` (+ the ZapfDingbats list as data, with its license),
`src/inkgrid/read/pymupdf_reader.py`, `typings/pymupdf/`, `tests/test_glyphs.py`,
`tests/test_reader_pages.py`, `tests/support/pdf_factory.py`.

- [ ] GN1, GN2 (fixtures), GN3 (pure) as tests (FAIL); implement; run (PASS); commit
  `fix(read): decode Dingbats glyph names, and no letter from a name's digits`.

### Task 6: The page box

**Files:** `src/inkgrid/read/pymupdf_reader.py`, `tests/test_reader_pages.py`, `tests/support/pdf_factory.py`.

- [ ] CB1, CB2, CB3 as tests (FAIL); implement one box helper for geometry, frames, and Camelot's
  copy; run (PASS); commit `fix(read): measure a page from its CropBox clipped to the MediaBox`.

### Task 7: A raised mark glued to its value

**Files:** `src/inkgrid/core/lines.py`, `tests/test_lines.py`, `tests/support/pdf_factory.py`,
`tests/test_pipeline.py`.

- [ ] MK2, MK3, MK4 (typed) and MK1 (fixture) as tests (FAIL); implement; run (PASS); commit
  `fix(core): keep a raised mark on its value's line`.

### Task 8: Acceptance

**Files:** `docs/specs/{01-model,02-reader,04-text-pipeline,10-verify,13-text-layer-fixes}.md`,
`README.md`, `CHANGELOG.md`.

- [ ] Run the gate on the named documents and the fee schedules; compare with the baseline: the
  classes' defects gone, none new, fee dumps identical; record in spec 13 § 7; amend the specs,
  README, and CHANGELOG; `scripts/dev.sh` passes; commit `docs: record M5c-1's text-layer fixes`.
