# inkgrid — repo instructions

A Python library that reads born-digital PDFs through their text layer and drawn rules. The binding
design is `docs/specs/00-design.md`; milestone specs are `docs/specs/NN-*.md`, and task plans are in
`docs/plans/`. These instructions add to the workspace `CLAUDE.md`; where they conflict, this file
wins.

## Non-negotiables

- **Spec-TDD.** Spec cases first (`docs/specs/`), then a failing test named `test_<CaseId>_<slug>`,
  then code. Never write production code without a test you watched fail.
- **The four guarantees** (design § 1): no invented text, no lost or doubled text, independently
  verified structure, never silent. A change that weakens one is a design change, not a fix.
- **The layer table** (`tests/test_architecture.py`): `model` imports only stdlib and pydantic;
  `core` imports only `model`; `verify` never imports `core` or `read`; only
  `read/pymupdf_reader.py` imports pymupdf.
- **Never loosen a check to make a document pass.** Classify the benign case and keep the check
  strict.
- **Commits:** Conventional Commits, imperative, a subject of 72 characters at most, no emoji, and no
  `Co-Authored-By` trailer.

## Commands

```bash
uv sync --all-groups                    # uv >= 0.12.19
scripts/dev.sh                          # every CI gate, in CI's order
uv run pytest                           # unit + integration; coverage report
uv run pytest -m slow --no-cov          # build the wheel and sdist, smoke-test them
uv run python scripts/export_schemas.py # regenerate docs/schema after a model change
uv run inkgrid words file.pdf --pretty  # inspect a reading
```

## Gotchas

- **Keep source ASCII.** Write non-ASCII test data as `\uXXXX` escapes; a test fails on any
  non-ASCII byte in `src/`, `tests/`, `scripts/`, or `typings/`. Invisible characters in code are
  indistinguishable from their absence.
- **`typings/pymupdf/` replaces PyMuPDF's own hints for mypy.** Declare anything new the reader calls
  there, typed to the shape measured on the real library.
- **Fixtures are generated, not committed.** `tests/support/pdf_factory.py` builds each PDF with
  known truth. Base-14 fonts cannot encode many characters (the euro sign becomes U+00B7), so use
  `TextWriter` with `pymupdf.Font("helv")` for non-Latin-1 text.
- **PyMuPDF is AGPL-3.0 or commercial.** inkgrid's code is MIT; the README states the consequence.
  Never import `pymupdf4llm` or `pymupdf.layout`: they change `find_tables()` for the whole process.
