# 01 · The typed model and the output contract (M0)

**Implements:** `00-design.md` § 8 (the contract), § 9 (findings), and the model half of § 4.2.
**Modules:** `src/inkgrid/model/{geometry,canonical,findings,page,document}.py`.
**Depends on:** stdlib and pydantic only (tested by the import-graph test, `03-cli-and-packaging.md`).

The model is the only thing every other package shares. Everything in it is a frozen value. A value
that exists satisfies its invariants, because construction and parsing both run the validators: an
illegal state cannot be represented (negative-space programming).

---

## 1 · Geometry (`model/geometry.py`)

### Behavior

- `quantize(v: float) -> float` rounds to 0.01 pt with Python's `round(v, 2)` and adds `0.0`, so
  `-0.0` becomes `0.0`. A NaN or infinite input raises `ValueError`.
- `Rect(x0, y0, x1, y1)` is a frozen, slotted dataclass. Construction quantizes all four values, then
  requires `x0 ≤ x1` and `y0 ≤ y1`; otherwise `ValueError`. A zero-width or zero-height rect is legal
  (glyphs such as combining marks have one).
  - `width`, `height`, `area`, and `center` (a `(x, y)` pair, not quantized).
  - `contains_point(x, y)`: **half-open**, `x0 ≤ x < x1` and `y0 ≤ y < y1`.
  - `contains_rect(other)`: closed containment of `other` inside `self`.
  - `intersects(other)`: overlap with positive area. Touching edges do not intersect.
  - `union(other)`, and `Rect.union_all(rects)`, which raises `ValueError` on an empty input.
- `Interval(start, end)` is a half-open band `[start, end)`. It is quantized and requires
  `start < end`: a band has positive width. It provides `contains(v)` and `overlaps(other)`.
- **Serialization.** Both types plug into pydantic. A `Rect` serializes to a JSON array
  `[x0, y0, x1, y1]` and an `Interval` to `[start, end]`. Validation from JSON accepts exactly that
  shape; from Python it also accepts an instance or a tuple. Their JSON Schemas are fixed-length
  number arrays.

### Test cases

| # | case | expected |
|---|---|---|
| G1 | `quantize(1.234567)` | `1.23` |
| G2 | `quantize(2.675)` | `2.67` (binary representation; pinned so nobody "fixes" it) |
| G3 | `quantize(-0.001)` | `0.0` with a positive sign bit |
| G4 | `quantize(nan)`, `quantize(inf)` | `ValueError` |
| G5 | property: finite `x` in ±1e6 | `quantize(quantize(x)) == quantize(x)` |
| G6 | `Rect(0, 0, 10, 5)` | width 10, height 5, area 50, center (5, 2.5) |
| G7 | `Rect(10, 0, 0, 5)`, `Rect(0, 5, 10, 0)`, `Rect(nan, 0, 1, 1)` | `ValueError` |
| G8 | `Rect(0, 0, 0, 0)` | legal |
| G9 | `Rect(0.001, 0, 1.006, 1)` | `x0 == 0.0`, `x1 == 1.01` |
| G10 | `Rect(1.004, 0, 1.001, 1)` (both quantize to 1.0) | legal, width 0 |
| G11 | `Rect(1.006, 0, 1.001, 1)` (1.01 > 1.0) | `ValueError` |
| G12 | `Rect(0,0,10,10).contains_point` at (0,0) / (10,5) / (5,10) / (9.99,9.99) | True / False / False / True |
| G13 | property: random cut points tile `[0, W) × [0, H)` into rects | every sampled point is in exactly one rect |
| G14 | `Rect(0,0,5,5).intersects(Rect(5,0,10,5))`; with `Rect(4,0,10,5)` | False; True |
| G15 | `union` and `union_all` | min/max envelope; `union_all([])` raises |
| G16 | `contains_rect` of itself, of a larger rect | True; False |
| G17 | JSON `[0,0,10,5]` → `Rect`; dump | `Rect(0,0,10,5)`; `[0.0,0.0,10.0,5.0]` |
| G18 | JSON `[0,0,10]`, `[10,0,0,5]`, `["a",0,1,1]`, `{"x0":0}` | `ValidationError` |
| G19 | `Interval(0, 0)`, `Interval(5, 1)` | `ValueError` |
| G20 | `Interval(1, 4).contains` at 1 / 4 / 3.99 | True / False / True |
| G21 | `Interval(0,5).overlaps(Interval(5,9))`; with `Interval(4,9)` | False; True |

