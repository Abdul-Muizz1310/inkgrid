# 06 · Ruled tables: Camelot lattice grids, header and banner rows, exports (M2a)

**Implements:** `00-design.md` § 4.3 stage 3 (ruled part), § 5.2 (Camelot), § 6.1 (value classes), and the
table exports of § 7. M2 is split in three: **M2a** ruled tables (this spec), **M2b** unruled tables
(whitespace corridors, and the rule-grid fallback), **M2c** note lists, glossaries, and definitions.
**Modules:**
- `model/lattice.py`: `PageFrame`, `RuledGrid`, `LatticeReading`;
- `model/geometry.py`: `turn_point`, `turn_rect` (moved from `core/view.py`);
- `model/document.py`: `Grid.frame`, and invariant 15 made frame-aware;
- `model/export.py`: table Markdown, HTML, and dense rows;
- `read/camelot_reader.py`: the only module that imports camelot;
- `read/pymupdf_reader.py`: `page_frames`;
- `core/lexicon.py`: `is_value`;
- `core/tables/pages.py`: which pages Camelot reads;
- `core/tables/shape.py`: rectangles to rows, columns, and spans;
- `core/tables/lattice.py`: accepted grids to proto tables;
- `core/pipeline.py`, `core/assemble.py`: the table stage in order;
- `api.py`, `cli.py`: the lattice engine setting.

---

## 0 · What was measured first (L19)

Camelot 2.0.0 ran over the seven M1 fee schedules (304 pages) with each engine; the record is
`knowledge/research/RR-0015-camelot-engines-on-fee-schedules.md`.

- **Engines.** `vector` matched `combined` on every page's table shapes and, wherever their cell edges
  differed, was right or `combined` was wrong (a banner split in four, a header merged, a cover page and a
  fill-only table read as grids). `vector` is about 5x faster (Cboe: 1.8 s against 8.2 s for 24 pages).
  `raster` alone found 25 of PHLX's 50 tables.
- **The default stays `combined`**, because DR-0022 accepted it and only the owner can supersede that
  decision. `vector` becomes a third allowed setting, and the measurement goes to the owner.
- **Pages.** "At least 2 horizontal and 2 vertical rules" selected exactly the pages Camelot found grids on,
  for 6 of 7 documents.
- **Frames.** SIX has no ruled tables. Its only grid, on all 70 pages, is a 3 x 3 box around a furniture
  label. The acceptance rule of § 5 rejects all 70 and accepts 257 grids elsewhere; claimed words match the
  prototype's conservation counts within 1% (Cboe 22,152 against 22,180).
- **Coordinates.** Camelot measures from the MediaBox's bottom-left, y up. It works in the page's rotated
  frame when it turns the page, which it does for `/Rotate` 180 and when the text is upright only after a
  `/Rotate` of 90 or 270; `Table.pdf_size` is then swapped for 90 and 270.

---

## 1 · Values (`core/lexicon.py`)

`is_value(text) -> bool` says whether a cell's whole text reads as one value. It classifies; it never
decides structure. The grammar, matched against the whole text after trimming:

- **number:** an optional sign (`-`, `+`, or U+2212) and digits, either grouped in threes by one of
  `,` `.` `'` U+00A0 U+202F or a space, with an optional decimal part after `.` or `,`; or plain digits with an
  optional decimal part. `1,234.5`, `1.234,5`, `1 234`, `1'234`, `0.40`, `12`.
- **value:** a number with, in order, optional pieces around it: a currency before it (a symbol from
  `$ € £ ¥ ₹ ₣ R`, or a three-letter upper-case code), a magnitude after it (`k`, `m`, `mn`, `bn`, `K`, `M`,
  `B`), a unit (`%`, `bp`, `bps`, `‰`, or a currency symbol or code), a per-unit suffix (`/port/month`,
  `/contract`), and trailing note marks (`*`, `†`, `‡`).
  One space may separate a currency or unit from the number. `$0.40`, `R 0.00`, `0.13 EUR`, `20,000 €`,
  `€1.4bn`, `-0.15bp`, `0.45bp*`, `12%`.
- **parenthesized:** a value inside `(` `)`, the accounting negative: `(47)`, `($0.10)`.
- **range:** two values joined by `-`, U+2013, or `to`, with optional spaces: `0.10 - 0.20`, `1–5`.
- **placeholder:** exactly `—`, `–`, `-`, `n/a`, `N/A`, `nil`, or `free` in any case.
- **Not values:** a bare year from 1900 to 2099 (labels such as `2026` head columns), and anything with a
  letter beyond the pieces above (`Tier 1`, `Monthly`, `0.10 per contract`).
