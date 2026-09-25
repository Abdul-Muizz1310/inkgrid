# M0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a typed, tested inkgrid package that reads any born-digital PDF into a validated page model
(`inkgrid words in.pdf`), with the full output contract (`Document`) defined and enforced, packaged
and CI-ready.

**Architecture:** frozen pydantic v2 models in `model/`, with invariants as validators. A PyMuPDF
adapter splits into pure word and rule builders over typed raw values plus one I/O module. A thin
`api.read_pages` and an argparse CLI sit on top. An `ast`-based test enforces the layer table.

**Tech Stack:** Python ≥ 3.12, uv 0.12.19 / uv_build, pymupdf 1.28.2, pydantic ≥ 2.11, pytest 9,
hypothesis, Ruff 0.16, mypy 2.3 `--strict`.

**Spec:** `docs/specs/00-design.md` (parent), `docs/specs/01-model.md`, `docs/specs/02-reader.md`,
`docs/specs/03-cli-and-packaging.md`. Case ids such as G7, W-4, or L1 refer to rows in those files'
test tables; each row becomes one test (or one parametrize entry) named `test_<id>_<slug>` that
asserts exactly the table's "expected" column.

## Global Constraints

- `requires-python = ">=3.12"`; build backend `uv_build>=0.12.19,<0.13`; `[tool.uv] required-version =
  ">=0.12.19,<0.13"`.
- Runtime dependencies are exactly `pymupdf>=1.28.2,<2` and `pydantic>=2.11,<3`.
- `license = "MIT"`, `license-files = ["LICENSE"]`, no `License ::` classifiers.
- Version `0.1.0.dev0`; import name `inkgrid`; distribution name `inkgrid`.
- Every model is a frozen pydantic model with `extra="forbid"`, `strict=True`,
  `serialize_by_alias=True`, `validate_by_name=True`, `validate_by_alias=True`. They share the base
  class `inkgrid.model.base.Frozen`.
- Coordinates go through `quantize` (0.01 pt) at construction; nothing else rounds them.
- Only `read/pymupdf_reader.py` imports `pymupdf`. `model/` imports only stdlib and pydantic.
- There are no relative imports (Ruff TID252) and no `# type: ignore` without an error code
  (`ignore-without-code`).
- Commits follow Conventional Commits, imperative mood, subject ≤ 72 characters, no emoji, and **no
  `Co-Authored-By` trailer**.
- Docs prose is American English, active voice, and avoids "simply", "just", "easy", "obviously", and
  "basically".

## Review Focus

1. **Non-ASCII text on a non-UTF-8 console.** Printing `Reading` JSON that holds `€0.13` or `Zürich`
   where `sys.stdout.encoding` is cp1252 must still write valid UTF-8. The CLI writes bytes to
   `sys.stdout.buffer`. Task 12 adds `test_cli_writes_utf8_on_cp1252_console`.
2. **The password line ending on stdin.** `--password-stdin` given `"pw\r\n"`, `"pw\n"`, or `"pw"` must
   use `pw`, stripping only the line ending, never inner spaces. Task 12 adds
   `test_password_stdin_strips_only_line_ending`.
3. **A non-seekable binary stream.** A pipe-like object whose `read()` returns bytes but that cannot
   `seek` must load. Task 6 adds `test_load_source_nonseekable_stream`.
4. **Subset-prefixed font names.** `ABCDEF+Arial-BoldMT` and `XYZABC+TimesNewRomanPS-ItalicMT` must set
   `bold` and `italic`. Task 7 adds these to the W-15 parametrization.
5. **A path with spaces and non-ASCII characters.** `tmp_path / "fee schedule Zürich.pdf"` must read,
   with `file_name` preserved exactly. Task 6 adds `test_load_source_unicode_path`.

---

## File Structure

