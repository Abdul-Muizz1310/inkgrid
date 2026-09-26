# M2c Note Lists and Glossaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Read glossary entries as definition blocks and note-list grids as footnote blocks, the M2 deliverables still open, and close M2.

**Architecture:** A new pure module, `core/glossary.py`, holds the term tests (quoted, bold, hanging), the
definitions-scope test, and the conversion of two-column grids into blocks. A document-wide pass,
`glossary()`, runs between prose and assembly: it walks each page's blocks and tables in reading order,
tracks the definitions scope across pages, re-types paragraphs, and dissolves qualifying tables. Assembly
learns the `definition` kind. The reading-order and heading-level helpers move out of `assemble.py` so
both stages share one definition of each.

**Tech Stack:** Python 3.12+, uv, pytest 9, Ruff, mypy `--strict`; no new dependencies.

**Spec:** `docs/specs/08-notes-and-glossaries.md`

## Global Constraints

- Spec-TDD: every case is a test named `test_<CaseId>_<slug>` written and watched failing before code.
- Layer table (`tests/test_architecture.py`): `core` imports only `model` (and `core`); only
  `read/pymupdf_reader.py` imports pymupdf.
- ASCII-only source: non-ASCII test data as `\uXXXX` escapes (quotes `“` `”`, euro `€`).
- The four guarantees hold: every word in exactly one block; a definition's `text` is `term + " " + body`;
  a footnote's label is its first word without `().`.
- No model or schema change: `Definition` and `Footnote` exist (`01-model.md` 8b, 8c).
- Commits: Conventional Commits, imperative, at most 72 characters, no emoji, no `Co-Authored-By`.

## Review Focus

1. A definitions heading whose scope never closes because every later heading is smaller: only the three
   term forms convert, but a bold lead-in far below the section becomes a definition. Expected: the scope
   ends at the next heading of the same or higher level, and no heading means no end.
2. A two-column grid with a banner row in its middle, or its last row a banner: expected, the banner
   becomes a heading block in place, between the rows around it.
3. Quotes the spec does not name (`« »`, `„ “`): expected, no term; the paragraph stays.
4. A term row whose first cell wraps onto two lines with a hyphen join (`Equinix FR2 Tier Co-` /
   `Location`): expected, the term renders `… Co-Location` with the join recorded, and `text` still equals
   `term + " " + body`.
5. A superscript mark that is a common word elsewhere (`A` printed raised): expected, only single-word first
   cells matching a mark count, so `A | prose` rows become notes only when `A` is printed raised somewhere.

---

### Task 1: Definition blocks through assembly

**Files:**
- Modify: `src/inkgrid/core/prose.py` (`ProseKind`, `ProtoBlock`)
- Modify: `src/inkgrid/core/assemble.py` (`_parts`, `_block`)
- Test: `tests/test_assemble.py`

