# 07 · Unruled tables: whitespace corridors (M2b)

**Implements:** `00-design.md` § 4.3 stage 3 (unruled part) and lesson L11: "Unruled columns come from
whitespace corridors, derived from data rows, clustered per line and then merged, and a cell's extent
covers its own words."
**Modules:**
- `core/tables/proto.py`: `ProtoCell`, `ProtoTable` (now with a `source`), `cell_lines`, `table_roles`,
  moved out of `core/tables/lattice.py` so both gridders share them;
- `core/tables/corridor.py`: value pieces, rows, columns, boundaries, cells, and `corridor_tables`;
- `core/tables/grid.py`: `Grid.source` from the proto table;
- `core/pipeline.py`: the corridor stage between layout and prose.

---

## 0 · What was measured first (L19)

A sketch of this spec ran over SIX, LSE, and Euronext on 2026-09-26 (the three fee schedules whose
tables Camelot does not read).

- **SIX draws horizontal rules only**, so no page reaches Camelot. Its fee tables are 9 pt rows about
  3 pt apart; section headings are 10 pt bold, 12–33 pt above; a wrapped header line sits 0 pt under
  its row. Money is right-aligned, so the whitespace *between* columns is stable while left edges are
  not (L11).
- **LSE centres a value beside a two-line label**, 4.9 pt above the label's second line, with rows at a
  9.3 pt pitch. Bold full-width lines are section banners. A header can be one right-aligned cell
  (`Charge`).
- **Euronext sets several thresholds in one ruled cell** (`First 700,000 executed orders` … with
  `€0.13 €0.08 €0.05` beside them). Folding those lines into one row would put three values in one cell,
  the fusion L2 forbids, so a line whose value falls in a column that already holds one in its row always
  starts a new row.
- **Layout's `rows` regions are not tables.** A rows region runs on past a table into the headings and
  paragraphs below, and one table can straddle two adjacent rows regions. The corridor stage finds
  tables inside runs of adjacent rows regions.
- **Result of the sketch:** SIX 100 tables (the prototype measured 121), LSE 8, Euronext 33. By eye, all
  sampled ones are tables; 23 of SIX's are a header row over a single value row.
- **Not in M2b: the rule-grid fallback** of design § 5.2 (a lattice built from our own vector rules when
  Camelot fails or disagrees). Camelot's `vector` engine is itself a reading of those vector rules, so a
  second reader of the same paths adds no independence; a page Camelot fails on keeps `lattice_failed`,
  and its words reach the corridor stage like any other.

---

## 1 · Value pieces (`core/tables/corridor.py`)

A *piece* is a fragment (`04` § 2): words of one line closer than `fragment_gap_em` × size.
`is_value_piece(words) -> bool` decides whether a piece is a value cell that can make a row a value row.
Superscript words are left out first (note marks). The piece is a value piece when its remaining text
`is_value` and contains a strong value token (`06` § 1), or when it has at most 4 tokens and its first
token is a strong value (`$5,000 per month`, `0.10 per contract`).

`is_value_like(words)` is looser: the remaining text `is_value` (weak values included: `1 – 150`, `62`,
`Free`, `-`). It guards row folding (§ 2).

| # | case | expected |
|---|---|---|
| VP1 | `0.25 bp`, `CHF 0.50`, `$5,000 per month`, `0.10 per contract`, `-0.15bp`, `£30,000` + a superscript `****` | value pieces |
| VP2 | `Section 2.1`, `Tier 1`, `1 – 150`, `Free`, `-`, `The fee is CHF 1.00 per trade`, `62` | not value pieces |
| VP3 | `is_value_like` on `1 – 150`, `62`, `Free`, `-`; on `Tier 1`, `Commitment` | true; false |

---

## 2 · Rows (`fold_rows`)

`fold_rows(lines) -> tuple[Row, ...]` groups consecutive lines into table rows. A `Row` holds its lines
top to bottom; its size is the median size of its words.

- A line's *pitch* is the distance from the top of the line before it to its own top. A line joins the
  row above when its pitch is at most 0.8 × the median pitch of the lines given, **unless** it holds a
  value-like piece that overlaps horizontally a value-like piece already in that row. Then it starts a new
  row: two values in one column are two rows, never one cell (L2).
- **A drawn rule ends a row.** A line never joins the row above across a horizontal rule of the page
  that lies between the centre of the line before it and its own centre and overlaps it horizontally.
  Euronext rules its rows while centring each value beside a two-line label, so the first label line of
  a row sits tight under the row above; the rule, not the pitch, says where it belongs. (This is the
  part of design § 5.2's rule grid that unruled reading needs: rules as row boundaries. Pages read
  upright in a turned frame carry no rules, `04` § 2a, and fold by pitch alone.)