```
pyproject.toml, uv.lock, .python-version (3.12), .gitignore, .editorconfig, .env.example
LICENSE, README.md, WHY.md, CHANGELOG.md, CLAUDE.md
.github/workflows/ci.yml, .github/dependabot.yml, .github/pull_request_template.md
docs/ARCHITECTURE.md, docs/DEMO.md, docs/schema/{reading,document}.schema.json
scripts/dev.sh, scripts/check_coverage_floors.py, scripts/export_schemas.py
typings/pymupdf/__init__.pyi              local stub: only what read/pymupdf_reader.py calls
src/inkgrid/__init__.py                   re-exports, __version__, __all__
src/inkgrid/__main__.py                   python -m inkgrid
src/inkgrid/py.typed
src/inkgrid/errors.py                     InkgridError tree
src/inkgrid/api.py                        read_pages
src/inkgrid/cli.py                        argparse; words subcommand
src/inkgrid/model/__init__.py             re-exports of the model
src/inkgrid/model/base.py                 Frozen (shared ConfigDict), Coord type
src/inkgrid/model/geometry.py             quantize, Rect, Interval
src/inkgrid/model/canonical.py            normalize_ws, content_key, assign_keys, sha256_hex
src/inkgrid/model/findings.py             Severity, FindingCode, SEVERITY, Finding
src/inkgrid/model/page.py                 Word, Rule, PageInfo, PageModel, Source, ReaderInfo, Reading
src/inkgrid/model/document.py             Region, block kinds, Grid, Cell, Link, Ledger, Producer, Document
src/inkgrid/model/invariants.py           cross-object checks Document's validator calls
src/inkgrid/read/__init__.py              empty
src/inkgrid/read/source.py                SourceLike, Loaded, load_source
src/inkgrid/read/raw.py                   RawChar/RawSpan/RawLine, path items, RawPath
src/inkgrid/read/words.py                 WordsOut, build_words (pure)
src/inkgrid/read/rules.py                 extract_rules (pure)
src/inkgrid/read/page_findings.py         page_findings, engine_warning_findings (pure)
src/inkgrid/read/pymupdf_reader.py        read_pdf (I/O)
tests/support/pdf_factory.py              synthetic PDF fixtures (imported as pdf_factory)
tests/support/doc_builder.py              builds valid Documents for contract tests
tests/test_*.py                           one file per module under test
tests/smoke_test.py                       installed-wheel smoke test (not collected)
```

---

### Task 1: Package skeleton, errors, version, coverage-floor script

**Files:**
- Create: `pyproject.toml`, `.python-version`, `.gitignore`, `.editorconfig`, `LICENSE`,
  `src/inkgrid/__init__.py`, `src/inkgrid/py.typed`, `src/inkgrid/errors.py`,
  `scripts/check_coverage_floors.py`, `scripts/dev.sh`
- Test: `tests/test_errors.py`, `tests/test_coverage_floors.py`

**Interfaces:**
- Produces:
  - `inkgrid.errors.InkgridError(Exception)`;
  - under it `PdfOpenError`, `PasswordRequired`, `WrongPassword`, `InvariantError`, and
    `StrictModeError`;
  - `inkgrid.__version__: str`;
  - `scripts/check_coverage_floors.py::main(report: Path = Path("coverage.json")) -> int` (0 ok, 1
    under floor, 2 without branch data).

- [ ] **Step 1: Write `pyproject.toml`.**
  - Start from the validated skeleton: `[project]` metadata, dependencies and dependency groups
    (`test`: pytest ≥ 9.1.1, pytest-cov ≥ 7.1.0, coverage ≥ 7.16.1, hypothesis ≥ 6.168.1; `lint`: ruff ≥
    0.16.9; `typecheck`: mypy ≥ 2.3.1; `dev` includes all three).
  - Tool config: Ruff with `extend-select` as in the skeleton; mypy strict with `mypy_path = "typings"`
    and `files = ["src"]`; pytest native `[tool.pytest]` with `strict = true`, importlib mode,
    `pythonpath = ["tests/support"]`, `filterwarnings = ["error"]`, `addopts` with bare `--cov`,
    `--cov-branch`, and `--cov-report=json`; coverage `source_pkgs = ["inkgrid"]` and
    `fail_under = 80`.
  - `[project.scripts] inkgrid = "inkgrid.cli:main"` is added in Task 12, not here: an entry point to
    a missing module breaks install.
- [ ] **Step 2: Write the failing tests.**
  - `test_A3_every_error_subclasses_inkgrid_error`: for each class, `issubclass(cls, InkgridError)` and
    not `issubclass(cls, (ValueError, OSError))`.
  - `test_A4_version_matches_metadata`: `inkgrid.__version__ == importlib.metadata.version("inkgrid")
    == "0.1.0.dev0"`.
  - `test_K4_floor_script_flags_file_below_floor`: load the script with `importlib.util`, write a
    `coverage.json` holding `meta.branch_coverage = true` and one `src/inkgrid/x.py` at 79.9, and
    assert `main(path) == 1`. At 80.0, `0`. With `branch_coverage = false`, `2`.
