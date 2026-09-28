# 03 · Public surface, CLI, architecture test, packaging (M0)

**Implements:** `00-design.md` § 4.2 (import rules), § 7 (API and CLI, the M0 part), § 12–13
(testing and tooling), and the M0 exit criteria in § 14.

---

## 1 · Public API in M0

```python
import inkgrid

reading = inkgrid.read_pages("fees.pdf", password=None)   # -> inkgrid.Reading
inkgrid.__version__                                        # "0.1.0.dev0" during development
```

- `read_pages` lives in `api.py`. It is the raw page model, for debugging a reading. `inkgrid.read()`,
  which returns a `Document`, arrives in M1. It is **not** stubbed in M0: a public function that raises
  `NotImplementedError` is built but never wired (RR-0002).
- The package root re-exports:
  - the error classes;
  - the model types a caller needs: `Reading`, `PageModel`, `PageInfo`, `Word`, `Rule`, `Rect`,
    `Interval`, `Finding`, `FindingCode`, `Severity`, and the `Document` family;
  - from M4, the report types: `VerificationReport`, `PageCheck`, `Defect`, and `DefectCode`;
  - `read_pages` and `__version__`.

  `__all__` lists exactly these.
- `errors.py` defines `InkgridError`, and under it `PdfOpenError`, `PasswordRequired`,
  `WrongPassword`, `InvariantError`, and `StrictModeError`.

| # | case | expected |
|---|---|---|
| A1 | `inkgrid.read_pages(path)` on a fixture | a `Reading` equal to the reader's output |
| A2 | every name in `inkgrid.__all__` | importable from `inkgrid` |
| A3 | the exception hierarchy | every error subclasses `InkgridError`; none subclasses `ValueError` or `OSError` |
| A4 | `inkgrid.__version__` | equals `importlib.metadata.version("inkgrid")` |

---

## 2 · CLI (`cli.py`, entry point `inkgrid`, also `python -m inkgrid`)

```
inkgrid words IN.pdf [-o OUT.json] [--pretty] [--password-stdin]
inkgrid --version
```

- `words` prints the `Reading` as canonical JSON to stdout, or writes it to `-o`. `--pretty` indents
  by 2 for reading; the canonical form is compact.
- `--password-stdin` reads the password from the first line of stdin, as bytes decoded as UTF-8, so a
  non-ASCII password survives a console whose locale encoding differs. Bytes that are not UTF-8 are
  a usage error (exit 2). There is no `--password` flag,
  because a password in argv is visible in the process list.
- An output file that cannot be written (a missing directory, no permission) is an input problem:
  exit 2 with one line on stderr.
- A reader that closes the pipe early (`inkgrid words f.pdf | head`) ends output quietly with exit 0:
  no traceback. The output already produced was correct.