- **Strong values.** `is_strong_value(token)` is a value with a currency, a unit, a magnitude, a decimal part,
  or thousands grouping: `$0.00`, `0.0030`, `5,000`, `12%`, `0.25bp`. A bare integer (`1`, `12`), a
  parenthesized one (`(47)`, a note reference), a placeholder, and an integer range are weak: header cells
  hold `Tier 1`, `Fee (47)`, and `Fee - Tier`.

| # | case | expected |
|---|---|---|
| VL1 | `0.40`, `1,234.5`, `1.234,5`, `1 234`, `1'234`, `−` + `0.10`, `12` | values |
| VL2 | `$0.40`, `R 0.00`, `0.13 EUR`, `20,000 €`, `€1.4bn`, `-0.15bp`, `0.45bp*`, `12%`, `CHF 25`, `$575/port/month`, `0.10/contract` | values |
| VL3 | `(47)`, `($0.10)`, `0.10 - 0.20`, `1–5`, `—`, `n/a`, `Free` | values |
| VL5 | `is_strong_value` on `$0.00`, `0.0030`, `5,000`, `12%`, `0.25bp`, `R0.00`; on `1`, `12`, `(47)`, `—`, `n/a`, `2026`, `1-5` | strong; weak |
| VL4 | `2026`, `Tier 1`, `Monthly`, `0.10 per contract`, `ZAR (Ex VAT)`, `` (empty), `1.2.3` | not values |

---

## 2 · The lattice reading (`model/lattice.py`, `read/camelot_reader.py`)

### Types

- **`PageFrame`**: a page's `number`, `rotation`, and the `width` and `height` of its unrotated CropBox.
  `pymupdf_reader.page_frames(data, password) -> tuple[PageFrame, ...]` reads them, so `camelot_reader`
  never imports pymupdf.
- **The lattice copy.** `pymupdf_reader.lattice_copy(data, password) -> bytes` is the document Camelot
  reads: decrypted, with each page's MediaBox set to its CropBox (in PDF coordinates; PyMuPDF reports
  the CropBox measured down from the MediaBox top). Camelot's raster engines render the CropBox but
  scale it by the MediaBox, and Camelot's parser needs an optional package for AES, so a copy whose
  two boxes agree and which carries no encryption is the only input all three engines place
  correctly. It shows every word where the original does.
- **`RuledGrid`**: `page` and `cells`, a tuple of `Rect` in **unrotated page coordinates**, one per cell,
  where a merged cell is one rectangle. It carries no bands and no indices: the core derives those in its
  own frame (§ 4). Validated: at least one cell, every rectangle of positive size.
- **`LatticeReading`**: `engine`, the `camelot` version, the `pages` read, the `grids`, and `findings`.

### Reading

`read_lattice(data, frames, pages, *, engine, password) -> LatticeReading`:

1. **One page at a time**, `camelot.read_pdf(data, pages=str(n), flavor="lattice", engine=engine,
   password=password, suppress_stdout=True)`, so a failure costs one page. Any exception becomes
   `lattice_failed` (warning) on that page, with the exception's type and message (L18).
2. **Never** `Table.df`, never `copy_text`, never an assignment to `Cell.text` (L1, L13).
3. **Merged cells** come from the edge flags. Two neighbouring cells belong together when the edge between
   them is drawn on neither side (`right` of the left cell and `left` of the right cell both false, or
   `bottom` of the upper cell and `top` of the lower cell both false). Each connected group becomes one
   rectangle when its cells fill that rectangle exactly; a group that does not is split back into its
   single cells, because a guessed merge would fuse values (L2).
4. **The frame.** Camelot's coordinates are y-up from the bottom-left of the copy's page, in the page's
   rotated frame when Camelot turned the page. It turned the page when `Table.pdf_size` is the page's
   height by width (a `/Rotate` of 90 or 270), or when the `/Rotate` is 180. A swapped `pdf_size` on a
   page whose `/Rotate` is 0 cannot be placed: `lattice_failed` for that grid.
5. **Conversion to unrotated page coordinates.** A point `(x, y)` in Camelot's frame is `(x, h − y)` on
   screen, with `h` the frame's height, and is then turned back by the page's rotation (`turn_point`
   inverted) when Camelot turned the page.