---

## 2 · Canonical helpers (`model/canonical.py`)

### Behavior

- `normalize_ws(text)`: every run of characters for which `str.isspace()` is true (this includes
  U+00A0, U+202F, U+2009, tab, and newline) becomes one ASCII space; the result is stripped.
- `content_key(kind, text)`: `"k" + sha256(f"{kind}\x1f{normalize_ws(text)}")[:16]`, lowercase hex.
- `assign_keys(items)`: given `(kind, text)` pairs in reading order, returns their keys. The 2nd,
  3rd, … identical pair gets `":2"`, `":3"`, … appended, so every key is unique.
- `sha256_hex(data: bytes)`: the full lowercase hex digest.

### Test cases

| # | case | expected |
|---|---|---|
| C1 | `content_key("paragraph", "a  b\n c")` vs `content_key("paragraph", "a b c")` | equal |
| C2 | same text, kinds `paragraph` and `heading` | different |
| C3 | the key shape | `^k[0-9a-f]{16}$` |
| C4 | `assign_keys([("p","x"),("p","y"),("p","x"),("p","x")])` | `[kx, ky, kx+":2", kx+":3"]` |
| C5 | `normalize_ws(" a b\tc\n")` | `"a b c"` |
| C6 | `sha256_hex(b"")` | the known empty-input digest |

---

## 3 · Findings (`model/findings.py`)

### Behavior

- `Severity`: `info`, `warning`, `error` (a `StrEnum`).
- `FindingCode`: a closed `StrEnum`. The severity of each code is fixed in one total mapping,
  `SEVERITY`, so no producer can mislabel one.

| code | severity | meaning |
|---|---|---|
| `no_text_layer` | error | a page has no words but draws content (an image or curves): unreadable, never guessed |
| `blank_page` | info | a page has no words and draws nothing but straight lines, or nothing at all |
| `partial_text_layer` | warning | characters without a Unicode mapping (they appear as U+FFFD) |
| `ocr_text_layer` | warning | most of the page's text is invisible (render mode 3) over an image: it is OCR output, so G1 does not hold for it |
| `hidden_text` | warning | invisible text that is not an OCR layer: the text layer says something the page does not show |
| `type3_font` | warning | words drawn in a Type 3 font, whose Unicode mapping MuPDF may have guessed from the raw character code |
| `clipped_text` | info | characters removed by clip paths or the page boundary |
| `overprinted_text` | info | characters of words drawn again at the same place, read once (M5c, spec 13 § 1) |
| `pdf_engine_warning` | info | a message MuPDF emitted while reading; pinned to the page it came from when it came from one |
| `unreadable_page` | error | a page the page tree declares could not be loaded, or its text could not be extracted |
| `lattice_failed` | warning | Camelot raised on a page (M2) |
| `lattice_disagrees` | warning | our rules saw a ruled region where Camelot returned no grid (M2) |
| `word_crosses_rule` | warning | a word's box crosses a drawn cell boundary (M2) |
| `header_not_found` | info | a table prints no header rows (M2) |
| `table_left_as_text` | warning | rows that read as an unruled table are left as text: no grid holds them without fusing two values or two rows (M2) |
| `call_unresolved` | warning | a footnote call with no note found (M3) |
| `no_furniture_long_document` | info | more than 8 pages and no furniture: confirm, do not assume (M1) |

`blank_page`, `hidden_text`, `type3_font`, `unreadable_page`, and `table_left_as_text` are additions
to the design's initial list:

- `blank_page` exists because `no_text_layer` is an error, and a genuinely empty page is not.
- Hidden text is a known way to smuggle instructions into text pipelines, so it must never be silent
  (G4).
- A Type 3 font's glyph names often map to nothing. MuPDF then falls back to the raw character code,
  which is a silent guess. The design folded this into `partial_text_layer`, but `text_layer` counts
  only U+FFFD, so it gets its own code.
- `unreadable_page` covers pages that exist in the page tree but cannot be read at all. Found by the
  final M0 review.
- `table_left_as_text` exists because an unruled table the corridors refuse (L2 forbids fusing two
  values into one cell) would otherwise become prose without a word (G4). Found by the final M2b
  review.

- `Finding(code, severity, page, block, detail)` is frozen. `page` is `None` or an integer of at least 1;
  `block` is `None` or a block id; `detail` is free text. A validator requires `severity ==
  SEVERITY[code]`. `Finding.of(code, detail, *, page=None, block=None)` fills the severity in.

### Test cases