- [ ] **Step 3: Run** `uv sync --all-groups && uv run pytest -q`. Expected: the new tests FAIL
  (import errors).
- [ ] **Step 4: Implement `errors.py`**, one-line docstrings per class, and set
  `__version__ = importlib.metadata.version("inkgrid")` in `__init__.py`. Copy the coverage script
  from the validated skeleton, with `DEFAULT_FLOOR = 80.0`.
- [ ] **Step 5: Run** `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv
  run mypy`. Expected: all PASS.
- [ ] **Step 6: Commit** `build: scaffold the inkgrid package and error types`.

### Task 2: Geometry

**Files:**
- Create: `src/inkgrid/model/__init__.py`, `src/inkgrid/model/base.py`, `src/inkgrid/model/geometry.py`
- Test: `tests/test_geometry.py`

**Interfaces:**
- Produces:
  - `quantize(value: float) -> float`;
  - `Coord = Annotated[float, AfterValidator(quantize)]` (in `base.py`);
  - `Frozen(BaseModel)`, with the ConfigDict from Global Constraints;
  - `@dataclass(frozen=True, slots=True) class Rect(x0, y0, x1, y1: float)`, with `width`, `height`,
    `area`, `center: tuple[float, float]`, `contains_point(x, y) -> bool`,
    `contains_rect(other) -> bool`, `intersects(other) -> bool`, `union(other) -> Rect`, and
    `classmethod union_all(rects: Iterable[Rect]) -> Rect`;
  - `@dataclass(frozen=True, slots=True) class Interval(start, end: float)`, with `width`,
    `contains(v) -> bool`, and `overlaps(other) -> bool`.

  Both dataclasses implement `__get_pydantic_core_schema__`: a JSON array of 4 (or 2) numbers in and
  out, and an instance or tuple accepted in Python.

- [ ] **Step 1: Write the failing tests.**
  - One test per row G1–G21.
  - G5 and G13 are Hypothesis properties:
    - G5: `floats(-1e6, 1e6, allow_nan=False)`.
    - G13: random sorted cut lists over `[0, W)`, tested with the points
      `floats(0, W, exclude_max=True)` × `floats(0, H, exclude_max=True)`. Count
      `sum(r.contains_point(x, y) for r in tiles) == 1`, and quantize both the cuts and the points
      first.
  - G17 and G18 use `TypeAdapter(Rect)`.
- [ ] **Step 2: Run** `uv run pytest tests/test_geometry.py -q`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement `geometry.py` and `base.py`.**
  - `__post_init__` quantizes through `object.__setattr__`, then checks the ordering.
  - The core schema is `json_or_python_schema(json_schema=<tuple of 4 floats → Rect>,
    python_schema=union(is_instance(Rect), <tuple → Rect>))`, serializing to a list.