| # | case | expected |
|---|---|---|
| LC1 | the lattice copy of `ruled_grid` with an offset MediaBox, an inset CropBox, an inset CropBox and `/Rotate` 90 or 180, and `ruled_landscape`; an encrypted PDF | every word where the original has it; the copy is not encrypted |
| CM1 | `ruled_grid`: a 4 x 3 ruled table whose header spans columns 1–2 and whose label spans rows 1–2 | 10 cells; the header and the label as one rectangle each, at the drawn positions |
| CM2 | `ruled_grid` with MediaBox `[-100 -100 512 692]` | the same cells in page coordinates as the words |
| CM3 | `ruled_grid` with CropBox `[50 50 550 750]` | the cells shifted by (−50, −50), as the words are |
| CM4 | `ruled_grid` on a page of `/Rotate` 90, 180, and 270 (text horizontal in the unrotated page), each also with an inset CropBox | the cells where the words are, in each |
| CM5 | `ruled_landscape`: a grid upright on screen on a `/Rotate` 90 page, with and without an inset CropBox | the cells where the words are |
| CM6 | a Camelot failure on page 2 of 3 (injected) | `lattice_failed` on page 2; pages 1 and 3 read |
| CM7 | edge flags whose connected group is L-shaped | its cells stay separate |
| CM8 | CM1–CM5 with each `engine`: `vector`, `combined`, and `raster` | the same cells, within 1 pt |
| CM9 | `ruled_grid` encrypted with only an owner password (AES-256); with a user password, read with it | the table, both times |

---

## 3 · Which pages Camelot reads (`core/tables/pages.py`)

`lattice_pages(reading) -> tuple[int, ...]`: the pages with at least 2 horizontal and 2 vertical rules.
Camelot runs on nothing else, because it renders at 300 DPI (risk 4) and finds nothing on unruled tables
(L13).

| # | case | expected |
|---|---|---|
| LP1 | pages with (2 h, 2 v), (5 h, 1 v), (1 h, 3 v), (0, 0) rules | only the first |

---

## 4 · Grid shapes (`core/tables/shape.py`, pure)

`grid_shape(cells) -> GridShape | None` turns cell rectangles into a grid: the row edges are the sorted
distinct `y0`/`y1` values of the rectangles, the column edges the distinct `x0`/`x1` values, and each
rectangle becomes `(row, col, row_span, col_span)` from the edges it starts and ends on. The shape exists
only when the rectangles tile their bounding box exactly: every position covered once, none twice.
Otherwise it is `None`. Edges within 0.5 pt are one edge.

| # | case | expected |
|---|---|---|
| GS1 | the 10 rectangles of CM1 | 4 rows, 3 columns; the header `(0, 1, 1, 2)`, the label `(1, 0, 2, 1)` |
| GS2 | two overlapping rectangles; rectangles leaving a hole | `None` |
| GS3 | edges 0.3 pt apart | one edge |

---

## 5 · The table stage (`core/tables/lattice.py`, pure, per page)

`lattice_tables(page, grids, words, profile, *, frame, read) -> TableStage` takes one page (upright, as the layout
reads it), the page's ruled grids turned into that frame (`turn_rect`), and the page's content words (not
furniture). It returns the proto tables, the ids of the words they claim, and findings.

1. **Claiming.** A word belongs to a grid when its centre lies inside the grid's bounding box, and to the
   cell whose rectangle contains its centre, half-open (`[x0, x1) x [y0, y1)`), so assignment is a partition
   by construction.
2. **Acceptance.** A grid becomes a table only when it has at least 2 rows, at least 2 columns, and at least
   2 cells holding words, and when at least one of its columns is not a column of running text. A column
   is running text when its single-column cells hold prose by layout's test (at least `column_min_lines`
   lines, a mean of at least `prose_min_words` words per line) and one of them holds at least
   `2 x column_min_lines` lines. A grid whose every column is running text is a ruled page layout (a frame
   with a rule between two columns of text), not a table. Measured: the frame case holds 12 lines per
   cell; two-column fee tables of text on Cboe, PHLX, and Nasdaq hold at most 5, and stay tables.
   Otherwise the grid claims nothing, and its words stay for prose: a box around a paragraph, a furniture
   label, or a ruled page layout is not a table.
3. **Cell text.** A cell's words form lines (`group_lines`), read top to bottom and left to right, and the
   text rule of `04` § 6 applies within the cell: one space between words and lines, and recorded hyphen
   joins.
