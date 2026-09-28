# M5a The Verifier on Public Corpora Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Name the engine differences PDFium and MuPDF show on ICDAR-2013 and olmOCR-bench, so that
every defect the verifier reports on them is one of inkgrid's own errors, an ambiguous page, or a
DECODE disagreement, before the benchmark scores anything.

**Architecture:** Verifier-only changes: character kinds and surrogate pairs at the reader boundary;
ligature, second-chance, repair and decode rules in ownership; token gaps and overlays in the checks;
a new DECODE code and two counts in the report. inkgrid's reading is untouched (apart from the
Camelot crash fix already committed), so the benchmark's baseline is M4's reading.

**Tech Stack:** Python 3.12+, uv, pytest 9, Hypothesis, Ruff, mypy `--strict`; pypdfium2 5.13.0.

**Spec:** `docs/specs/11-verify-on-public-corpora.md` (amends `docs/specs/10-verify.md`)

## Global Constraints

- Spec-TDD: every case is a test named `test_<CaseId>_<slug>`, written and watched failing first.
- Never loosen a check to make a document pass: each rule names one measured engine difference and
  applies only to it; everything else stays a defect.
- No change to `read/` or `core/` behaviour (the benchmark's baseline is M4's reading).
- Corpus runs are sequential and niced; corpora stay in `~/.cache/inkgrid-bench/` and the scratchpad.
- ASCII-only source; commits: Conventional Commits, at most 72 characters, no emoji, no trailer.

## Review Focus

1. **A rule that hides a real loss.** The ligature rule must need a ligature's letters and one
   unmapped or ligature glyph in the same word; the overlap rule an identical character the word
   still needs; the edge rule a word containing the centre. Tests OW8, OW13 pin the boundaries.
2. **Repair that loops or steals.** Repair moves a character only from a word with more of it than
   it needs, and stops when nothing moves; a two-word cycle must terminate (OW11 plus a property).
3. **DECODE swallowing a loss and an invention.** A stray character inside a word and a missing one
   elsewhere in it become one DECODE: still a defect, never benign (OW12).
4. **Surrogates at a page's last index**, and a high surrogate followed by a generated character.
5. **The fee corpus and fixtures stay exactly as they were** (8 cells; 0 fixture defects).

---

### Task 1: The report's new code and counts

**Files:** `src/inkgrid/model/verification.py`, `docs/schema/verification.schema.json`,
`tests/test_verification_model.py`.

- [ ] RP7, RP8 as tests; run them (FAIL); add `DefectCode.DECODE` (after INVENTED; table code: no;
  it names its block and holds text), `PageCheck.ligature_chars` and `overlay_chars` (0 unless
  verified); export the schema; run (PASS); commit `feat(model): add DECODE and two verification counts`.

### Task 2: Kinds and surrogate pairs

**Files:** `src/inkgrid/verify/ink.py` (`char_kind`, `join_surrogates(chars) -> list[InkChar]`),
`src/inkgrid/verify/pdfium_reader.py` (call it), `tests/test_ink.py`.

- [ ] CK1–CK4 as tests (FAIL); implement § 1.1's order and § 1.2's joining; run (PASS); commit
  `fix(verify): read map-error glyphs as unmapped; join surrogate pairs`.

### Task 3: Ownership rules

**Files:** `src/inkgrid/verify/ownership.py`, `src/inkgrid/verify/report.py`,
`tests/test_ownership.py`, `tests/test_verify_report.py`.

- [ ] OW6–OW13 as tests (FAIL); implement § 2.1 (ligatures, in `_pair`), § 2.2 (second chance, in
  `_assign`), § 2.3 (repair, after pass 2), § 2.4 (DECODE, after `_pair`); `PageOwnership` gains
  `ligatures: int` and `decoded: tuple[Decode, ...]`; the report builds DECODE defects and
  `ligature_chars`; run (PASS); commit `feat(verify): name ligatures, overlaps, and decode disagreements`.

### Task 4: Value tokens and overlays

**Files:** `src/inkgrid/verify/checks.py`, `src/inkgrid/verify/report.py`,
`tests/test_verify_checks.py`.

- [ ] VF5, VF6, TB16, TB17 as tests (FAIL); implement § 3.1 and § 3.2 (`TableResult.overlay`); the
  report sums `overlay_chars`; run (PASS); commit `feat(verify): split value tokens at gaps; count overlays`.

### Task 5: The corpora and the docs

**Files:** `docs/specs/11-verify-on-public-corpora.md` § 0 (the re-verification), README, CHANGELOG.

- [ ] Re-verify the three corpora, the fixtures, and the fee corpus, one document at a time; every
  remaining defect is in § 5 or § 0's ambiguous classes or a DECODE; record the counts.
- [ ] `scripts/dev.sh` passes; commit `docs: record the verifier on public corpora`.
