# 14 · Tables and furniture on public corpora: rules, extents, charts, watermarks (M5c-2)

**Implements:** the table and furniture half of spec 11 § 5's "what stays reported", after M5b
recorded the baseline (`12-benchmark.md`, `DR-0023`), and the benchmark's tuned run. It amends
`02-reader.md` (§ 5), `04-text-pipeline.md` (§ 3), `06-ruled-tables.md` (§§ 2, 5), `07-unruled-tables.md`
(§§ 1, 3, 6), `01-model.md` (`Word`, `PageModel`, `RuledGrid`, findings), and `12-benchmark.md` (§ 7's
results path, for a tuned run).
**Modules:**
- `read/rules.py`: thin fills (§ 1); `read/pymupdf_reader.py` and `model/page.py`: filled shapes and
  diagonal words (§§ 6, 7);
- `read/camelot_reader.py` and `model/lattice.py`: a frame's core (§ 4.2);
- `core/tables/lattice.py`: overlapping grids (§ 4.1), a frame's core (§ 4.2), splitting cells at the
  page's rules (§ 2), charts (§ 6), diagonal words (§ 7);
- `core/tables/corridor.py`: a drawn rule ends a piece (§ 3), foreign words (§ 5), charts (§ 6);
- `core/tables/chart.py` (new, pure): the chart evidence (§ 6);
- `core/furniture.py`, `core/pipeline.py`: furniture and tables (§ 8);
- `bench/inkgrid_bench/{run,report}.py`: the tuned run (§ 9).

**Tuned.** Every rule here was designed while looking at ICDAR-2013 and olmOCR-bench's failures; the
benchmark run after them is labelled as tuned on those sets (DR-0023). The 42 fee schedules and the
fixture suite guard against regressions; M5d's held-out fee set is the test no fix has seen.

---

## 0 · What was measured first (L19)

Each class was traced on 2026-09-29 from Camelot's grids and edge flags, the drawings as PyMuPDF and
PDFium see them, and rendered crops; each rule was prototyped in memory and run one document at a
time over the named documents and the 42 fee schedules (1,084 tables, 951 Camelot grids).

- **A drawn rule the grid misses (32 defects).** Practice us-008 draws its column rules as fill-only
  grey rectangles 2.75 pt wide; the reader drops fills thicker than 2.5 pt as backgrounds, and
  Camelot's vector engine turns a fill into a line only up to 1.5 pt, so two printed columns fuse.
  olmOCR 008d1d's column rule starts 2.68 pt above the header's bottom edge, and Camelot drops a
  vertical segment whose end is more than 2 pt from a row edge. Practice us-012's table has no
  Camelot grid; its label and first value sit 9.5 pt apart at 11 pt with a drawn rule between, less
  than the fragment gap, so the corridor stage reads them as one piece. The thickest word-free fill
  in any corpus is 3.24 pt (fee-schedule dividers); the thinnest fill holding a word is 4.08 pt.
- **Table extent (114).** Camelot returns every joint inside an outer contour's box, so a page
  panel, a page-scale grid, or an open `]` frame around a table yields a second, larger grid over the
  same table (practice us-021, olmOCR 1529b2, competition us-036); the first-come claim gives the table
  to the smaller one and the headings and prose around it to the larger one's margin cells. A page
  border or image panel around a table yields one grid: the frame, whose ring of open cells
  (drawn top and bottom only, or left and right only) the merged-cell reading splits into single
  cells, cutting headings, paragraphs, and page numbers into columns (practice us-022, olmOCR c45171).
  A corridor table's outer edge can reach past another block's word centre (olmOCR 2d0e05, b8d3ad).
  The fee schedules have no overlapping grid pair, no trimmed frame, and no table extent holding
  another block's word centre.
- **Charts (17).** A plot box with ticks gives Camelot a grid (competition eu-027, us-028; olmOCR
  2ad3ea); evenly placed bar labels read as corridor rows (competition eu-012, us-001; practice eu-018;
  olmOCR 83b820). Bars are filled rectangles proportional to their labels (residuals at most 1.3%); a
  numeric axis is an arithmetic run of labels, each at a perpendicular tick. Neither holds in any of
  the 1,084 fee tables once proportionality is required: shaded rows share an edge and differ in
  length, but not in proportion to a number.
- **A diagonal watermark (3, olmOCR 1ec1f9).** `For Peer Review` at 51.5° is claimed by cell centre.
  No fee-schedule cell holds a non-horizontal word.
