# 05 · `inkgrid.read`, strict mode, Markdown, the CLI, and the inspector (M1)

**Implements:** `00-design.md` § 7 (API and CLI), § 9 (strict mode), and the M1 exit criteria.
**Modules:**
- `api.py`: `read`;
- `model/export.py`: the pure Markdown formatters, used by `Document.to_markdown()`;
- `cli.py`: `inkgrid read`;
- `read/pymupdf_reader.py`: `render_pages`;
- `render/inspector.py`: the HTML inspector.

---

## 1 · `inkgrid.read`

```python
doc = inkgrid.read(source, *, password=None, lexicon=Lexicon.default(),
                   profile=Profile.default(), lattice="combined", strict=False)   # -> Document
```

- It runs `read_pages`, then `build_document` (`04-text-pipeline.md` § 6).
- **Arguments are checked before any reading.** These are programming errors, not bad input:
  - a `lexicon` that is not a `Lexicon`, or a `profile` that is not a `Profile`, raises `TypeError`;
  - an instance that fails revalidation (one built with `model_copy(update=…)`, which skips
    validation) raises pydantic's `ValidationError`;
  - a `lattice` other than `combined` or `raster` raises `ValueError`.
- `lattice` is recorded in `Producer.lattice` now and used from M2.
- **`strict=True`:** when the document carries an error-severity finding, `read` raises
  `StrictModeError`, whose message names the codes and pages. The document is never returned
  half-trusted.
- Errors are the same as `read_pages`'s, plus `StrictModeError`, plus `InvariantError` for a bug.
- `inkgrid.read`, `inkgrid.Profile`, and `inkgrid.Lexicon` are re-exported from the package root.

| # | case | expected |
|---|---|---|
| RD1 | `read(fixture)` for every `OPENABLE` fixture | a valid `Document` (M1 exit criterion) |
| RD2 | the two-column fixture | the left column's blocks, then the right column's |
| RD3 | `read(image_only(), strict=True)` | `StrictModeError` naming `no_text_layer` and page 1 |
| RD4 | `read(image_only())` | a `Document` whose `complete` is False and which has no blocks |
| RD5 | `read(x, lattice="fast")` | `ValueError` |
| RD6 | `read(x, profile=Profile(id="custom/1", paragraph_gap_ratio=2.0))` | `producer.profile == "custom/1"` |
| RD7 | reading the same bytes twice | byte-identical `model_dump_json()` |
| RD8 | `read(x, profile=Profile().model_copy(update={"paragraph_gap_ratio": -1.0}))` | `ValidationError` |
| RD9 | `read(x, profile={"id": "p/1"})`; `read(x, lexicon="generic/1")` | `TypeError` |
| RD10 | a `Document` from `read` dumped and parsed back with `Document.model_validate_json` | equal, and every invariant re-checked |

---

## 2 · Markdown (`model/export.py`, pure)

`Document.to_markdown() -> str`. The dispatch over block kinds lives in `model/document.py`, and
the formatting in `model/export.py`, which imports nothing from `document.py`, so the method adds no
import cycle.

- **Each block kind has a fixed form:**
  - heading: `#` × min(level, 6), a space, then the text;
  - paragraph: its text, escaped (below);
  - list item: `- ` + the text without its label when the label is a bullet (one character: bullets
    are single characters and enumerators never are). An enumerated label is kept, and the text is
    written as printed, so the numbering reads as printed;
  - footnote: `[^label]:`, then a space and the text without its first word, when there is more;
  - definition: `**term** body`;
  - table: its text, one line per row, until M2 adds grids;
  - furniture: omitted.
- **Layout:** blocks are separated by one blank line, the output ends with one newline, and page
  breaks are not marked. A document with no rendered block is `""`.
- **Escaping.** Printed text must not turn into Markdown structure:
  - the opening of a paragraph, of a bullet item's text after its bullet, and of a footnote's text
    after its label gets a backslash before a leading `#`, `>`, `-`, `+`, or `*`, and before the
    `.` or `)` after leading digits;
  - a `<` that would open an HTML tag (followed by a letter, `/`, `!`, or `?`) becomes `\<`, in
    every block;
  - other inline markup (`*`, `_`, `[`, backticks) passes through as printed, so text that looks
    like emphasis can render as emphasis. The JSON is the canonical text; Markdown is a view of it.

