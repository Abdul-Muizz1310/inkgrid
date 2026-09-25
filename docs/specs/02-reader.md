# 02 · The PyMuPDF reader (M0)

**Implements:** `00-design.md` § 5.1, and the page-model half of guarantee G4.
**Modules:**
- `src/inkgrid/read/source.py`: normalize the input to bytes (I/O);
- `src/inkgrid/read/words.py`: pure; typed characters become words;
- `src/inkgrid/read/rules.py`: pure; typed vector paths become rules;
- `src/inkgrid/read/pymupdf_reader.py`: the only module that calls PyMuPDF.

**Output:** a `Reading` (`01-model.md` § 4).

The reader's job is to turn one PDF into typed values and to absorb every PyMuPDF quirk, so nothing
downstream sees one. It makes the few layout decisions that belong to the text layer itself (what a
word is, what a drawn rule is) and none of the decisions that belong to layout.

The facts below were measured on PyMuPDF 1.28.2 on 2026-09-25/26, with probes kept out of the repo.

---

## 1 · Input (`read/source.py`)

`load_source(source) -> Loaded(data: bytes, file_name: str | None)` accepts:
- a path (`str` or `os.PathLike`);
- `bytes`, `bytearray`, or `memoryview`;
- a binary file object whose `read()` returns bytes.

| # | case | expected |
|---|---|---|
| S1 | a path to a PDF | its bytes; `file_name` is the base name |
| S2 | `bytes` / `bytearray` / `memoryview` / `io.BytesIO` | the same bytes; `file_name` is `None` |
| S3 | a missing path; a directory | `PdfOpenError`, chained to the `OSError` |
| S4 | a text-mode file object (`read()` returns `str`) | `TypeError` |
| S5 | `None`, `42` | `TypeError` |
| S6 | empty input from any source | `PdfOpenError("empty input")` |

A wrong *type* is a programming error, so it raises `TypeError`. A bad *file* is bad input, so it
raises an `InkgridError`.

---

## 2 · Opening (`read/pymupdf_reader.py`)

- Open with `pymupdf.open(stream=data, filetype="pdf")`, so a PNG or an EPUB is never parsed as
  something else. `pymupdf.FileDataError`, and its subclass `EmptyFileError`, become `PdfOpenError`.
- Encryption:
  - `doc.needs_pass` with no password raises `PasswordRequired`.
  - `doc.authenticate(pw) == 0` raises `WrongPassword`.
  - A password given for an unencrypted file is ignored.
  - A file encrypted with only an owner password opens without one; PyMuPDF reports
    `needs_pass == 0`.
- A document with zero pages raises `PdfOpenError`.
- `source.sha256` is the digest of the input bytes, and `source.pages` is `doc.page_count`.

**Quiet by construction.** Around each read, the reader:
1. saves `TOOLS.mupdf_display_errors()` and `TOOLS.mupdf_display_warnings()`, and sets both off;
2. calls `TOOLS.reset_mupdf_warnings()`;
3. reads the document;
4. collects `TOOLS.mupdf_warnings()`;
5. restores both display settings, in a `finally` block.

Nothing reaches stdout or stderr, down to the file-descriptor level. The reader imports `pymupdf`
only, never `fitz` (which prints a deprecation warning), `pymupdf4llm`, or `pymupdf.layout`. PyMuPDF is
not thread-safe, so neither is the reader; the docstring says so.

| # | case | expected |
|---|---|---|
| O1 | `b"hello world"` | `PdfOpenError` |
| O2 | the first half of a valid PDF | `PdfOpenError` |
| O3 | `b"%PDF-1.7\n"` alone | `PdfOpenError` |
| O4 | O1–O3 under `capfd` | nothing written to stdout or stderr |
| O5 | a user-password PDF with no password / a wrong one / the right one | `PasswordRequired` / `WrongPassword` / a `Reading` |
| O6 | an owner-password-only PDF with no password | a `Reading` |
| O7 | a password for an unencrypted PDF | a `Reading` |
| O8 | a hand-written PDF whose page tree has `/Count 0` | `PdfOpenError` |
| O9 | a read that makes MuPDF warn | display settings afterwards equal those before |
| O10 | reading the same bytes twice | byte-identical `model_dump_json()` |