- Pitch, not gap, because MuPDF's line boxes span the font's full ascent and descent (1.38 em for base-14
  Helvetica), so rows set at ordinary leading overlap and their gaps are negative, like a wrap's. Measured
  pitch over the block's median: SIX wraps 0.76, rows 1.0; LSE wraps 0.28–0.55, rows 1.0.

| # | case | expected |
|---|---|---|
| RW1 | a header line, then its wrap 0 pt below, then rows 3 pt apart | the wrap joins the header row; each value line is its own row |
| RW2 | three lines 0.5 pt apart, each with a value right-aligned in the same column (Euronext) | three rows |
| RW3 | a two-line label with its value centred between the lines, 4.9 pt above the second (LSE) | one row of three lines |
| RW4 | lines 9 pt apart in a block whose median gap is 9 pt | one row each |
| RW7 | a row's value, then the next row's first label line 1 pt below, a drawn rule between them, and its value below | the label line starts the next row |
| RW6 | 9 pt rows at a 12 pt pitch, whose boxes overlap by 0.4 pt, under a bold header | one row each |
| RW5 | `151 – 500` 0 pt above `501 – 1,000`, in the same column | two rows |

---

## 3 · Table extent (`table_runs`)

A *candidate* is the lines of a maximal run of adjacent regions of one page that stack: each region's first
line starts below the top of the previous region's last line. Side-by-side prose columns start level, so
they never stack and are never one candidate; stacked regions whose boxes overlap by a point or two (MuPDF's
tall line boxes) still do. Layout's `rows` regions hold most tables, but a table of two rows, or one whose
label column reads as prose, lands in a prose region (layout needs `column_min_lines` rows to see a
gutter). A candidate without a table passes through unchanged. Its lines
are split into *size runs* wherever a line's size differs from the previous line's by more than
`size_change_ratio` × the smaller of the two, and each size run is folded into rows (§ 2) on its own, so
the pitch of the headings around a table never sets the pitch its rows are measured by.

In each size run:

1. **Value rows** have at least 2 pieces, and a value piece other than their leftmost.
2. **Columns** (§ 4) are computed from the value rows. With fewer than 2 columns there is no table.
3. The table runs from its first value row through each following value row whose rows in between all
   align (item 4) with the columns of the value rows so far: banners, label rows, and value-free rows such
   as `Commitment | No commitment required` stay in. A row between that does not align ends the table at
   the value row before it.
4. **Aligned rows.** A row *aligns* when all its pieces lie within the table's width (from the first
   column's start to the last column's end, give or take half the run's size) and each piece is anchored,
   within half the run's size: its start at a column's start, its end at a column's end, or its centre at
   the centre of a span of consecutive columns. A sentence that runs past the columns does not align, even when it starts where
   they do.
5. **Upward**, the table takes up to 3 preceding rows, nearest first, while each holds no value piece and
   aligns: the column header, and a caption or a banner above it.
6. **Downward**, it takes following rows while each has at least 2 pieces and aligns.
7. **Acceptance:** at least 2 rows. A size run can hold several tables: after one, the search resumes at
   the first row after it.

| # | case | expected |
|---|---|---|
| EX1 | a 10 pt bold heading, then a 9 pt table | the heading is not in the table |
| EX2 | a caption, a bold header `Fee \| Floor \| Scale \| Cap`, then value rows | the caption and the header are rows 0 and 1 |
| EX3 | a 9 pt sentence spanning the page above a narrower table | not in the table |
| EX4 | a trailing `Commitment \| No commitment required` row | in the table |
| EX5 | a trailing bullet line `■ \| Members paying the fee …` whose text runs past the columns | not in the table |
| EX6 | a bold full-width banner between value rows | in the table |
| EX7 | a table whose last row starts the next rows region | one table |
| EX8 | two tables in one size run, a value-free, unaligned line between them | two tables |
| EX9 | a header row over a single value row | a table of 2 rows |
| EX11 | a two-row table (`First 1,000 executed orders \| €0.60` over `Subsequent executed orders \| €0.30`) in a prose region | one table |
| EX12 | two prose columns side by side whose lines hold values at the same heights | never one candidate: no table across the columns |
| EX13 | a centred label's first line in a prose region whose box overlaps the table's rows region by 1 pt | one candidate: the line joins the table |
| EX10 | 10 pt headings 25 pt apart around a 9 pt table whose rows are 15 pt apart | the table's header and rows stay apart |

---

## 4 · Columns and boundaries

- **Columns** are the connected components of the union of the value rows' piece extents. Two pieces
  that overlap in x, in any value rows, are in one column.