- Exit codes:
  - 0: success;
  - 1: reserved for defects (`verify`, M4) and strict mode (M1);
  - 2: usage errors (argparse's convention) and unreadable input: `PdfOpenError`,
    `PasswordRequired`, or `WrongPassword`. The message goes to stderr, with no traceback.
- The CLI imports only `api`, `model`, `errors`, and the stdlib (argparse).

| # | case | expected |
|---|---|---|
| L1 | `inkgrid words fixture.pdf` for **every** fixture in the factory | exit 0; stdout parses as a `Reading` (M0 exit criterion) |
| L2 | `-o out.json` | exit 0; the file holds the canonical JSON; stdout is empty |
| L3 | `--pretty` | indented JSON that parses to the same `Reading` |
| L4 | a missing file; a non-PDF | exit 2; one line on stderr naming the problem; no traceback |
| L5 | an encrypted PDF without `--password-stdin` | exit 2; stderr says a password is required |
| L6 | `--password-stdin` with the right / a wrong password | exit 0 / exit 2 |
| L7 | `inkgrid --version` | prints the version; exit 0 |
| L8 | no subcommand; an unknown one | exit 2 with usage |
| L9 | `python -m inkgrid words fixture.pdf` | same as L1 |
| L10 | `-o missing-dir/out.json` | exit 2; one line on stderr naming the path; no traceback |
| L11 | stdout closed after the first bytes (a pipe to `head -c 1`) | exit 0; nothing on stderr |
| L12 | `--password-stdin` with a UTF-8 non-ASCII password, under a Latin-1 locale stdin | exit 0 |
| L13 | `--password-stdin` with bytes that are not UTF-8 | exit 2; stderr says the password is not UTF-8; no traceback |

---

## 3 · The architecture test (`tests/test_architecture.py`)

A test parses every module under `src/inkgrid/` with `ast` and checks each import against this table.
Relative imports are banned by Ruff (TID252), so every internal import is absolute.

| module | may import (plus the stdlib and `inkgrid.errors`) |
|---|---|
| `inkgrid.model` | pydantic |
| `inkgrid.core` | `inkgrid.model` |
| `inkgrid.read` | `inkgrid.model`, pymupdf, camelot |
| `inkgrid.verify` | `inkgrid.model`, pypdfium2 |
| `inkgrid.render` | `inkgrid.model`, `inkgrid.read` |
| `inkgrid.api` | `inkgrid.model`, `inkgrid.core`, `inkgrid.read`, `inkgrid.verify` |
| `inkgrid.cli` | `inkgrid.api`, `inkgrid.render`, `inkgrid.model` |
| `inkgrid` (the package `__init__`) | `inkgrid.api`, `inkgrid.model` |
| `inkgrid.__main__` | `inkgrid.cli` |
| `inkgrid.errors` | nothing |

Within a layer, modules may import each other. The stdlib is `sys.stdlib_module_names`, plus
`__future__`.

**Extra rule inside `read/`.** Only `read/pymupdf_reader.py` may import pymupdf (and, from M2, only
`read/camelot_reader.py` may import camelot). This keeps `words.py` and `rules.py` pure.

| # | case | expected |
|---|---|---|
| T1 | the real source tree | no violations |
| T2 | a temporary tree where `model/x.py` imports `inkgrid.core` | one violation, naming the file and the import |
| T3 | a temporary tree where `verify/x.py` imports `inkgrid.core.lines` | one violation |
| T4 | a temporary tree where `read/words.py` imports `pymupdf` | one violation |
| T5 | a temporary tree where `core/x.py` imports `numpy` | one violation (third party outside the table) |

---

## 4 · Packaging and tooling

- **`pyproject.toml`:**
  - build backend `uv_build>=0.12.19,<0.13`; `requires-python = ">=3.12"`;
  - `license = "MIT"` with `license-files = ["LICENSE"]`, and no license classifiers;
  - dependencies `pymupdf>=1.28.2,<2` and `pydantic>=2.11,<3`; Camelot and pypdfium2 are added by the
    milestones that use them;
  - dependency groups `test`, `lint`, `typecheck`, and `dev`;
  - `[project.scripts] inkgrid = "inkgrid.cli:main"`.
- **Lint:** Ruff 0.16, configured with `extend-select` (0.16's larger default rule set, plus the house
  additions).
- **Types:** `mypy --strict` on `src/`, with `mypy_path = "typings"`.
- **Tests:** pytest 9 with `strict = true`, `--import-mode=importlib`, `filterwarnings = ["error"]`,
  and `pythonpath = ["tests/support"]` so the fixture factory imports as `pdf_factory`. Coverage:
  branch coverage, a total floor of 80%, and a per-file floor of 80% enforced by
  `scripts/check_coverage_floors.py`.
- **`scripts/export_schemas.py`** writes `docs/schema/{reading,document}.schema.json`.
- **`scripts/dev.sh`** runs, in order: `uv sync`, `ruff check`, `ruff format --check`, `mypy`,
  `pytest`, and the coverage floors.
- **CI** (`.github/workflows/ci.yml`):
  - lint and type check;
  - tests on Ubuntu with Python 3.12, 3.13, and 3.14, on Windows with 3.12, and on macOS with 3.14;
  - a 3.15 job allowed to fail;
  - a build job that runs `uv build --no-sources` and smoke-tests the wheel and the sdist in isolated
    environments;
  - a `pip-audit` job over the locked dependencies.

  Actions are pinned by SHA, with `permissions: {}` by default. Dependabot covers `uv` and
  `github-actions`.
- **House skeleton:**
  - `README.md` in the house section order;
  - `WHY.md`;
  - `LICENSE` (MIT);
  - `CHANGELOG.md` (Keep a Changelog 1.1.0);
  - `CLAUDE.md`;
  - `.editorconfig`, `.gitignore`, `.env.example`;
  - `.github/pull_request_template.md`, with the Spec-TDD checklist;
  - `docs/ARCHITECTURE.md`, with a Mermaid diagram;
  - `docs/DEMO.md`.

  The README says plainly what works today (the page model) and claims no benchmark number (design
  § 11.3). Its Licensing section carries the PyMuPDF AGPL notice. The hero GIF waits for the M1
  inspector; the README says so instead of linking a missing file.

| # | case | expected |
|---|---|---|
| K1 | `uv build --no-sources` | a wheel and an sdist; the wheel contains `inkgrid/py.typed` |
| K2 | the wheel's `METADATA` | `License-Expression: MIT`, no `License ::` classifier, `Requires-Python: >=3.12` |
| K3 | `tests/smoke_test.py` in a fresh environment with only the wheel installed | builds a one-word PDF with pymupdf, reads it with `inkgrid.read_pages`, and asserts the word |
| K4 | `scripts/check_coverage_floors.py` on a report where one `src/` file is below 80% | exit 1 naming the file |
| K5 | `scripts/export_schemas.py` then `git diff --exit-code docs/schema` | no diff |
| K6 | `uv run pip-audit` against the locked environment | no known vulnerabilities (or a documented, justified exception) |

---

## 5 · M0 exit criteria (from `00-design.md` § 14)

- [ ] L1: `inkgrid words` prints a validated page model for every fixture.
- [ ] Every M0 case in `01-model.md`, `02-reader.md`, and this file passes locally on Python 3.12.
- [ ] Ruff, `ruff format --check`, `mypy --strict`, and the coverage floors are clean.
- [ ] K1–K3 pass on the built distributions.
- [ ] CI green on the matrix. This needs the GitHub repository, which is created and pushed only with
      the owner's go-ahead. Until then, every CI command runs locally, and the workflow is checked with
      `actionlint`.