---

## 3 · Characters

Text is extracted with `page.get_text("rawdict", flags=TEXT_PRESERVE_WHITESPACE | TEXT_CLIP)`. The
flags are chosen on purpose:

- **`TEXT_USE_CID_FOR_UNKNOWN_UNICODE` is off.** With it on, a glyph with no Unicode mapping comes
  back as its raw character code, a silent guess. With it off, the glyph comes back as U+FFFD, which is
  honest and countable.
- **`TEXT_PRESERVE_LIGATURES` is off**, so a ligature glyph arrives as its constituent letters, which
  is what a reader of the page reads.
- **`TEXT_PRESERVE_IMAGES` is off**, because image bytes are not needed. Image placement comes from
  `get_image_info()`.

The reader converts `rawdict` into typed values, `RawLine(dir, spans)`, `RawSpan(font, size, flags,
char_flags, chars)`, and `RawChar(c, bbox)`, at the boundary. Nothing past this point sees a dict.

---

## 4 · Words (`read/words.py`, pure)

`build_words(lines, page, first_id) -> WordsOut(words, invisible_chars, unmapped_chars,
hidden_chars)`.

**Character classes.** A character is:
- *whitespace* if `c.isspace()`, or if it is U+200B (the zero-width space, which marks a word break);
- *invisible* if its Unicode category is Cc, Cf, Co, or Cn and it is not whitespace;
- otherwise a *word character*.

**Rules.**
- **W1.** A token is a maximal run of word characters within one span, with invisible characters
  skipped over. Whitespace ends a token; an invisible character does not.
- **W2.** A token's box is the union of its characters' boxes.
- **W3.** Across a span boundary *within one line*, the first token of a span joins the last token of
  the previous span when all of these hold:
  - no whitespace separates them;
  - both have the same superscript state and the same hidden state;
  - they overlap vertically by at least 0.3 × the smaller height;
  - `−1.0 ≤ next.x0 − prev.x1 ≤ 0.6` pt.

  This is how a font change mid-word stays one word, and how `$0.40` followed by a raised `2` becomes
  two words. W3 applies only on horizontal lines.
- **W4.** A word's `size` and `font` come from the span that contributes the most of its characters,
  with ties going to the earliest. `size` is rounded to 2 dp.
  - `bold` is set if that span's `flags & 16`, or its `char_flags & 8`, or `"bold"` appears in the
    lower-cased font name.
  - `italic` is set if `flags & 2`, or `"italic"` or `"oblique"` appears in the name.
  - `superscript` is `flags & 1`.
  - `hidden` is set when `char_flags & (16 | 32) == 0`: the span is neither filled nor stroked
    (render mode 3 or 7).
  - `horizontal` is the line direction `(1, 0)` within 1e-3.
- **W5.** Counts:
  - `invisible_chars` counts invisible characters, which never appear in a word;
  - `unmapped_chars` counts U+FFFD characters, which stay in the word;
  - `hidden_chars` counts the word characters of hidden spans.
- **W6.** Words are numbered from `first_id` in `rawdict` order (block, line, span, character).

**Why the superscript flag and not a size test.** MuPDF flags a character as superscript when its
origin sits more than 0.1 × size above the origin of the line's first character. So a marker that
opens a line is never flagged, and subscripts never are. Parenthesized and named calls cover those
cases in M3 (design L7).