| # | case | expected |
|---|---|---|
| F1 | every `FindingCode` member | has an entry in `SEVERITY` |
| F2 | `Finding(code=no_text_layer, severity=info, …)` | `ValidationError` |
| F3 | `Finding.of(no_text_layer, "x", page=1).severity` | `error` |
| F4 | `page=0`; JSON with an unknown code | `ValidationError` |

---

## 4 · The page model (`model/page.py`)

This is what the reader produces (`02-reader.md`) and what `inkgrid words` prints.

### Behavior

- `Word`: `id` (≥ 0), `page` (≥ 1), `bbox` (`Rect`), `text`, `size` (≥ 0), `font`, and the flags
  `bold`, `italic`, `superscript`, `hidden` (in the text layer but not drawn), and `horizontal` (set on
  a left-to-right horizontal line).
  - `text` is non-empty and contains no whitespace (`str.isspace`) and no character in Unicode
    categories Cc, Cf, Co, Cn, or Cs (a lone surrogate cannot be serialized as UTF-8). U+FFFD is
    legal: it is how an unmapped glyph appears.
- `Rule`: `page`, `axis` (`"h"` or `"v"`), `at` (the line's y for `h`, its x for `v`), `start < end`
  (its extent along the other axis), and `thickness` (≥ 0). It provides `length` and `rect`, the
  thickened bounding box.
- `PageInfo`: `number` (≥ 1), `width` and `height` (> 0, the unrotated CropBox), `rotation` (0, 90,
  180, or 270), `text_layer` (`full`, `partial`, or `none`), the counts `invisible_chars`,
  `clipped_chars`, `unmapped_chars`, and `hidden_chars` (each ≥ 0), `image_area_ratio` (0 to 1), and
  `overprinted_chars` (≥ 0, default 0; spec 13 § 1).
- `PageModel(PageInfo)` adds `words` and `rules`. Validators:
  - every word's and every rule's `page` equals `number`;
  - `text_layer == "none"` exactly when there are no words;
  - `text_layer == "partial"` exactly when there are words and `unmapped_chars > 0`.
- `Source`: `sha256` (64 lowercase hex), `pages` (≥ 1), `file_name` (`None` or a non-empty string).
- `ReaderInfo`: the `inkgrid`, `pymupdf`, and `mupdf` versions.
- `Reading`: `schema` (the literal `"inkgrid.reading/1"`), `source`, `reader`, `pages`, `findings`.
  Validators:
  - there is at least one page, and `len(pages) == source.pages`;
  - page numbers run `1..n` in order;
  - word ids, read page by page, run `0..N-1` with no gap;
  - every finding's `page` is `None` or `≤ n`, and its `block` is `None` (a reading has no blocks).
  - `Reading.words()` iterates every word in id order.

### Test cases

| # | case | expected |
|---|---|---|
| P1 | `Word` text `"a b"`, `""`, `"a\tb"`, `"a b"`, `"a​b"` (Cf), `""` (Co) | `ValidationError` |
| P2 | `Word` text `"�"` | legal |
| P2b | `Word` text holding a lone surrogate `\ud800` | `ValidationError` |
| P3 | `Word` with `size=-1`, `page=0`, `id=-1` | `ValidationError` |
| P4 | `Rule` with `start == end`, axis `"x"`, `thickness=-1` | `ValidationError` |
| P5 | `PageModel` holding a word from page 2 as page 1 | `ValidationError` |
| P6 | `rotation=45`; `width=0` | `ValidationError` |
| P7 | `text_layer="none"` with words; `"full"` with no words | `ValidationError` |
| P8 | `"partial"` with `unmapped_chars=0`; `"full"` with `unmapped_chars=3` | `ValidationError` |
| P9 | `image_area_ratio=1.5` | `ValidationError` |
| P10 | `Reading` with `source.pages=2` and one page | `ValidationError` |
| P11 | page numbers `[1, 3]`; an empty `pages` | `ValidationError` |
| P12 | word ids `[0, 2]`; ids restarting per page `[0, 1] [0]` | `ValidationError` |
| P13 | a finding with `page=5` in a 2-page reading; a finding with a `block` | `ValidationError` |
| P14 | `sha256` uppercase, or 63 characters | `ValidationError` |
| P15 | property: a generated `Reading` survives `model_dump_json` → `model_validate_json` | equal, and the second dump is byte-identical |
| P16 | `Reading.model_json_schema()` | equals the committed `docs/schema/reading.schema.json` |

---

## 5 · The document contract (`model/document.py`)

`Document` is the output of `inkgrid.read()` (M1). M0 defines it and its validators so every later
stage builds against a fixed contract. Its field list is `00-design.md` § 8.1, made exact here.

### Types

- `PageInfo` (§ 4) for each page, and `Word` (§ 4).
- `Region(page, bbox)`.
- The block kinds share `BlockBase`: `id`, `key`, `regions` (non-empty), `word_ids` (non-empty, no
  duplicates, in reading order), `text`, `markers` (strings), and `hyphen_joins` (pairs of word ids).
  They are discriminated by `kind`:
  - `Heading`: `level` (≥ 1, where 1 is the document's largest heading size) and `number` (the printed
    section number, or `None`);
  - `Paragraph`;
  - `ListItem`: `label`, non-empty;
  - `Footnote`: `label`, non-empty;
  - `Definition`: `term` and `body`, both non-empty;
  - `Table`: `grid`;
  - `Furniture`: `role`, one of `header`, `footer`, or `page_number`.
- `Grid`: `n_rows` and `n_cols` (≥ 1), `row_bands` and `col_bands` (`Interval`s), `header_rows`
  (`0..n_rows`), `banner_rows` (sorted, unique row indices), `source` (`lattice` or `corridor`),
  `frame` (`0`, `90`, `180`, or `270`, default `0`: the rotation from the unrotated page to the frame
  the bands are measured in), and `cells`.
- `Cell`: `row`, `col` (≥ 0), `row_span`, `col_span` (≥ 1), `text`, `word_ids`, `carried`,
  `source`, and `markers`. An empty cell (no words, text `""`) is legal: blank cells, including
  blank merged cells, are part of a table's shape. `source` lists the parent-table anchors a carried
  cell copies (non-empty exactly when `carried`).
- `Link`: `kind` (`footnote_call` or `continuation`), `from` (`{block, cell}`, where `cell` is a
  `(row, col)` anchor or `None`; the Python attribute is `from_`, and JSON uses `"from"`), `to`,
  `label`, `method` (`superscript`, `parenthetical`, or `named`), `status` (`resolved`, `unresolved`,
  or `rejected`), and `reason`.
- `Ledger`: `content_chars`, `furniture_chars`, `invisible_chars`, `clipped_chars`,
  `overprinted_chars` (each ≥ 0), and `partition` (the literal `"proved"`).
- `Producer`: the versions of `inkgrid`, `pymupdf`, and `mupdf`; `camelot` and `pypdfium2` (`None`
  until a milestone uses them); and the `lexicon` and `profile` ids and the `lattice` engine
  (`combined` or `raster`).
- `Document`: `schema` (the literal `"inkgrid.document/1"`), `source`, `producer`, `pages`, `words`,
  `blocks`, `links`, `findings`, and `ledger`. It also provides `complete` (no error-severity finding)
  and `tables()`, which returns the table blocks in reading order.

### Invariants (every one is a validator)

**Pages and words.**
1. `len(pages) == source.pages`, and page numbers run `1..n`.
2. Word ids run `0..N-1` in list order; word pages are non-decreasing and at most `n`.
3. For each page, `text_layer == "none"` exactly when it has no words, and `"partial"` exactly when it
   has words and `unmapped_chars > 0`.

**The partition (G2).**
4. Every word id belongs to exactly one block. The validator reports the first missing or doubled id.
5. Every block owns at least one word, and its `word_ids` hold no duplicates.

**Block identity.**
6. Block ids are `b1..bM` in list order, and keys are unique.

**Text (G1 at the model level).** `text` may contain only `" "` and `"\n"` as whitespace, never two in
a row, and none at either end.
7. **In order**, the non-whitespace characters of `text` equal the concatenation of the block's
   words' texts in `word_ids` order, with the final `"-"` of word `a` removed for each hyphen join
   `(a, b)`. An ordered check, not a multiset: `12` and `34` can never read as `13 24`. For a table,
   `word_ids` order is the non-carried cells' words in `(row, col)` order, and `text` excludes carried
   cells.
8. Each hyphen join `(a, b)` names two different words of the block, where `a` ends in `"-"` and is
   longer than one character, `b` starts with a lower-case letter, and `b` immediately follows `a` in
   `word_ids`. No pair appears twice.

**Derived fields are re-derived.**
8a. Each block's `key` equals `assign_keys` over the document's `(kind, text)` pairs in order.
8b. A list item's `label` equals its first word's text. A footnote's `label` equals its first word's
    text stripped of `(`, `)`, and `.` at both ends. A heading's `number`, when set, equals its first
    word's text.
8c. A definition's `text` equals `term + " " + body`.
8d. A block's `markers` equal the texts of its superscript words, in `word_ids` order.

**Regions.**
9. Region pages are strictly increasing. Every region's page holds at least one of the block's words,
   and every block word lies inside the region for its page (closed containment).
10. A table has exactly one region.

**Grids.**
11. `len(row_bands) == n_rows` and `len(col_bands) == n_cols`, and each band list is sorted and
    non-overlapping.
12. `header_rows ≤ n_rows`, and every banner row is in `[0, n_rows)`.

**Cells.**
13. Cells are sorted by `(row, col)` and tile the grid **exactly**: every span is at least 1 and stays
    within bounds, and every position is covered by exactly one cell. The check runs per row over
    column intervals, so its cost is bounded by the grid's own size.
14. A carried cell has non-empty text, owns no words, and names its `source`. A non-carried cell's
    words are table words; the non-carried cells' word sets are disjoint and their union is the
    table's `word_ids`. A non-carried cell with no words has text `""`.
15. The center of every word of a non-carried cell lies inside the cell's rectangle, computed from the
    bands and tested half-open. When the grid's `frame` is not 0 (a table on a page read upright in
    its screen frame, `06-ruled-tables.md` § 6), the word's box is first turned by `frame` over the
    page's unrotated size (`turn_rect`), and the turned box's center is tested, exactly as the table
    stage claimed it.
