# M3 Notes, Footnote Calls, and Continuation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Find a document's notes in every form it prints them, link each footnote call to its note or
record why not, and join tables and paragraphs that continue across a page break.

**Architecture:** The reader splits a raised, smaller mark from the word it is glued to. Three new pure
modules run after the glossary pass: `core/notes.py` turns called note openers and titled note grids into
footnote blocks; `core/joins.py` joins continued tables (carried header cells) and paragraphs; and
`core/calls.py` finds call candidates, applies the prototype's drafting conventions, and resolves calls
forward. Assembly turns resolved, unresolved, and rejected calls and continuations into `Link`s and
`call_unresolved` findings. No model change.

**Tech Stack:** Python 3.12+, uv, pytest 9, Hypothesis, Ruff, mypy `--strict`; no new dependencies.

**Spec:** `docs/specs/09-notes-calls-and-continuation.md`

## Global Constraints

- Spec-TDD: every case is a test named `test_<CaseId>_<slug>`, written and watched failing before code.
- Layer table: `core` imports only `model` (and `core`); `read/words.py` imports nothing outside
  `model` and the stdlib.
- ASCII-only source: non-ASCII test data as `\uXXXX` escapes (`†` dagger, `®` registered).
- The guarantees hold: every word in exactly one block; joins never move a word between two blocks
  (a paragraph join is a union; a carried cell owns no words); every call candidate ends resolved,
  unresolved, or rejected with a reason; unresolved calls raise `call_unresolved`.
- No model or schema change (`01-model.md` invariants 14, 17–21 already cover links and carried cells).
- Commits: Conventional Commits, imperative, at most 72 characters, no emoji, no `Co-Authored-By`.

## Review Focus

1. A note opener whose label is also a list enumerator in a numbered list elsewhere (`1 Tier one …` in a
   table-like list, with a superscript `1` on another page): expected, only the size and shape rules of
   spec 09 § 1.1 decide; a bare number at text size opening a list of values stays a paragraph unless
   called.
2. Calls inside a paragraph joined across a page (§ 5): expected, the joined block's page for resolution
   is its first region's page, and its calls resolve against notes on that page or the next.
3. A continuation chain whose middle part reprints the header (TC7 inside TC9): expected, the reprint
   links without carrying, and the next part carries from it (its own printed header).
4. Carried header bands on a page whose table sits at the very top (no block above): expected, `room` is
   the table's top above the page top, and a band never has zero height.
5. A parenthetical `(n)` inside a table cell whose note is in a titled note grid on a later page (Cboe):
   expected, resolved from `{table, cell}` to the dissolved grid's footnote.

---

### Task 1: Glued raised marks (the reader)