| # | case (typed input, no PDF) | expected |
|---|---|---|
| W-1 | one span `"Hello world"` | words `Hello`, `world`, ids `first_id`, `first_id+1` |
| W-2 | spans `"Trans"` + `"action"` (bold), touching | one word `Transaction`; font from the longer span |
| W-3 | spans `"$0.40"` + raised `"2"` (superscript flag) | `$0.40`, then `2` with `superscript=True` |
| W-4 | the W-2 spans with a gap of 0.7 pt; of 0.6 pt; of −1.0 pt; of −1.1 pt | two words; one; one; two |
| W-5 | the W-2 spans in *different* lines | two words |
| W-6 | spans on one baseline, overlapping vertically by 0.25 × height | two words |
| W-7 | `"soft­hy"` (soft hyphen, Cf) | one word `softhy`; `invisible_chars=1` |
| W-8 | `"zero​width"` | words `zero`, `width`; `invisible_chars=1` |
| W-9 | `"ab"` (private use), `"a\x07b"` (Cc) | `ab`; `invisible_chars=1` each |
| W-10 | `"��C"` | one word `��C`; `unmapped_chars=2` |
| W-11 | a span with `char_flags=0` (render mode 3) | words with `hidden=True`; `hidden_chars` counts them |
| W-12 | a hidden span next to a visible span, touching | two words (W3 requires equal hidden state) |
| W-13 | tabs, U+00A0, U+202F, U+2009 inside a span | all split words |
| W-14 | a vertical line, direction `(0, -1)` | words with `horizontal=False`; no W3 joins |
| W-15 | fonts `Helvetica-Bold`, `Arial,BoldMT`, `Times-Italic`, `Foo-Oblique` | `bold` / `bold` / `italic` / `italic` |
| W-16 | a span of only whitespace and invisible characters | no words |
| W-17 | property: random spans of word characters and whitespace | every word character appears in exactly one word, in order; no word contains whitespace |

---

## 5 · Rules (`read/rules.py`, pure)

`extract_rules(paths, page) -> tuple[Rule, ...]`, where each `RawPath` carries:
- `kind`: `f`, `s`, or `fs`;
- stroke `width`, stroke `color` and `stroke_opacity`;
- `fill` and `fill_opacity`;
- `items`: `Line(p, q)`, `RectItem(rect)`, `QuadItem(4 points)`, or `Curve`.

**Visibility.**
- A path is *stroke-visible* when its kind contains `s`, its color is set, and its stroke opacity
  (`None` means 1) is above 0.
- It is *fill-visible* when its kind contains `f`, its fill is set, and its fill opacity is above 0.
- A path that is neither yields nothing.

**Rules.**
- **R1. Lines count only in stroke-visible paths.**
  - Horizontal when `|dy| ≤ 0.5` and `|dx| ≥ 2.0`. The rule sits at the mean y, spans min x to max x,
    and has thickness = the stroke width (`None` means 0).
  - Vertical is the mirror.
  - Other lines are not rules.
- **R2. Rectangles.** A `re` item is a rectangle. So is a `qu` item whose corners form an axis-aligned
  rectangle within 0.5 pt; a closed four-segment path comes back from PyMuPDF as `qu`. Let `t` be the
  shorter side and `L` the longer:
  - if `t ≤ 2.5` and `L ≥ 2.0`: one rule along the long axis at the centre line, with
    `thickness = t` (plus the stroke width when stroke-visible);
  - else, if stroke-visible and both sides are at least 2.0: four edge rules (top, bottom, left, right)
    with the stroke width as thickness;
  - else no rule. A thick fill-only rectangle is a background, and a small one is a dot.
- **R3.** Curves and other quads are not rules.
- **R4.** Rules equal in `(axis, at, start, end)` after quantization collapse to one, keeping the
  greatest thickness. PyMuPDF returns a stroked line with its closing segment, so it arrives twice.
  Output is sorted by `(axis, at, start, end)`.

These thresholds are fixed and documented, not configurable. The verifier (M4) reads rules with
different thresholds on purpose.

| # | case (typed input) | expected |
|---|---|---|
| R-1 | a stroked horizontal line (50,200)→(150,200), width 0.8, plus its closing segment | one rule `h` at 200, 50..150, thickness 0.8 |
| R-2 | a line slanted by 0.4 pt over 100 pt; by 0.6 pt | a rule; no rule |
| R-3 | a line 1.9 pt long | no rule |
| R-4 | a fill-only thin rect (50,100)–(150,101) | `h` at 100.5, 50..150, thickness 1.0 |
| R-5 | a stroked 100 × 60 rect, width 1 | four rules: `h` at y0 and y1 over x0..x1, `v` at x0 and x1 over y0..y1 |
| R-6 | a fill-only 100 × 60 rect | no rules |
| R-7 | an axis-aligned `qu` from a closed polyline, stroked | four edge rules |
| R-8 | a rotated `qu` (a diamond) | no rules |
| R-9 | a stroked line in a path with `color=None`; with `stroke_opacity=0` | no rule |
| R-10 | a line item in a fill-only path | no rule |
| R-11 | a curve item | no rule |
| R-12 | two identical rules with thicknesses 0.5 and 1.0 | one rule, thickness 1.0 |
| R-13 | a vertical thin rect 1 × 80 | `v` at the centre x, thickness 1 |
| R-14 | output order for shuffled input | sorted by `(axis, at, start, end)` |