16. A cell's text satisfies invariant 7 against its own words and the block's joins inside it.
17. A table with carried cells is the `from` of a resolved `continuation` link. Each carried cell's
    `source` anchors are cells of that link's `to` table in its header rows (`row < header_rows`), and
    its text equals their texts joined by single spaces, in the order listed: a carried header
    is only ever the parent's printed header.

**Links.**
18. `from.block` exists; `from.cell`, if set, is a cell anchor of that block, which must be a table.
19. `to`, if set, exists. `resolved` requires `to`; `unresolved` and `rejected` forbid it, and
    `rejected` requires `reason`.
20. A `footnote_call` requires `label` and `method`, and when resolved, `to` is a footnote block.
21. A `continuation` has no `method`, is always `resolved`, links two tables, and its `to` comes earlier
    in reading order than its `from`.

**Findings and ledger.**
22. A finding's `page` is `≤ n` and its `block` exists.
23. `content_chars` is the character count of the words in non-furniture blocks, and
    `furniture_chars` the count in furniture blocks. `invisible_chars`, `clipped_chars`, and
    `overprinted_chars` equal the sums over pages.

Serialization is `model_dump_json()` in declaration order, using aliases. That output is canonical:
parsing it and dumping again returns the same bytes.

**No bypass.** Models re-validate nested instances (`revalidate_instances="always"`). So a value
altered with `model_copy(update=…)` fails validation the moment it is placed inside another model, and
a `PageModel` passed where a `PageInfo` is expected is rejected, since its extra fields are forbidden,
rather than carried along silently.