- **Boundaries.** Between two consecutive columns lies a *corridor*, and every row of the table votes on
  where in it the boundary goes:
  - a row's *blanks* are the parts of the corridor none of its words cover, at least half the row's size
    wide (narrower gaps are word spacing, not column space); a row with no blank abstains;
  - the candidates are the corridor's midpoint and the midpoint of every blank;
  - a candidate scores +1 for each row with a blank that contains it, and −1 for each row whose blanks
    all miss it; the best score wins, and a tie goes to the candidate farthest from any word.

  So a long label in a value-free row (`Securities in the uncleared market …`) stays in its column, a
  header's own column break wins inside a wide data corridor, and a spanning header whose only blanks are
  word spacing abstains and keeps its span. (A plain "widest blank in every row" would pick the 2 pt word
  gaps inside `Trades executed via STI` and split it.)
- The column bands run from the table's leftmost word start, through the boundaries, to its rightmost word
  end plus 0.01 pt (half-open, as `06` § 5).

| # | case | expected |
|---|---|---|
| CB1 | value rows `a) Poster \| - \| 1.00 bp \| -` and `b) Aggressor \| CHF 0.50 \| 0.55 bp \| -` | 4 columns |
| CB2 | a value-free row whose label reaches 20 pt into the corridor | the boundary sits past the label, and the label stays in column 0 |
| CB3 | a header word centred across a corridor, with no blank in every row | the boundary at the corridor's midpoint; the word's cell spans both columns |

---

## 5 · Cells and the grid

1. **Pieces are split at boundaries.** Within a row, each fragment is split wherever a boundary falls in
   the gap between two of its words, so `During continuous trading` and `Auction & TAL executions`, set
   less than a fragment gap apart, land in their own columns (L11: per line, then merged).
2. Each piece covers the bands from the band of its start to the band of its end. Pieces of one row that
   share a band merge into one cell, spanning the union of their bands. A position no piece covers is an
   empty cell.
3. A cell's lines are its words by `cell_lines` (`06` § 5), and its text follows the text rule.
4. **Row bands** run from the first row's top to the last row's bottom. The edge between two rows is the
   midpoint of the gap between them, clamped between the upper row's lowest word centre and the lower
   row's highest; when those interleave, there is no table.
5. **Never fuse (L2).** A table where any cell would hold two value-like pieces is not a table: its words
   go to prose.
6. Row spans are 1. Header and banner rows come from `table_roles` (`06` § 5), and `header_not_found` is
   raised as for ruled tables. The grid's `source` is `corridor`.

| # | case | expected |
|---|---|---|
| CG1 | SIX's two-line header `Trades executed via STI \| Trades executed via OTI` over five value columns | the header cells span columns 1–2 and 3–4 |
| CG2 | `During continuous trading` and `Auction & TAL executions` less than a fragment gap apart | two cells |
| CG3 | `Commitment \| No commitment required` under 4 columns | `No commitment required` spans columns 2–3; column 1 is an empty cell |
| CG4 | two values in one column of one row, bridged by a wide cell in another row | no table |
| CG5 | a valid corridor table built into a `Document` | valid: every word's centre in its cell, cells tiling the grid |

---

## 6 · What is not a table

| # | case | expected |
|---|---|---|
| NT1 | a hanging-indent list whose items mention a fee inside their text (`a) \| The fee is CHF 5 per trade.`) | no table |
| NT2 | a table of contents (`1.2 Ad valorem fee` … `7`) | no table |
| NT3 | one value row with nothing aligned above or below | no table |
| NT4 | a single column of values | no table |

---

## 7 · Pipeline

Per page, after layout: the corridor stage runs on each candidate (§ 3) with the page's horizontal rules,
claims the words of its tables' rows, and returns the other lines as regions of their own kind in their
places. Prose runs on those,
and assembly places corridor tables among the page's blocks exactly as ruled tables (`06` § 6).

| # | case | expected |
|---|---|---|
| CP1 | `unruled_table`: a heading, an intro sentence, a SIX-style table with a trailing `Commitment` row, and a heading | heading, paragraph, table, heading; the table has 5 rows and 4 columns |
| CP2 | `centred_values`: an LSE-style table with two-line labels, centred values, and a bold banner | one table; each value in the row of its label |
| CP3 | `ruled_and_unruled`: a ruled table and an unruled table on one page | two tables, sources `lattice` and `corridor` |
| CP4 | `unruled_landscape`: an unruled table upright on a `/Rotate` 90 page | one table with `frame = 90`, rows in screen order |
| CP5 | every `OPENABLE` fixture | a valid `Document` |

---

## 8 · Acceptance

- [ ] VP1–VP3, RW1–RW7, EX1–EX13, CB1–CB3, CG1–CG5, NT1–NT4, and CP1–CP5 pass.
- [ ] The seven fee schedules read without error; SIX, LSE, and Euronext gain their unruled tables, and
      a sample of them, rendered in the inspector, reads as the page prints.
- [ ] Every M0, M1, and M2a case still passes.