4. **Header rows** are the leading run of rows that each hold at least one word and no value cell. A cell
   is a value cell when its text without its superscript words `is_value`, or when one of those words
   `is_strong_value`: a fee with a note mark (`$0.0030` and a raised `1`), a code (`{CK} $0.00`), or a
   qualifier (`$5,000 per month`) is still a value. A full-width row, whose only cell with words is its first, ends the run
   once a row with several cells has been counted: a caption above the column headers belongs to the header,
   a section banner below them does not. A row's cells are the cells that start in it. When the run would
   cover every row, the table has no value rows to tell headers from: it has 1 header row when the first
   row's words are all bold, else none. With no header rows, the table raises `header_not_found` (info).
5. **Banner rows** are the rows, anywhere, that are full-width and hold no value.
6. **`word_crosses_rule`** (warning): one finding per table, with the count, when any claimed word's box
   extends more than 1 pt past its own cell's left or right edge into a neighbouring cell. A merged cell
   has no interior rule, so words inside it never cross. Vertical overhang is ordinary: MuPDF's line boxes
   span the font's full ascent and descent, so they reach past tight rows.
7. **`lattice_disagrees`** (warning): Camelot read the page and returned no grid at all. (A page whose grids
   were all rejected is not a disagreement: Camelot saw the rules.) The rule-grid fallback of design § 5.2
   arrives with M2b; until then the page's words stay for prose.

| # | case | expected |
|---|---|---|
| LT1 | `ruled_grid` | one table of 4 x 3; `Rate` is one cell over columns 1–2; `Equity` one cell over rows 1–2; header rows 1 |
| LT2 | a grid of one row, or one column, or with words in only one cell | no table; its words go to prose |
| LT3 | a word whose centre sits exactly on an interior edge | in the cell to the right (or below) of the edge |
| LT4 | a caption row spanning all columns, then `Service \| Fee`, then values | header rows 2; banner rows (0) |
| LT5 | `Description \| Type \| Fee`, then a full-width `Disk storage`, then values | header rows 1; banner rows (1) |
| LT6 | a table whose first row holds values | header rows 0; `header_not_found` |
| LT7 | a word straddling a drawn column rule by 3 pt | `word_crosses_rule` with count 1 |
| LT8 | a page Camelot read that returned no grid | `lattice_disagrees` on that page |
| LT11 | a first data row whose fee `$0.0030` carries a superscript `1` | header rows 1 |
| LT12 | header `Tier 1 \| Fee (47)`, then data `{CK} $0.00 \| $5,000 per month` | header rows 1 |
| LT13 | a 2 x 2 grid: a full-width title, then two cells of prose (6 lines of 7 words each); the same with one cell of short values; the same with cells of 4 lines | no table; one table; one table |
| LT10 | a table of text only, with a bold first row; the same with a regular first row | header rows 1; header rows 0 |
| LT9 | two lines of text in one cell, the first ending `execu-` and the second `tions` | cell text `executions`, one join |

---

## 6 · Pipeline and assembly

**Order.** Per page: furniture (document-wide) → **tables** (on the upright page, over its content words)
→ layout and prose over the words tables did not claim → assembly. Stage 3 claims before stage 4 (design
§ 4.4).

**Reading order.** A table goes before the first block of the page, in reading order, whose top lies below
the table's top; with none, after the page's content. Furniture keeps its places (`04` § 6).

**The `Table` block.**
- `grid`: the bands from the shape's edges (`row_bands` from the row edges, `col_bands` from the column
  edges), `n_rows`, `n_cols`, `header_rows`, `banner_rows`, `source = "lattice"`, and `frame`.
- `cells`: one per shape cell, with its span, its words' ids, its text, and its markers.
- `word_ids`: the cells' words in `(row, col)` order, then reading order within the cell.
- `text`: the rows' non-empty cell texts joined by one space, and the rows joined by `\n`; empty rows are
  left out.
- `regions`: one, the union of the grid's bounding box and its words, in unrotated coordinates.

**`Grid.frame`** (model change, `01-model.md`): `0`, `90`, `180`, or `270`, the rotation from the unrotated
page to the frame the bands are measured in. It is the page's rotation when the page was turned upright,
else 0. Invariant 15 turns each word's centre by `frame` (`turn_point`, over the page's unrotated size)
before testing it against the cell rectangle.