### Test cases

Tests build documents with a small helper that assembles valid ones (pages, words, blocks) from short
descriptions; each failure case starts from a valid document and breaks one thing.

| # | case | expected |
|---|---|---|
| D1 | a one-page document: two words, one paragraph, matching ledger | valid; `complete` is True |
| D2 | a word in two blocks | `ValidationError` naming the word id |
| D3 | a word in no block | `ValidationError` naming the word id |
| D4 | block `word_ids` with a duplicate; an id that is not a word; an empty `word_ids` | `ValidationError` |
| D5 | block ids starting at `b2`; two blocks with one key | `ValidationError` |
| D6 | text with an extra character; with `"\t"`; with a double space; with a leading space | `ValidationError` |
| D7 | words `["execu-", "tions"]`, join `(0, 1)`, text `"executions"` | valid |
| D8 | the same text without the join | `ValidationError` |
| D9 | a join whose first word lacks the `-`; whose second is upper case; naming a word outside the block; `(a, a)` | `ValidationError` |
| D10 | a region on a page with none of the block's words; a word outside its region | `ValidationError` |
| D11 | a paragraph with regions on pages 1 and 2 holding its words | valid |
| D12 | regions on pages `[2, 1]`; a table with two regions | `ValidationError` |
| D13 | `n_rows` ≠ `len(row_bands)`; overlapping bands; unsorted bands | `ValidationError` |
| D14 | `header_rows > n_rows`; a banner row out of range or unsorted | `ValidationError` |
| D15 | a 2 × 2 table, four cells, words centered in their cells | valid |
| D16 | a cell with `row_span=0`; a cell past the grid edge; two cells covering one position; cells unsorted | `ValidationError` |
| D17 | a merged cell `row_span=2` covering two rows, holding its words | valid |
| D18 | a carried cell with words; a carried cell with empty text | `ValidationError` |
| D19 | a table word in no cell (its cell emptied); a word in two cells; a cell word from outside the table | `ValidationError` |
| D20 | a cell word whose center lies outside the cell's rectangle | `ValidationError` |
| D21 | carried cells and no continuation link | `ValidationError` |
| D22 | links: unknown `from` block; unknown `to`; `resolved` without `to`; `unresolved` with `to`; `rejected` without a reason | `ValidationError` |
| D23 | a `footnote_call` without a label or method; resolved to a paragraph | `ValidationError` |
| D24 | a `continuation` with a method; between a table and a paragraph; pointing forward; `unresolved` | `ValidationError` |
| D25 | a link whose `from.cell` is not a cell anchor of its table | `ValidationError` |
| D26 | a valid continuation: a later table with carried header cells linked to an earlier one | valid |
| D27 | a finding on page 3 of 2; a finding naming block `b9` that does not exist | `ValidationError` |
| D28 | ledger `content_chars` off by one; `clipped_chars` ≠ the page sum | `ValidationError` |
| D29 | an error-severity finding | valid; `complete` is False |
| D30 | `tables()` on a document with a paragraph and two tables | the two tables, in order |
| D31 | JSON round trip of D15, D26 | equal, byte-identical second dump; `"from"` is the JSON key |
| D32 | `Document.model_json_schema()` | equals the committed `docs/schema/document.schema.json` |
| D33 | property: a random partition of N words into paragraphs (valid text) | validates; moving one word into two blocks fails |
| D34 | `source.pages=2` with one page; page numbers `[1, 1]` | `ValidationError` (invariant 1) |
| D35 | word ids `[0, 2]`; a page-1 word after a page-2 word; a word on page 3 of 2 | `ValidationError` (invariant 2) |
| D36 | a page with words but `text_layer="none"`; with `unmapped_chars=1` but `"full"` | `ValidationError` (invariant 3) |
| D37 | a cell whose text has an extra character; whose text is its word scrambled (`04.$0` for `$0.40`) | `ValidationError` (invariant 16) |
| D38 | words `12` and `34` with block text `13 24` | `ValidationError` (invariant 7 is ordered) |
| D39 | a join listed twice; a join recorded but not applied (`execu- tions`); a join between non-adjacent words | `ValidationError` (invariant 8) |
| D40 | a key `k0000000000000000` that is not content-derived; a first key ending `:7` | `ValidationError` (8a) |
| D41 | a list-item label that is not its first word; a footnote label unrelated to it; a heading number that is not its first word; a definition whose text is not `term body` | `ValidationError` (8b, 8c) |
| D42 | a 2 × 2 table with one blank cell; a blank merged cell spanning two rows | valid |
| D43 | a grid with one position covered by no cell | `ValidationError` (invariant 13) |
| D44 | a carried cell whose source is not a header cell of the parent; whose text differs from its source (`Rebate` for `Fee`) | `ValidationError` (invariant 17) |
| D45 | a `Word` altered with `model_copy(update={"size": -3})`, placed in a `PageModel`; a `Document` given a `PageModel` as a page | `ValidationError` (no bypass) |
| D48 | a `frame = 90` table whose word, turned, has its centre exactly on a column edge, and sits in the cell right of it | valid: the check turns the word's box and takes its centre, as the table stage does |
| D47 | a table whose grid has `frame = 90`, valid in the turned frame; the same table with `frame = 0` | valid; `ValidationError` (invariant 15) |
| D46 | a paragraph with a superscript word but no markers; with a marker naming a word that is not superscript | `ValidationError` (invariant 8d) |

---

## 6 · Acceptance

- [ ] G1–G21, C1–C6, F1–F4, P1–P16 (and P2b), and D1–D45 pass.
- [ ] The model package imports only stdlib and pydantic (import-graph test).
- [ ] `docs/schema/reading.schema.json` and `docs/schema/document.schema.json` are generated by
      `scripts/export_schemas.py` and committed; the schema tests fail if a model changes without them.
- [ ] `mypy --strict` is clean.