| # | case | expected |
|---|---|---|
| MD1 | a heading level 2, a paragraph, a `•` list item, a `1.` list item, a footnote `3`, and a footer | `## Title\n\nText\n\n- item\n\n1. first\n\n[^3]: note\n` |
| MD2 | a paragraph `# of trades`; `- 5 bp`; `2026. A year` | `\# of trades`; `\- 5 bp`; `2026\. A year` |
| MD3 | a document with only furniture | `""` |
| MD4 | a heading of level 9 | six `#` |
| MD5 | a definition `Member` / `a firm admitted to trading` | `**Member** a firm admitted to trading\n` |
| MD7 | a `•` item `# of trades`; a footnote `3 - see below`; a paragraph `Use <script> here`; a heading `Fees <b>` | `- \# of trades`; `[^3]: \- see below`; `Use \<script> here`; `## Fees \<b>` |
| MD6 | a 2 × 2 table `Fee 0.10` / `Rebate 0.20` | `Fee 0.10\nRebate 0.20\n` |

---

## 3 · CLI: `inkgrid read`

```
inkgrid read IN.pdf [-o OUT.json] [--pretty] [--markdown OUT.md] [--inspector OUT.html]
                    [--strict] [--password-stdin]
```

- It prints the `Document` JSON to stdout, or writes it to `-o`.
- `--markdown` and `--inspector` write their files in addition.
- **Exit codes:**
  - 0: success;
  - 1: `--strict` and the document carries an error-severity finding. Every requested output is
    still written, so the evidence is not lost, and stderr names the findings;
  - 2: usage errors and unreadable input, as for `words`, including an output file that cannot be
    written.
- Output is UTF-8 bytes, and a closed pipe ends output quietly, as for `words`.

| # | case | expected |
|---|---|---|
| CR1 | `inkgrid read` for every `OPENABLE` fixture | exit 0; stdout parses as a `Document` |
| CR2 | `--markdown out.md --inspector out.html -o out.json` | all three files; nothing on stdout |
| CR3 | `--strict` on `image_only` | exit 1; the JSON is written; stderr names `no_text_layer` |
| CR4 | a missing file | exit 2 |
| CR5 | `--markdown` into a missing directory | exit 2; one line on stderr naming the path |

---

## 4 · The inspector (`render/inspector.py`)

It is for looking, not for gates (R-12 of the prototype: "review is by looking").

- **`render_pages(data, password, dpi) -> tuple[bytes | None, ...]`** (in `read/pymupdf_reader.py`)
  renders each page as PNG, unrotated, so the image matches the page model's coordinates. A page
  MuPDF cannot render (a damaged content stream) gives `None`, and the reading stops at the first
  page that cannot load, as the reader does.
- **`inspector_html(doc, pages_png) -> str`** builds the page from the document and one PNG per page.
  It raises `ValueError` when the count of images differs from the count of pages.
- **`build_inspector(doc, source, password=None) -> str`** loads the source, checks that its SHA-256
  is the document's, renders at 100 dpi, and calls `inspector_html`. A different PDF raises
  `ValueError`, because boxes drawn over the wrong page would mislead.

For each page, the HTML shows:

- **The rendered page** as an inline SVG: the PNG as an `<image>` with a `data:image/png;base64,`
  source, sized in points, with every block region on that page drawn as a `<rect>` coloured by kind
  and tagged with the block's number in reading order;
- **the page's findings** above the cards;
- **beside the image, the page's blocks as cards:** the id, the kind (and its level, label, or role),
  the text, and the markers.

Document-level findings (no page) head the whole report.

The page is static HTML with inline CSS and no scripts or external requests. It works in light and
dark mode (`prefers-color-scheme`) and prints legibly. All document text is HTML-escaped.

| # | case | expected |
|---|---|---|
| IN1 | `simple_text` | one page section, with one `<image>` whose source is `data:image/png;base64,` and one `<rect>` per block region |
| IN2 | a document whose text contains `<script>` | the text appears escaped, and the HTML contains no `<script` |
| IN3 | a 3-page document | three page sections, in order |
| IN4 | the HTML | references no `http://` or `https://` resource |
| IN5 | `inspector_html` with 2 images for a 3-page document | `ValueError` |
| IN6 | `build_inspector` with a different PDF than the document's | `ValueError` naming the mismatch |
| IN7 | `render_pages` on `rotated` | one PNG whose pixel size matches the unrotated page at the dpi |
| IN8 | `build_inspector` on `nested_graphics_states` | HTML whose page section says the page could not be rendered, with no `<image>` |
| IN9 | `render_pages` on `null_second_kid` | one image: rendering stops where loading stops |
| IN10 | a document with a heading, list item, footnote, definition, and footer | one card each, naming the level, label, term, and role |

---

## 5 · Acceptance

- [ ] RD1–RD10, MD1–MD7, CR1–CR5, and IN1–IN10 pass.
- [ ] `inkgrid read` emits a valid `Document` for every fixture, and the two-column fixture reads in
      column order (the M1 exit criteria).
- [ ] `render/` imports only `model` and `read`; only `read/pymupdf_reader.py` imports pymupdf.