| # | case | expected |
|---|---|---|
| TP1 | `ruled_grid` through `inkgrid.read` | one `Table` block; every word of the grid is in it; a valid `Document` |
| TP2 | `table_between_paragraphs`: a paragraph, a ruled table, a paragraph | paragraph, table, paragraph |
| TP3 | `boxed_paragraph`: a 1 x 1 box around a paragraph | a paragraph, no table |
| TP4 | `ruled_landscape` | one table, rows in screen order (`Fee Rate Cap` first); a valid `Document` with `frame = 90` |
| TP5 | a `Document` whose table has `frame = 90`, with a word moved out of its cell (JSON) | `ValidationError` (invariant 15) |
| TP7 | `ruled_columns`: a page frame with a rule under its header and a rule between two columns of prose | no table; the left column's blocks, then the right column's |
| TP6 | the SIX-like `labelled_page`: a boxed furniture label on 3 pages | no table |

---

## 7 · Exports (`model/export.py`)

- **`Table.to_markdown()`**: a GFM pipe table. The first header row (or an empty header when there is
  none) is the GFM header; further header rows come first in the body. A merged cell's text appears once, in
  its first position, and the positions it covers are empty (L1). `|` in text becomes `\|`, and tag openings
  are escaped as in `05` § 2.
- **`Table.to_html()`**: a `<table>` with `<thead>` for the header rows, `<tbody>` for the rest,
  `colspan`/`rowspan` for merged cells, `class="banner"` on banner rows, and every string HTML-escaped.
- **`Table.to_rows()`**: dense rows, a tuple per grid row of `DenseCell(text, row, col, copy)`. Every
  position is filled; a position covered by a merged cell repeats its text with `copy=True`, so a consumer
  that expands spans can always tell a copy from a printed value (L1).
- **`Document.to_markdown()`** renders tables with `to_markdown`.
- **The inspector** draws each cell of a table as a thin rectangle inside the table's box.

| # | case | expected |
|---|---|---|
| EX1 | `to_markdown` on LT1's table | `\| Fee \| Rate \|  \|` header, then rows; `Equity` once, its covered position empty |
| EX2 | `to_html` on LT1's table | `<th colspan="2">Rate</th>` and `<td rowspan="2">Equity</td>` |
| EX3 | `to_rows` on LT1's table | 4 rows of 3; the positions covered by `Rate` and `Equity` repeat them with `copy=True`; nothing else is a copy |
| EX4 | a cell text `a \| b <b>` | Markdown `a \\| b \\<b>`; HTML `a \| b &lt;b&gt;` |
| EX5 | the inspector on `ruled_grid` | one `<rect class="cell">` per cell |

---

## 8 · API, CLI, and packaging

- `inkgrid.read(..., lattice=...)` accepts `combined` (the default), `vector`, and `raster`. It computes
  `lattice_pages` from the reading, runs `read_lattice` on those pages only, and passes the grids to
  `build_document`. `Producer.camelot` records Camelot's version whenever Camelot ran.
- `inkgrid read --lattice {combined,vector,raster}`.
- **Dependencies:** `camelot-py>=2.0.0,<3`, and `opencv-python-headless>=4.14.0.94,!=5.0.0.93` (the one 5.x
  release bundles an FFmpeg with CVE-2026-8461; design risk 6). inkgrid never imports OpenCV; the pin exists
  for the environments it creates.
- **Typing:** `typings/camelot/` declares the parts of Camelot the reader calls.
- **Layers:** only `read/camelot_reader.py` imports camelot (a new architecture case).
- **README:** the Licensing section names Camelot's MIT license; "What it does" and the known limitations say
  what M2a reads (ruled tables) and what it does not yet (unruled tables, M2b).

| # | case | expected |
|---|---|---|
| AP1 | `read(ruled_grid(), lattice="vector")` | `producer.lattice == "vector"`, `producer.camelot` set |
| AP2 | `read(simple_text())` | Camelot does not run; `producer.camelot is None` |
| AP3 | `inkgrid read ruled.pdf --lattice raster` | exit 0; a `Document` with a table |
| AP5 | `read(ruled_grid(cropbox=(10, 10, 602, 782)))` with the default engine | one 4 x 3 table |
| AP6 | `read(ruled_encrypted("secret"), password="secret")`; `read(ruled_encrypted(None))` | one table each |
| AP4 | the architecture test with `read/words.py` importing camelot | one violation |

---

## 9 · Acceptance

- [ ] VL1–VL5, LC1, CM1–CM9, LP1, GS1–GS3, LT1–LT13, TP1–TP7, EX1–EX5, and AP1–AP6 pass.
- [ ] The seven fee schedules read without error, with Camelot's tables claimed as in § 0.
- [ ] Every M0 and M1 case still passes.