- [ ] **Step 4: Run** the tests plus `ruff` and `mypy`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(model): add quantized Rect and Interval geometry`.

### Task 3: Canonical helpers and findings

**Files:**
- Create: `src/inkgrid/model/canonical.py`, `src/inkgrid/model/findings.py`
- Test: `tests/test_canonical.py`, `tests/test_findings.py`

**Interfaces:**
- Produces:
  - `normalize_ws(text: str) -> str`, `content_key(kind: str, text: str) -> str`,
    `assign_keys(items: Sequence[tuple[str, str]]) -> tuple[str, ...]`, and
    `sha256_hex(data: bytes) -> str`;
  - `class Severity(StrEnum)` and `class FindingCode(StrEnum)`, with the 13 codes of `01-model.md` § 3
    in that order;
  - `SEVERITY: Final[Mapping[FindingCode, Severity]]`, a `MappingProxyType`;
  - `class Finding(Frozen)` with `code`, `severity`, `page: PositiveInt | None`, `block: str | None`
    (pattern `^b[1-9][0-9]*$`), and `detail: str`;
  - `classmethod Finding.of(code, detail, *, page=None, block=None) -> Finding`.

- [ ] **Step 1: Write the failing tests** C1–C6 and F1–F4.
  - C6 asserts `sha256_hex(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"`.
  - F1 iterates `FindingCode` and asserts `set(SEVERITY) == set(FindingCode)`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement.** `Finding` gets an `@model_validator(mode="after")` that compares against
  `SEVERITY`.
- [ ] **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit** `feat(model): add content keys and the closed finding codes`.

### Task 4: Page model, Reading, schema export

**Files:**
- Create: `src/inkgrid/model/page.py`, `scripts/export_schemas.py`, `docs/schema/reading.schema.json`
- Test: `tests/test_page_model.py`, `tests/test_schemas.py`

**Interfaces:**
- Consumes: `Rect`, `Coord`, `Frozen`, and `Finding` (Tasks 2–3).
- Produces:
  - `Word(id, page, bbox, text, size, font, bold, italic, superscript, hidden, horizontal)`;
  - `Rule(page, axis: Literal["h","v"], at, start, end, thickness)`, with `.length` and `.rect`;
  - `PageInfo(number, width, height, rotation: Literal[0, 90, 180, 270], text_layer:
    Literal["full","partial","none"], invisible_chars, clipped_chars, unmapped_chars, hidden_chars,
    image_area_ratio)`;
  - `PageModel(PageInfo)`, adding `words: tuple[Word, ...]` and `rules: tuple[Rule, ...]`;
  - `Source(sha256, pages, file_name)`, `ReaderInfo(inkgrid, pymupdf, mupdf)`;
  - `Reading(schema_version: Literal["inkgrid.reading/1"] = …, alias "schema"; source; reader; pages:
    tuple[PageModel, ...]; findings: tuple[Finding, ...])`, with `.words() -> Iterator[Word]`;
  - `scripts/export_schemas.py::schemas() -> dict[str, dict[str, object]]`, a file name → schema map,
    and `main() -> int`, which writes them with `json.dumps(s, indent=2, sort_keys=True) + "\n"`.

- [ ] **Step 1: Write the failing tests** P1–P16.
  - P15 is a Hypothesis property. A composite strategy builds 1–3 pages of 0–5 words each (ids dense,
    text from `text(alphabet=characters(categories=["L","N"]), min_size=1)`) and asserts
    `Reading.model_validate_json(r.model_dump_json()) == r`, with `r.model_dump_json()` byte-identical
    after a second round trip.
  - `test_P16_reading_schema_is_committed` compares `schemas()["reading.schema.json"]` with the parsed
    committed file.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement `page.py`.** The word-text rule is a field validator: non-empty, with no
  character where `c.isspace()` or `unicodedata.category(c) in {"Cc","Cf","Co","Cn"}`. Then run
  `uv run python scripts/export_schemas.py` to create `docs/schema/reading.schema.json`.
- [ ] **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit** `feat(model): add the page model and the Reading contract`.

### Task 5: The document contract

**Files:**
- Create: `src/inkgrid/model/document.py`, `src/inkgrid/model/invariants.py`,
  `tests/support/doc_builder.py`, `docs/schema/document.schema.json`
- Modify: `scripts/export_schemas.py` (add the document schema), `src/inkgrid/model/__init__.py`
- Test: `tests/test_document.py`

**Interfaces:**
- Consumes: Tasks 2–4.
- Produces:
  - `Region(page, bbox)`;
  - `BlockBase(id, key, regions, word_ids, text, markers, hyphen_joins)`, and the block kinds
    `Heading(level, number)`, `Paragraph`, `ListItem(label)`, `Footnote(label)`,
    `Definition(term, body)`, `Table(grid)`, and `Furniture(role)`, each with
    `kind: Literal[...]`;
  - `Block`, the discriminated union on `kind`;
  - `Grid(n_rows, n_cols, row_bands, col_bands, header_rows, banner_rows, source, cells)`, with
    `.cell_rect(cell) -> Rect`;
  - `Cell(row, col, row_span, col_span, text, word_ids, carried, markers)`;
  - `LinkEnd(block, cell)`;
  - `Link(kind, from_ alias "from", to, label, method, status, reason)`;
  - `Ledger(content_chars, furniture_chars, invisible_chars, clipped_chars, partition:
    Literal["proved"])`;
  - `Producer(inkgrid, pymupdf, mupdf, camelot, pypdfium2, lexicon, profile, lattice)`;
  - `Document(schema_version alias "schema", source, producer, pages: tuple[PageInfo, ...], words,
    blocks, links, findings, ledger)`, with `.complete -> bool` and `.tables() -> tuple[Table, ...]`;
  - `tests/support/doc_builder.py`: `words_line(texts, *, page=1, y=100.0, x=72.0) ->
    list[Word]` (10 pt boxes, 5 pt gaps, ids assigned later) and `build_document(pages: int, blocks:
    Sequence[BlockSpec], links=(), findings=()) -> Document`.
    - A `BlockSpec` holds the kind, the words, and any kind fields.
    - The builder assigns word ids, block ids, keys, regions, text (words joined by a single space)
      and the ledger, so a failure test can take a valid spec and break one field through
      `model_copy(update=…)`, or pass raw keyword arguments to `Document`.

  The check placement follows `01-model.md` § 5:
  - **The `Grid` validator** checks invariants 11–13, plus the shape of carried cells (text
    non-empty, no words).
  - **The `Table` validator** checks invariants 10 and 14 (the union and disjointness of cell word
    sets).
  - **The `BlockBase` validator** checks unique, non-empty `word_ids`; the whitespace shape of
    `text`; joins distinct and inside the block; and region pages strictly increasing.
  - **`Document`'s `model_validator`** calls `invariants.check_document(doc) -> None`, which raises
    `ValueError` for invariants 1–9 and 15–23. It imports `Document` only under `TYPE_CHECKING`.

- [ ] **Step 1: Write `doc_builder.py` and the failing tests** D1–D33.
  - D2 and D3 assert that the error message contains the word id (for example `"word 1"`).
  - D33 is a property test. A random partition of `n ≤ 12` single-letter words into paragraphs must
    validate; the same partition with one word id appended to a second block must raise.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement `document.py` and `invariants.py`.**
  - The character check is a helper over `collections.Counter`:

    ```python
    def text_matches_words(text: str, word_texts: Sequence[str], joins: int) -> bool:
        want = Counter("".join(word_texts))
        want["-"] -= joins
        return want["-"] >= 0 and +want == Counter(c for c in text if c not in " \n")
    ```

  - Regenerate the schemas.
- [ ] **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit** `feat(model): define the Document contract and its invariants`.

### Task 6: Source loading

**Files:**
- Create: `src/inkgrid/read/__init__.py`, `src/inkgrid/read/source.py`
- Test: `tests/test_source.py`

**Interfaces:**
- Produces:
  - `SourceLike = str | os.PathLike[str] | bytes | bytearray | memoryview | BinaryIO`;
  - `@dataclass(frozen=True, slots=True) class Loaded(data: bytes, file_name: str | None)`;
  - `load_source(source: SourceLike) -> Loaded`.

- [ ] **Step 1: Write the failing tests** S1–S6, plus the Review Focus tests
  `test_load_source_nonseekable_stream` (a `RawIOBase` subclass whose `seekable()` returns False and
  whose `readinto` serves the bytes in 7-byte chunks) and `test_load_source_unicode_path`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - A path goes through `Path(source).read_bytes()`, with `OSError` → `PdfOpenError(f"cannot read
    {path}: {exc.strerror}") from exc`.
  - An object with `read` must return `bytes`, else `TypeError`.
  - Any other type raises `TypeError`.
  - Empty data raises `PdfOpenError("empty input")`.
- [ ] **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit** `feat(read): normalize PDF input sources`.

### Task 7: Raw types and the word builder

**Files:**
- Create: `src/inkgrid/read/raw.py`, `src/inkgrid/read/words.py`
- Test: `tests/test_words.py`

**Interfaces:**
- Produces:
  - `Box = tuple[float, float, float, float]`;
  - `@dataclass(frozen=True, slots=True) class RawChar(c: str, bbox: Box)`;
  - `RawSpan(font: str, size: float, flags: int, char_flags: int, chars: tuple[RawChar, ...])`;
  - `RawLine(direction: tuple[float, float], spans: tuple[RawSpan, ...])`;
  - `WordsOut(words: tuple[Word, ...], invisible_chars: int, unmapped_chars: int, hidden_chars: int)`;
  - `build_words(lines: Sequence[RawLine], page: int, first_id: int) -> WordsOut`.

  The constants live in `words.py`:

  ```python
  JOIN_GAP_MAX = 0.6
  JOIN_GAP_MIN = -1.0
  JOIN_OVERLAP = 0.3
  SUPERSCRIPT = 1
  ITALIC = 2
  BOLD = 16
  CHAR_BOLD = 8
  CHAR_FILLED = 16
  CHAR_STROKED = 32
  ```

- [ ] **Step 1: Write the failing tests** W-1 to W-17. A local helper
  `span(text, x0, *, y0=100, h=10, w=5, flags=0, char_flags=16, font="Helvetica", size=10)` lays out
  one 5 pt-wide box per character. W-15's parametrization includes the two subset-prefixed names from
  Review Focus item 4. W-17 is a Hypothesis property over `lists(sampled_from("ab \t"))` split into
  random spans.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement `build_words`.** It walks lines, then spans, then characters, keeping an
  "open token" per span; this is the W3 join. The dominant-span rule is W4. A `Word` is built only at
  the end of a token, with `Rect(*union_box)`, so quantization happens once.
- [ ] **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit** `feat(read): build words from characters, splitting superscripts`.

### Task 8: Rule extraction

**Files:**
- Modify: `src/inkgrid/read/raw.py`, adding the path types
- Create: `src/inkgrid/read/rules.py`
- Test: `tests/test_rules.py`

**Interfaces:**
- Produces:
  - `Point = tuple[float, float]`;
  - the path items `LineItem(p: Point, q: Point)`, `RectItem(rect: Box)`,
    `QuadItem(corners: tuple[Point, Point, Point, Point])`, and `CurveItem()`;
  - `PathItem`, their union;
  - `RawPath(kind: str, width: float | None, color: tuple[float, ...] | None, stroke_opacity:
    float | None, fill: tuple[float, ...] | None, fill_opacity: float | None, items:
    tuple[PathItem, ...])`;
  - `extract_rules(paths: Sequence[RawPath], page: int) -> tuple[Rule, ...]`.

  The constants are `SLANT_MAX = 0.5`, `MIN_LENGTH = 2.0`, `THIN_MAX = 2.5`, and
  `QUAD_AXIS_TOL = 0.5`.

- [ ] **Step 1: Write the failing tests** R-1 to R-14. R-5 asserts the exact four rules:

  ```python
  Rule(page=1, axis="h", at=200, start=200, end=300, thickness=1)
  Rule(page=1, axis="h", at=260, start=200, end=300, thickness=1)
  Rule(page=1, axis="v", at=200, start=200, end=260, thickness=1)
  Rule(page=1, axis="v", at=300, start=200, end=260, thickness=1)
  ```

- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement** R1–R4. De-duplicate with a dict keyed by `(axis, at, start, end)`, holding
  the greatest thickness, then sort.
- [ ] **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit** `feat(read): extract drawn rules from vector paths`.

### Task 9: PDF fixture factory, PyMuPDF stubs, opening and quiet reads

**Files:**
- Create: `tests/support/pdf_factory.py`, `typings/pymupdf/__init__.pyi`,
  `src/inkgrid/read/page_findings.py`, `src/inkgrid/read/pymupdf_reader.py`
- Test: `tests/test_page_findings.py`, `tests/test_reader_open.py`

**Interfaces:**
- Consumes: Tasks 3–8.
- Produces:
  - `read_pdf(data: bytes, *, file_name: str | None, password: str | None) -> Reading`;
  - `page_findings(page: PageModel, *, has_image: bool, has_curves: bool) -> tuple[Finding, ...]`;
  - `engine_warning_findings(messages: Sequence[str]) -> tuple[Finding, ...]`, for 20 distinct lines
    at most plus one "N more" finding;
  - `pdf_factory`: one function per fixture, each returning `bytes`:
    - text and superscripts: `simple_text()`, `superscript()`, `font_change()`;
    - visibility and layers: `hidden_text()`, `ocr_layer()`, `image_only()`, `blank()`,
      `line_only()`, `clipped_text()`, `unmapped_glyph()`;
    - geometry: `ruled_table()`, `rotated()`, `offset_mediabox()`, `cropbox()`, `multipage(n=3)`;
    - encryption: `encrypted(user_pw="u", owner_pw="o")`, `owner_only()`;
    - damaged files: `repaired()` (a valid PDF whose `startxref` offset is corrupted), `zero_pages()`
      (hand-written bytes, `/Count 0`);
    - `OPENABLE: dict[str, Callable[[], bytes]]`, every fixture that opens without a password (used by
      L1).

  Every fixture is deterministic: fixed geometry and text, `garbage=0`, and no timestamps
  (`doc.set_metadata({})` before `tobytes()`).

- [ ] **Step 1: Write the failing tests.**
  - O1–O10.
  - The `page_findings` cases, one per rule in `02-reader.md` § 6: no words with an image →
    `no_text_layer`; no words and nothing drawn → `blank_page`; `unmapped_chars=2` →
    `partial_text_layer`; hidden 60% with image ratio 0.9 → `ocr_text_layer`; hidden 60% with image
    ratio 0.2 → `hidden_text`; clipped → `clipped_text`; the fixed finding order.
  - `engine_warning_findings`: 25 distinct lines → 21 findings, the last reading `"5 more"`; duplicate
    lines appear once.
  - O4 uses `capfd` and asserts `capfd.readouterr() == ("", "")`.
  - O9 records `pymupdf.TOOLS.mupdf_display_errors()` before and after.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - Write the `typings/pymupdf/__init__.pyi` stub with `TypedDict`s for the measured `rawdict`,
    drawing, and image-info shapes (`NotRequired` for `lines` on image blocks), and overloads of
    `Page.get_text` for `"rawdict"` and `"text"`.
  - Implement `read_pdf`: a `_quiet()` context manager (save the display settings, set them off,
    reset the warnings, yield the collected warnings, restore in `finally`), then open, check
    encryption, and read the pages.
  - The page conversion is minimal here: words, rules, and geometry, enough for the O-cases. Task 10
    adds the measurements.
- [ ] **Step 4: Run** the tests, plus `uv run mypy` (the stub must type-check the reader with no
  `Any` leaks). Expected: PASS.
- [ ] **Step 5: Commit** `feat(read): open PDFs quietly and map failures to typed errors`.

### Task 10: Page measurements and integration fixtures

**Files:**
- Modify: `src/inkgrid/read/pymupdf_reader.py`
- Test: `tests/test_reader_pages.py`

**Interfaces:**
- Consumes: Task 9 (`read_pdf`, `pdf_factory`, `page_findings`).
- Produces: a complete `PageModel` per page:
  - `image_area_ratio`, from `get_image_info()`;
  - `clipped_chars`, from the difference of two `get_text("text")` calls;
  - `invisible_chars`, `unmapped_chars`, and `hidden_chars`, from `WordsOut`;
  - `text_layer`, set by the rules in `01-model.md` § 4;
  - the page findings, and the engine warnings appended at the document level.

- [ ] **Step 1: Write the failing tests** X1–X16, each reading a factory fixture through `read_pdf`.
  - X11 asserts the exact rule tuple the fixture documents; `ruled_table()` also exposes
    `RULED_TABLE_RULES`.
  - X12 asserts `(page.width, page.height, page.rotation) == (612.0, 792.0, 90)`.
  - X13 asserts the word `Offset` has `bbox.x0 == 172.0`.
  - X14 asserts `(500.0, 700.0)` and the word at `x0 == 50.0`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement the measurements.** A curve item (`"c"`) anywhere in the page's drawings sets
  `has_curves`.
- [ ] **Step 4: Run** the whole suite. Expected: PASS.
- [ ] **Step 5: Commit** `feat(read): measure hidden, clipped, and unmapped text per page`.

### Task 11: Public API and the architecture test

**Files:**
- Create: `src/inkgrid/api.py`
- Modify: `src/inkgrid/__init__.py`
- Test: `tests/test_api.py`, `tests/test_architecture.py`

**Interfaces:**
- Consumes: `load_source` (Task 6) and `read_pdf` (Task 9).
- Produces:
  - `inkgrid.read_pages(source: SourceLike, *, password: str | None = None) -> Reading`;
  - `inkgrid.__all__`, as `03-cli-and-packaging.md` § 1 lists it;
  - in `tests/test_architecture.py`, `violations(root: Path) -> list[str]` over the layer table in § 3
    of that spec.

- [ ] **Step 1: Write the failing tests.**
  - A1 and A2.
  - T1: `violations(Path("src/inkgrid")) == []`.
  - T2–T5 each write a small tree under `tmp_path/"inkgrid"` and assert exactly one violation naming
    the file.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - `api.read_pages` is `loaded = load_source(source); return read_pdf(loaded.data,
    file_name=loaded.file_name, password=password)`.
  - `violations` maps each file to its layer by its first path segment under `inkgrid/`. It collects
    `Import` and `ImportFrom` targets, classifies each as stdlib (`sys.stdlib_module_names` or
    `__future__`), internal (`inkgrid.<layer>`), or third party, and checks the table plus the `read/`
    rule.
- [ ] **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit** `feat: expose read_pages and enforce the layer table in tests`.

### Task 12: The `inkgrid words` CLI

**Files:**
- Create: `src/inkgrid/cli.py`, `src/inkgrid/__main__.py`
- Modify: `pyproject.toml` (add `[project.scripts] inkgrid = "inkgrid.cli:main"`)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `inkgrid.api.read_pages` (Task 11) and `pdf_factory.OPENABLE` (Task 9).
- Produces: `inkgrid.cli.main(argv: Sequence[str] | None = None) -> int`.

- [ ] **Step 1: Write the failing tests.**
  - L1 is parametrized over `pdf_factory.OPENABLE`. Write each fixture to `tmp_path`, call
    `main(["words", str(p)])` with stdout captured as bytes (`capsysbinary`), and assert exit 0 and
    that `Reading.model_validate_json(out)` succeeds.
  - L2–L8.
  - L9 runs `subprocess.run([sys.executable, "-m", "inkgrid", "words", p])`.
  - The Review Focus tests `test_cli_writes_utf8_on_cp1252_console` and
    `test_password_stdin_strips_only_line_ending`. The former monkeypatches `sys.stdout` with an
    `io.TextIOWrapper(io.BytesIO(), encoding="cp1252")` and asserts the buffer holds the UTF-8 bytes of
    `€`, using a fixture with the text `€0.13`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement** `main` with argparse subparsers.
  - Output is `sys.stdout.buffer.write(data)`, where `data = reading.model_dump_json().encode()` (or
    `model_dump_json(indent=2)` with `--pretty`), plus a trailing newline.
  - `InkgridError` subclasses print `inkgrid: <message>` to stderr and return 2.
  - `--password-stdin` reads `sys.stdin.readline()` and removes one trailing `"\r\n"` or `"\n"`.
- [ ] **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit** `feat(cli): add inkgrid words to print the page model`.

### Task 13: CI, distribution checks, and the house documents

**Files:**
- Create:
  - `.github/workflows/ci.yml`, `.github/dependabot.yml`, `.github/pull_request_template.md`;
  - `tests/smoke_test.py`, `.env.example`;
  - `README.md`, `WHY.md`, `CHANGELOG.md`, `CLAUDE.md`;
  - `docs/ARCHITECTURE.md`, `docs/DEMO.md`.
- Test: `tests/test_distribution.py`, marked `slow`. It runs `uv build --no-sources` into `tmp_path`.

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Write the failing tests.** The `slow` marker is registered in `pyproject.toml`; the CI
  build job runs it.
  - `test_K1_wheel_contains_py_typed`.
  - `test_K2_wheel_metadata`: parse `METADATA` with `email.parser`. Assert `License-Expression ==
    "MIT"`, that no classifier starts with `License ::`, and `Requires-Python == ">=3.12"`.
  - `test_K3_smoke_test_passes_in_isolated_env`: run `uv run --isolated --no-project --with <wheel>
    tests/smoke_test.py` and assert returncode 0 and `"smoke test passed"`.
  - `test_K5_schemas_are_current` already exists from Task 4; keep it.
- [ ] **Step 2: Run** `uv run pytest -m slow -q`. Expected: FAIL (no smoke test yet).
- [ ] **Step 3: Write `tests/smoke_test.py`, the workflow files, and the documents.**
  - `smoke_test.py` builds a one-word PDF with pymupdf in memory and calls `inkgrid.read_pages`.
  - `ci.yml` follows the validated skeleton, adding a `pip-audit` job:

    ```
    uv export --frozen --no-emit-project --format requirements.txt > requirements.txt
    uvx pip-audit --strict -r requirements.txt
    ```

  - The README follows the house order. Its sections: status (M0: the page model; the roadmap links to
    design § 14); "Benchmarks: none yet, the benchmark runs in M5"; Licensing with the PyMuPDF AGPL
    notice from design § 13.
  - `WHY.md` is three first-person paragraphs, about 200 words.
  - `CLAUDE.md` holds the non-negotiables, the commands, and the layer table.
- [ ] **Step 4: Run** the M0 exit checks:
  - `scripts/dev.sh`;
  - `uv run pytest -m slow -q`;
  - `uvx --from actionlint-py actionlint`;
  - the `pip-audit` commands above.

  Expected: all PASS. A pip-audit finding in a transitive dependency gets an `--ignore-vuln` entry
  with a comment only if it cannot be fixed by a constraint.
- [ ] **Step 5: Commit** `ci: add the test matrix, build smoke test, and house documents`.

---

## After the tasks

A fresh reviewer checks the whole M0 branch against the three specs. Its findings are fixed or
ledgered. Then the branch fast-forwards into `main`. Creating the GitHub repository and pushing, which
is the only way to see CI green, waits for the owner's go-ahead.