---

## 6 · Page geometry and findings

**Geometry.**
- `width` and `height` are the unrotated CropBox dimensions. `rotation` is `page.rotation`.
- Coordinates are measured from the CropBox's top-left corner, y pointing down, in the unrotated page.
  A 90° page keeps its unrotated coordinates, and so does an offset MediaBox (probe: text at PDF
  (72, 600) in MediaBox `[-100 -100 512 692]` reads at x = 172).

**Page-level measurements.**
- `image_area_ratio` is the sum of image-placement areas from `get_image_info()`, each clipped to the
  page, divided by the page area and capped at 1.
- `clipped_chars` is the count of non-whitespace characters in `get_text("text")` with `TEXT_CLIP`
  cleared, minus the count with it set. These are characters inside clip paths or off the page.

**Findings, per page, in this order.**
1. **No words.** If the page has an image or any curve item, `no_text_layer`; otherwise `blank_page`.
   `text_layer` is `none`.
2. `partial_text_layer`, when `unmapped_chars > 0`; the detail gives the count.
3. `ocr_text_layer`, when `hidden_chars ≥ 50%` of the page's word characters and
   `image_area_ratio ≥ 0.5`. Otherwise `hidden_text`, whenever `hidden_chars > 0`. The detail gives the
   count.
4. `clipped_text`, when `clipped_chars > 0`.

**Document level, after all pages.** One `pdf_engine_warning` for each distinct MuPDF warning line, in
first-seen order. After 20, a single final finding says how many more there were.

| # | case (generated PDF fixture) | expected |
|---|---|---|
| X1 | a page with a heading (bold, 14 pt), a paragraph, and an italic word | words in order with the right `bold`, `italic`, and `size` |
| X2 | `$0.40` with a raised 6.5 pt `2` | words `$0.40`, `2` (superscript) |
| X3 | `Trans` + bold `action` inserted flush | one word `Transaction` |
| X4 | text in render mode 3 on a page without images | hidden words; `hidden_text` |
| X5 | an image covering the page with render-mode-3 text on it | `ocr_text_layer` |
| X6 | an image-only page | no words; `text_layer=none`; `no_text_layer` (error) |
| X7 | an empty page | `blank_page` (info) |
| X8 | a page drawing only a straight line | `blank_page` |
| X9 | `inside` plus `clipped` drawn inside a clip path that hides it | only `inside` in words; `clipped_chars=7`; `clipped_text` |
| X10 | Helvetica with an `/Encoding /Differences` to unknown glyph names | words contain U+FFFD; `text_layer=partial`; `partial_text_layer` |
| X11 | a drawn table: stroked lines, thin filled rects, a stroked cell rect, a background, a diagonal | exactly the expected rule set |
| X12 | a `/Rotate 90` page | `rotation=90`; width and height unrotated (612 × 792); word coordinates as drawn |
| X13 | MediaBox `[-100 -100 512 692]` | a word at x = 172 |
| X14 | CropBox `[50 50 550 750]` inside a 600 × 800 MediaBox | width 500, height 700; a word drawn at x = 100 reads at x = 50 |
| X15 | a three-page document | word ids dense across pages; `source.pages=3` |
| X16 | a file that makes MuPDF repair it but still opens | a `Reading` with `pdf_engine_warning` findings |

---

## 7 · Acceptance

- [ ] S1–S6, O1–O10, W-1–W-17, R-1–R-14, and X1–X16 pass.
- [ ] Only `read/pymupdf_reader.py` imports `pymupdf`; `read/words.py` and `read/rules.py` import
      nothing outside `model` and the stdlib.
- [ ] `mypy --strict` is clean, using local stubs in `typings/pymupdf/` for the parts of PyMuPDF the
      reader calls. The stubs type `get_text("rawdict")` with `TypedDict`s taken from the measured
      shape.