- **Furniture inside tables (27).** Furniture keys need only 2 pages on a 3- or 4-page document, and a
  key once marked is marked everywhere. A spanning header (`THRESHOLD FOR RELEASES`, competition eu-001),
  a column-group header (`Age 4` / `Age 3`, us-007), a banner row and a header cell's second line
  (practice us-006), and a stub banner (`Actual`, us-017) repeat in a page band and were taken as
  running headers, removed from their tables. The furniture stage runs before any table exists.

**Prototype result:** all 193 defects of these classes but one gone, none new (the one left, a title
word straddling Camelot's header-row edge on us-008, is an extent case § 4 does not reach); the fee
schedules read identically bar one column edge moved 2 pt onto its drawn rule.

---

## 1 · Thin fills are rules (`read/rules.py`, amends `02-reader.md` § 5 R2)

- **R2, amended:** a rectangle whose shorter side `t` is at most **3.5 pt** (was 2.5) and whose longer
  side is at least 2.0 pt is one rule along its long axis. The verifier keeps its own 3.0 pt threshold
  (`10-verify.md` § 1.4): the two differ on purpose, and a rule only the reader keeps can split a cell
  (§ 2) but never hides a verifier defect.
- **Why 3.5 pt:** the thickest word-free fill measured is 3.24 pt, and the thinnest fill holding a word
  4.08 pt.

## 2 · Ruled grids split at the page's rules (`core/tables/lattice.py`, amends `06` § 5)

After a grid is **accepted** (never before: a rejected one-row grid on a fee schedule would split at
invisible 1.56 pt fills), its cells are split at the page's own rules, merged first (same axis, `at`
within 0.25 pt, gaps of at most 0.5 pt):

- a cell splits at a merged rule when the rule lies more than 1.5 pt inside both of the cell's edges
  across it, reaches within 1.5 pt of both of the cell's ends along it, and the cell's words, by
  centre, lie on both sides;
- splitting repeats until nothing splits; header and banner rows are then read again.

Every threshold is stricter than the verifier's VRULE and HRULE tests (1.0 and 2.0 pt, merged at 0.5
and 1.0 pt), so at a rule both read, a split happens only where the verifier would have reported a
drawn rule dividing a cell. A fill 3.0 to 3.5 pt thick is a rule to the reader and shading to the
verifier (§ 1), so a split at one has no independent check. Halves are half-open, so every claimed
word keeps exactly one cell.

## 3 · A drawn rule ends a corridor piece (`core/tables/corridor.py`, amends `07` § 1)

Between two consecutive words of a line, a page's vertical rule ends the piece when its `at` lies in
the gap between them and its extent covers both words' vertical centres, as a drawn horizontal rule
already ends a row (§ 2 there). A short tick crossing only one word's centre does not.

## 4 · Grid extent

### 4.1 Overlapping grids (`core/tables/lattice.py`)

A page's grids are taken in ascending order of their boxes' areas (after § 4.2). A grid whose box
overlaps an already accepted table's box by at least 1.0 pt on both axes is not a table and claims
nothing. Grids that share only a border overlap by at most 0.5 pt (`shape.SNAP`).

### 4.2 A frame's core (`read/camelot_reader.py`, `model/lattice.py`, `core/tables/lattice.py`)

- On Camelot's lattice (R rows × C columns, a line drawn when either neighbouring cell flags it),
  `K = rows [r0, r1) × columns [c0, c1)` is a **core** when:
  1. K's boundary is drawn along its full length;
  2. every row outside K has no drawn vertical line strictly inside `(c0, c1)`, and every column
     outside K no drawn horizontal line strictly inside `(r0, r1)` (the corners are unconstrained);
  3. K is at least 2 × 2 cells;
  4. the lattice extends past K on both the left and the right, and above or below it.

  The largest core is taken (each column pair `(c0, c1)` is tried; `r0` and `r1` are the first and last
  rows with a drawn interior vertical line in that span). `RuledGrid.core: Rect | None`, in unrotated
  page coordinates, lies inside the grid.
- The table stage uses only the core's cells when no content word's centre lies in a cell beside the
  core: a grid cell left or right of the core that shares its rows, over the cell's whole extent
  (within 0.5 pt). A frame's side margins are blank; a real table's side columns are not (three fee
  tables with a spanning header row and a row-spanning label column hold 48, 9, and 1 words there),
  even when their text is top-aligned in a cell that also spans the header row (FR4).