**Interfaces:**
- Produces: `ProseKind` gains `"definition"`; `ProtoBlock.term: tuple[Line, ...] = ()`, the term's lines,
  which `lines` begins with (a prose term is the leading words of the first line, as a `Line` of those
  words; the body's first line is the rest of that line).

- [ ] **Step 1: Write the failing test** `test_DF14_a_definition_renders_as_term_and_body`: assemble a page
  whose one block is `ProtoBlock("definition", lines=(term_line, body_line), size=10, term=(term_line,))`
  with term words `“ABBO”` and body `means the best bid`; assert the `Document` holds one
  `Definition` with `term == "“ABBO”"`, `body == "means the best bid"`, `text == term + " " + body`,
  and `doc.to_markdown() == "**“ABBO”** means the best bid\n"`.
- [ ] **Step 2: Run it.** `uv run pytest tests/test_assemble.py -k DF14 --no-cov` — Expected: FAIL (the kind is
  not handled; the match falls through or validation fails).
- [ ] **Step 3: Implement.** In `_parts`, a definition's text is `term_text + " " + body_text` from
  `block_text` over `item.term` and over the remaining lines, and its joins are both parts' joins; `_block`
  builds `Definition.model_validate({**common, "term": ..., "body": ...})`.
- [ ] **Step 4: Run** `uv run pytest --no-cov -q` — Expected: all pass.
- [ ] **Step 5: Commit** `feat(core): assemble definition blocks from a term and a body`.

### Task 2: Terms in prose

**Files:**
- Modify: `src/inkgrid/core/lexicon.py` (`DEFINITION_WORDS`, `DEFINING_VERBS`)
- Create: `src/inkgrid/core/glossary.py`
- Test: `tests/test_glossary.py`

**Interfaces:**
- Consumes: Task 1's `ProtoBlock("definition", ..., term=...)`.
- Produces (all in `core/glossary.py`):
  - `quoted_term(words: Sequence[Word]) -> int` — how many leading words form a quoted term, 0 if none;
  - `defines(words: Sequence[Word]) -> bool` — the words open with a defining verb;
  - `bold_term(line: Line) -> int`;
  - `hanging_term(lines: Sequence[Line], profile: Profile) -> int`;
  - `as_definition(block: ProtoBlock, *, in_scope: bool, profile: Profile) -> ProtoBlock` — the paragraph
    re-typed as a definition by spec 08 § 2, or the block unchanged.
- `DEFINITION_WORDS: frozenset[str]` and `DEFINING_VERBS: tuple[tuple[str, ...], ...]` (token tuples, so
  `shall mean` is `("shall", "mean")`) in `core/lexicon.py`, values exactly as spec 08 §§ 1–2 list them.

- [ ] **Step 1: Write the failing tests** DF1–DF13 in `tests/test_glossary.py`, one test each, building
  paragraphs with `page_blocks` over `layout_builder` words (bold via `P(bold=True)`, hanging via explicit
  x positions) and asserting the kind and the term and body texts the spec's table gives.
- [ ] **Step 2: Run them.** `uv run pytest tests/test_glossary.py --no-cov` — Expected: FAIL on import
  (`inkgrid.core.glossary` does not exist).
- [ ] **Step 3: Implement** the four term tests and `as_definition`: the forms in spec 08 § 2's order; a
  prose term's `Line` is built from the first line's leading words, the body from the rest.
- [ ] **Step 4: Run** `uv run pytest --no-cov -q` — Expected: all pass (the layer test included).
- [ ] **Step 5: Commit** `feat(core): find glossary terms in prose paragraphs`.

### Task 3: Scopes and grids

**Files:**
- Create: `src/inkgrid/core/order.py` (moved from `assemble.py`: `reading_order`, `heading_level`)
- Modify: `src/inkgrid/core/assemble.py` (use `order.py`)
- Modify: `src/inkgrid/core/glossary.py`
- Test: `tests/test_glossary.py`

**Interfaces:**
- Consumes: Task 2's `as_definition`.
- Produces:
  - `order.reading_order(blocks: Sequence[ProtoBlock], tables: Sequence[ProtoTable]) -> list[ProtoBlock | ProtoTable]`
    (assemble's `_with_tables`, unchanged) and `order.heading_level(size: float, sizes: Sequence[float]) -> int`
    (assemble's `_level`, unchanged);
  - `is_definitions_title(text: str) -> bool` (spec 08 § 1);
  - `dissolve(table: ProtoTable, *, in_scope: bool, marks: frozenset[str], profile: Profile) -> tuple[ProtoBlock, ...] | None`
    — the table's rows as blocks (§ 3), or `None` when it stays a table;
  - `glossary(pages: Sequence[Sequence[ProtoBlock]], tables: Sequence[Sequence[ProtoTable]], *, marks: frozenset[str], profile: Profile) -> tuple[list[tuple[ProtoBlock, ...]], list[tuple[ProtoTable, ...]]]`
    — the document pass (§ 5); a dissolved table's blocks take its place among the page's blocks.

- [ ] **Step 1: Refactor first, under the existing suite:** move `_with_tables` (with `_slot`, `_overlaps`)
  and `_level` to `core/order.py` as public names; run `uv run pytest --no-cov -q` — Expected: all pass.
- [ ] **Step 2: Write the failing tests** SC1–SC6 and NL1–NL8 in `tests/test_glossary.py`: scopes over
  `ProtoBlock` sequences built with `page_blocks` (headings by size or bold), grids from `lattice_tables`
  over word boxes as `tests/test_lattice_tables.py`'s `run` builds them, and `marks` given directly.
- [ ] **Step 3: Run them.** Expected: FAIL (the names do not exist).
- [ ] **Step 4: Implement** `is_definitions_title`, `dissolve`, and `glossary` per spec 08 §§ 1, 3, 5.
- [ ] **Step 5: Run** `uv run pytest --no-cov -q` — Expected: all pass.
- [ ] **Step 6: Commit** `feat(core): dissolve note lists and glossary grids into blocks`.

### Task 4: The pipeline, fixtures, and docs

**Files:**
- Modify: `src/inkgrid/core/pipeline.py`
- Modify: `tests/support/pdf_factory.py` (`definitions_section`, `legend_grid`, added to `OPENABLE`)
- Create: `tests/test_glossary_pipeline.py`
- Modify: `README.md`, `docs/ARCHITECTURE.md`, `CHANGELOG.md`, `docs/specs/04-text-pipeline.md` (§ 5's
  deferral now points at spec 08)

**Interfaces:**
- Consumes: Task 3's `glossary`. `marks` is the text of every superscript word the reading holds.

- [ ] **Step 1: Write the failing tests** GP1 (`definitions_section`: a heading, a quoted, a bold, and a
  hanging entry, read end to end: three definitions in order) and NL9 (`legend_grid` read end to end: a
  heading, a definition, and a footnote, no table, a valid `Document`), and extend GP2's fixtures by the two.
- [ ] **Step 2: Run them.** Expected: FAIL (the fixtures do not exist, then the pass is not wired).
- [ ] **Step 3: Implement** the fixtures (`TextWriter` with `pymupdf.Font("helv")` for the curly quotes) and
  wire `glossary` into `build_document` after `page_blocks`.
- [ ] **Step 4: Run** `scripts/dev.sh` — Expected: all gates pass; then the seven fee schedules read, and
  SIX p6, Euronext p19, and a MIAX definitions page show definition blocks.
- [ ] **Step 5: Docs, then commit** `feat(core): read glossaries and note lists in documents` and
  `docs: describe note lists and glossaries`.