**Files:** Modify `src/inkgrid/read/words.py` (`_can_join`); Test `tests/test_words.py`; Modify
`docs/specs/02-reader.md` (W3's new condition, W-22–W-23).

**Interfaces:** Produces: no API change; words split as spec 09 § 1.3.

- [ ] **Step 1:** Write W-22 and W-23 as typed `RawLine` inputs (no PDF), asserting word texts and the
  superscript flag.
- [ ] **Step 2:** Run `uv run pytest tests/test_words.py -k "W22 or W23" --no-cov`. Expected: W-22 FAILS
  (one word `1A`), W-23 passes.
- [ ] **Step 3:** In `_can_join`, refuse when the carried token's dominant size is at most 0.92 × the
  next span's size and its box bottom sits above the next character box's bottom by more than 0.2 × that
  size (pass the next span's size in).
- [ ] **Step 4:** Run the whole suite. Expected: all pass.
- [ ] **Step 5:** Commit `feat(read): split a raised, smaller mark from the word it opens`.

### Task 2: Note openers and titled note grids

**Files:** Create `src/inkgrid/core/notes.py`; Modify `src/inkgrid/core/lexicon.py` (`NOTES_WORDS`,
`NOT_CALLS`); Test `tests/test_notes.py`.

**Interfaces:**
- Produces: `call_labels(words: Iterable[Word]) -> frozenset[str]` — the labels of every superscript
  call (spec 09 § 2.1's splitting and exclusions; shared with Task 3);
  `as_note(block: ProtoBlock, *, called: frozenset[str], body: float) -> ProtoBlock` (§ 1.1);
  `note_grid(table: ProtoTable) -> tuple[ProtoBlock, ...] | None` (§ 1.2);
  `notes(pages, tables, *, called, body) -> (pages, tables)` — the document pass, in the shape of
  `glossary()`.

- [ ] **Step 1:** Write OP1–OP10 and NG1–NG4 in `tests/test_notes.py` over `page_blocks` and
  `lattice_tables` inputs, as `tests/test_glossary.py` builds them.
- [ ] **Step 2:** Run them. Expected: FAIL on import.
- [ ] **Step 3:** Implement per § 1.1–1.2.
- [ ] **Step 4:** Run the whole suite. Expected: all pass.
- [ ] **Step 5:** Commit `feat(core): read called note openers and titled note grids as notes`.

### Task 3: Call candidates and the drafting conventions

**Files:** Create `src/inkgrid/core/calls.py`; Test `tests/test_calls.py`.

**Interfaces:**
- Consumes: Task 2's `call_labels` splitting rules.
- Produces: `Candidate(label: str, method: Literal["superscript", "parenthetical", "named"], reason: str | None)`;
  `superscript_calls(words: Sequence[Word]) -> list[Candidate]`;
  `parenthetical_calls(text: str, register: frozenset[str]) -> list[Candidate]` (accepted and rejected,
  § 2.2's order); `named_calls(text: str) -> list[Candidate]`.

- [ ] **Step 1:** Write SP1–SP4 and FC1–FC20 (FC1–FC19 as a table-driven test over the verbatim texts
  against `register = {"1", ..., "54"}`, asserting accepted labels in order and each rejection reason
  named in the spec; FC20 asserting no candidate of any method).
- [ ] **Step 2:** Run them. Expected: FAIL on import.
- [ ] **Step 3:** Implement per § 2.
- [ ] **Step 4:** Run the whole suite. Expected: all pass.
- [ ] **Step 5:** Commit `feat(core): find footnote calls and reject drafting conventions`.

### Task 4: Resolution, links, and findings

**Files:** Modify `src/inkgrid/core/calls.py` (`resolve`); Modify `src/inkgrid/core/assemble.py`
(links, `call_unresolved`); Test `tests/test_calls.py`, `tests/test_assemble.py`.

**Interfaces:**
- Consumes: Task 3's candidates; the ordered items and their parts in assembly.
- Produces: `CallSite(order: int, page: int, cell: tuple[int, int] | None, candidate: Candidate)`;
  `Note(order: int, page: int, label: str)`;
  `resolve(sites: Sequence[CallSite], notes: Sequence[Note]) -> list[int | None]` — the note order each
  site resolves to (§ 3), `None` when unresolved; assembly builds one `Link` per distinct
  `(block, cell, label, method)`, and one `call_unresolved` per page with unresolved calls.

- [ ] **Step 1:** Write FR1–FR8 (FR1–FR4 on `resolve` directly; FR5–FR8 through `assemble`).
- [ ] **Step 2:** Run them. Expected: FAIL (`resolve` missing; no links built).
- [ ] **Step 3:** Implement `resolve`, and in `assemble`, after `_parts`, find the sites per block and
  per cell, resolve, and pass `links` and the findings to `Document`.
- [ ] **Step 4:** Run the whole suite. Expected: all pass.
- [ ] **Step 5:** Commit `feat(core): resolve footnote calls forward into links`.

### Task 5: Table continuation

**Files:** Create `src/inkgrid/core/joins.py`; Modify `src/inkgrid/core/tables/proto.py` (`ProtoCell`
carried text and source; `ProtoTable.continues`), `src/inkgrid/core/tables/grid.py` (carried cells),
`src/inkgrid/core/tables/lattice.py` and `corridor.py` (no `missing_header` there);
`src/inkgrid/core/assemble.py` (continuation links); Test `tests/test_joins.py`,
`tests/test_lattice_tables.py` (LT6 through the pipeline).

**Interfaces:**
- Produces: `ProtoCell.carried: str = ""`, `ProtoCell.source: tuple[tuple[int, int], ...] = ()`
  (carried when `source` is set); `ProtoTable.continues: ProtoTable | None = None`, the part it continues;
  `join_tables(pages, tables) -> tables` (§ 4); assembly emits a continuation link from each table with
  `continues` to that table's block.

- [ ] **Step 1:** Write TC1–TC10 on proto tables built with `lattice_tables`, and move LT6's
  `header_not_found` assertion to the pipeline.
- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement per § 4; raise `header_not_found` in the pipeline after joins.
- [ ] **Step 4:** Run the whole suite. Expected: all pass.
- [ ] **Step 5:** Commit `feat(core): carry a table's header onto the page it continues on`.

### Task 6: Paragraph continuation

**Files:** Modify `src/inkgrid/core/joins.py` (`join_paragraphs`); Modify `src/inkgrid/core/assemble.py`
if a block's lines span pages; Test `tests/test_joins.py`.

**Interfaces:** Produces: `join_paragraphs(pages) -> pages` — the child removed from its page, its lines
appended to the parent (§ 5).

- [ ] **Step 1:** Write PJ1–PJ6.
- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement per § 5.
- [ ] **Step 4:** Run the whole suite. Expected: all pass.
- [ ] **Step 5:** Commit `feat(core): join a paragraph broken by a page`.

### Task 7: The pipeline, fixtures, and docs

**Files:** Modify `src/inkgrid/core/pipeline.py`; `tests/support/pdf_factory.py` (`continued_table`,
`continued_paragraph`, `footnoted_table`, `glued_notes`, all in `OPENABLE`); Create
`tests/test_links_pipeline.py`; Modify `README.md`, `docs/ARCHITECTURE.md`, `CHANGELOG.md`.

- [ ] **Step 1:** Write TC11, PJ1 end to end, LK1, and LK2 over the fixtures; LK3 is the `OPENABLE`
  parametrisation.
- [ ] **Step 2:** Run them. Expected: FAIL (fixtures missing, then the passes unwired).
- [ ] **Step 3:** Add the fixtures and wire `notes` and the joins after `glossary`.
- [ ] **Step 4:** Run `scripts/dev.sh`. Expected: all gates pass. Then read the 42 fee schedules one at a
  time and count resolved, unresolved, and rejected calls against spec 09 § 0.
- [ ] **Step 5:** Docs, then commit `feat(core): link footnote calls and continued tables in documents`
  and `docs: describe notes, calls, and continuation`.