## 5 · A corridor table's extent holds no foreign word (`core/tables/corridor.py`, amends `07` § 3)

`corridor_tables` takes the page's content words. Then:
- a row taken upward or downward (§ 3 items 5 and 6 there) is not taken when another word's centre lies
  within that row's vertical extent and the table's width;
- when a word outside the table within its width has its centre inside the table's top or bottom
  band (between the outer edge and the outer row's nearest word centre), that edge follows the
  interior-edge rule (§ 5 item 4 there) against the nearest such word: the midpoint of the gap,
  clamped between that word's centre and the row's nearest word centre. An edge only ever moves in,
  and a table with no such word keeps its edges exactly;
- an extent that still holds a foreign word's centre is refused through the existing path
  (`table_left_as_text`).

## 6 · A chart is not a table (`core/tables/chart.py`, used by both gridders)

- **Filled shapes.** `PageModel.fills: tuple[Rect, ...]`: the page's visible filled `re` and
  axis-aligned `qu` rectangles thicker than 3.5 pt on both sides (the rules' threshold, § 1), turned
  with the page's words when layout reads it upright (`04` § 2). The upright view carries no rules,
  so E2 does not reach a turned page; E1 does (practice eu-018's bars are on a `/Rotate 90` page).
- A table candidate from either gridder is refused, its words left for prose, with one info finding
  **`chart_left_as_text`** per chart, when its extent holds either piece of evidence:
  - **E1, proportional bars:** at least 3 fills meeting the extent that share one baseline edge
    (within 0.5 pt) and one thickness (within 0.5 pt) and are pairwise disjoint across the baseline.
    Every bar of the group pairs with a numeric word (value > 0): the only word whose centre lies
    inside the bar's span across the baseline and, along it, inside the bar or beyond its far end by
    at most 1.5 × the word's size plus half the word's extent along the bar (its near edge within
    1.5 × its size). A group with a bar that pairs with no word, or with two, is no evidence: a
    table's in-cell data bars pair only where a value sits near its bar's end (CH6). The words hold
    at least 3 distinct values and the bars at least 3 distinct lengths (more than 1 pt apart), and
    one factor k fits every pair: `|length − k·value| ≤ max(1 pt, 3% of length)`.
  - **E2, a ticked numeric axis:** at least 3 numeric words on one line or one column (each centre
    within 3 pt of the next across the line, so right-aligned labels of different widths are one
    column), all of whose values are an arithmetic progression (step constant within 0.1%) evenly
    spaced (gaps within max(1.5 pt, 5%)), each with a page rule perpendicular to the axis within
    1.5 pt of its centre coordinate, the rule's near end within 2 × the word's size of the word, the
    rule not running through it, no perpendicular rule between them, and no text divided by the
    rule: a rule with words of the extent along it on both sides, within 2 × the label's size, is a
    row rule (a sub-row rule beside a tier number, CH7).
- A numeric word prints a number: an optional sign (`-`, `+`, `−`), currency (`$`, `€`, `£`),
  digits with thousands commas or none, a decimal part after `.` or `,`, and `%`, in parentheses or
  not. `1,400` is 1400 and `1,4` is 1.4; `1,400,5` is no number.
- Both gridders are guarded: once the lattice refuses a chart, the corridor stage would otherwise read
  one from its labels. The lattice stage returns the extents it refused; a grid over a refused chart
  is skipped like one over an accepted table (§ 4.1), and the corridor stage drops a found table
  whose extent holds a chart whole (its rows go to prose), reporting it only when it overlaps no chart
  already reported.

## 7 · Diagonal words are no cell's (`read/words.py`, `core/tables/`)

- `Word.diagonal: bool = False`, set when the line's direction is 15°–75° from the horizontal, modulo
  90° (the verifier's overlay band, spec 11 § 3.2); a diagonal word is not horizontal (validated).
- Neither gridder claims a diagonal word, and a diagonal word is no foreign word to a corridor
  table's extent (§ 5; DG3). Layout already makes such words a block of their own.

## 8 · Furniture and tables (`core/furniture.py`, `core/pipeline.py`, amends `04` § 3)

The furniture stage takes the page's ruled tables as the lattice stage accepts them over all of the
page's words, before furniture exists: a frame's core, not the frame (§ 4.2); no ruled page layout;
no grid over a table (§ 4.1); no chart (§ 6). Camelot's raw grids would make a page border's running
header and page numbers content (FT5).

- **S1. A line inside a ruled table is table content.** A line is never a furniture candidate, and
  never marked, when every word centre of it lies inside the cells of one grid on the page that has at
  least 2 rows and 2 columns, and at least 2 of its other cells hold a word centre (the lattice
  stage's own acceptance values). A table whose texts, digits masked, recur on as many pages as a
  furniture key needs is a running header or footer drawn as a box, and S1 skips it (FT6).
- **S2. Furniture runs from the page's edge.** A line is a candidate only when every line between it
  and its band's page edge (by centre: above its top in the top band, below its bottom in the bottom
  band) is a candidate too. A column-shaped line (3 or more fragments), a stacked line, or an S1 line
  breaks the run; an ordinary heading or caption does not. A band's outermost line breaks no run
  when it is the band's only column-shaped line, and neither stacked nor a table's: a footer set in
  three parts (left, centre, right) is no table row (FT7).
- Rejected: requiring everything between a line and the edge to be furniture already. It loses a
  real running footer line whose line below it, nearer the edge, mirrors its word order between pages
  (practice eu-030: `ECB` above `S 1 Monthly Bulletin March 2006`).

## 9 · The tuned run (`bench/`, amends `12-benchmark.md` § 7)

The benchmark runs again at this milestone's final commit, unchanged but for its label: `run.py
--label tuned` writes `bench/results/<date>-<commit>-tuned/`, whose report says "tuned on these
documents" in its title and first paragraph. The baseline stays; `latest.md` points to the newest run;
README shows the baseline and the tuned run side by side, each labelled.

---

## 10 · Cases

| Case | Input | Expected |
|---|---|---|
| RU1 | a fill-only rectangle 2.75 × 248 pt | one vertical rule, thickness 2.75 |
| RU2 | fill-only rectangles 3.6 × 90 and 4.08 × 11 | no rule |
| LS1 | a ruled table whose column rules are grey fills 2.75 pt wide (practice us-008) | the columns apart; verification clean |
| LS2 | a column rule starting 2.7 pt above the header's bottom (olmOCR 008d1d) | the columns apart; the header cell spanning both stays one cell |
| LS3 | typed: a rule stopping 3 pt short of the cell's end; a rule 1.2 pt inside the cell's edge; words on one side only | no split |
| LS4 | typed: a rejected one-row grid over thin fills | no table, no split |
| CR1 | a label and a value 9.5 pt apart at 11 pt with a drawn vertical rule between (practice us-012) | two pieces; the table's columns `Area \| Army \| Navy` |
| CR2 | typed: a short tick crossing only one word's centre | one piece |
| GO1 | a `]` frame (two page-width horizontal rules and a vertical one) around a heading and a 4 × 3 table | one table; the heading prose |
| GO2 | typed: two grids sharing a border | both tables |
| FR1 | a page-border rectangle 36 pt in, around a heading, a paragraph, a 4 × 3 ruled table with blank side margins, a footnote, and a page number | one 4 × 3 table; the rest prose |
| FR2 | typed: the frame-core search on us-022's and c45171's flag maps; on a caption-in-box map | cores found; no core |
| FR3 | typed: a spanning header row with a row-spanning label column whose side band holds words | the whole grid kept |
| FR4 | FR3's table whose label and note columns span the header row too, their text top-aligned (R12) | the whole 6 × 4 grid kept |
| CX1 | typed: a word above a corridor table whose centre sits 0.1 pt below the first row's top | the edge clamped; the word not in the table |
| CX2 | typed: another region's word on a value-free upward row | the row not taken |
| CX3 | typed: a foreign word between value rows | the extent refused; `table_left_as_text` |
| CH1 | a boxed bar chart: 5 bars at 1.88 pt per unit, labels above, category ticks | no table; `chart_left_as_text` |
| CH2 | typed: axis labels 0, 10, 20, 30 with ticks at their centres | chart evidence |
| CH3 | typed: shaded rows sharing the table's edge, lengths not proportional to values; equal-length fills; tiers `1…4` beside sub-row rules in the next column; year columns | no chart evidence |
| CH4 | the CH1 chart after the lattice refuses it | the corridor stage refuses it too |
| CH5 | the CH1 chart upright on screen on a `/Rotate 90` page | no table; `chart_left_as_text`; the view's fills turned with its words |
| CH6 | a ruled 7 × 3 table with in-cell data bars, 4 of 6 paired with their values (R4); typed: 4 bars, one without its number | one 7 × 3 table, no `chart_left_as_text`; no chart evidence |
| CH7 | tier numbers level with the rule between each tier's two sub-rows, which starts at the next column (R5); typed: the same rules with and without the sub-rows' text | one table, no `chart_left_as_text`; ticks without the text, none with it |
| DG1 | a ruled table with `DRAFT` and `COPY` at 45° across it | no cell holds them; one prose block; verification clean |
| DG3 | an unruled 9 × 3 table under a 45° `DRAFT` (the final review's R3) | one 9 × 3 table; verification clean |
| DG2 | typed: a word at 90°; at 10°; at 51.5° | not diagonal; not diagonal; diagonal |
| FT1 | three pages, a table whose spanning header sits in the top band on pages 2 and 3, and a real footer | the header stays in the table; the footer is furniture |
| FT2 | three pages, a stub banner between a table's header and its rows, and a real running header and page number | the banner stays in the table; header and page number are furniture |
| FT3 | two pages whose footer line `ECB` sits above a line, nearer the edge, that mirrors its word order between pages | `ECB` is furniture |
| FT4 | `labelled_page` (spec 04 TP6) | its label stays furniture |
| FT5 | 3 pages, a page border around a running header, a table, and a page number; a bordered two-column newsletter (R1) | the header and page numbers are furniture |
| FT6 | 3 pages, each with a ruled 2 × 2 running-header box (R11); typed: the same box on 3 pages | the box's lines are furniture, no table |
| FT7 | 3 pages, a copyright line above a footer in three parts nearest the edge (R2) | the copyright line is furniture on each page |
| TR1 | `run.py --label tuned` on a stub run | results under `<date>-<commit>-tuned/`; the report's title says tuned |

Every existing case keeps passing.

## 11 · Acceptance

- [x] Every case above has a test named `test_<CaseId>_<slug>`, and it failed before its code (GO2,
      LS3, LS4, CR2's short tick, and FT3 guard what must not change and passed before it; FT4 is
      TP6, run with the grids passed; the clause tests added after their code were each checked by
      removing the clause and watching the test fail).
- [x] On the named documents, one at a time: the defects of these classes are gone, but for the one
      § 0 predicted, and none is new.
- [x] The 42 fee schedules read as before, with their 8 cells: their text dumps are byte-identical.
- [x] Every `OPENABLE` fixture verifies with no defect; `docs/schema/` is regenerated.
- [ ] The benchmark's tuned run is committed beside the baseline; README shows both, labelled, and
      states only what the intervals support.

**Measured** (2026-09-30, the M5c gate at `71437bc` against M5c-1's final reading, one document at a
time): the 31 named documents' defects fall from 217 to 25 (316 at the baseline). Of § 0's 193,
192 are gone: the drawn rules (practice us-008 22, us-012 4, olmOCR 008d1d 5), the extents (practice
us-021 47, us-022 16, olmOCR 1529b2 22, c45171 9, b8d3ad 2, 2d0e05 1, competition us-036 17), the
charts (competition eu-012 3, us-028 3, eu-027 2, us-001 1, olmOCR 2ad3ea 4, 83b820 3, practice
eu-018 1), the watermark (olmOCR 1ec1f9 3), and furniture (competition eu-001 7, us-017 12, us-007 2,
practice us-006 6). The one left is us-008's title word straddling Camelot's header-row edge. The
other 24 were there before and are outside these classes: 17 glyphs of a symbol font on us-008's
second page, 5 dashes and tildes on 008d1d, a word on us-001 that PDFium does not show, and a run of
digits on 1ec1f9 read as one value. No document gains a defect.

eu-018's bars are on a `/Rotate 90` page. The gate first measured them still read as a table,
because the upright view dropped its fills; it now turns them with its words (§ 6, CH5).

**After the final review** (the gate at `46959b8`): the review's seven reproductions (a page
border's furniture, data bars, sub-row rules, top-aligned side cells, a watermark over an unruled
table, a running box, a three-part footer) are fixed as DG3, CH6, CH7, FR4, and FT5 to FT7. The
named documents keep their 25 defects, none new; three read better and no worse: practice us-021 and
us-022's running header and page numbers inside a page border are furniture again, as at the
baseline (Task 6 had made them content; the verifier cannot see furniture), and olmOCR c8cdd4's
table reads whole, its title and column headers included, where a core had cut it into a heading, a
paragraph, and three tables. The fee schedules' dumps stay byte-identical.
