# 19 · One-page furniture, prose columns, and header runs (M7b)

**Implements:** spec 18 § 7, the improvements after the OCR benchmarks' baseline: rules designed from
inkgrid's failures on the **dev half** of olmOCR-bench, OmniDocBench, ParseBench and DP-Bench only
(spec 18 § 2's split; no test-half failure was looked at). It amends `04-text-pipeline.md` § 3
(furniture) and § 4 (layout), and `07-unruled-tables.md` § 3 (size runs).
**Modules:** `core/furniture.py` (§ 1), `core/layout.py` (§ 2), `core/tables/corridor.py` (§ 3). Their
thresholds are module constants, as spec 07's and spec 14's are; the `Profile` and its id `default/1`
are unchanged.

**Tuned.** Every rule here was designed while looking at the dev half's failures, so any run after
them is labelled tuned (DR-0023), and the test half, which no fix has seen, measures whether they
carry (spec 18 § 7). The fixture suite, the 42 fee schedules, spec 12's ICDAR-2013 and olmOCR table
sets, and the held-out fee set guard against regressions.

---

## 0 · What was measured first (L19)

On 2026-10-09, from the baseline run at `00cc5ca` (0.1.0's reading), on dev documents only (283
olmOCR-bench, 311 OmniDocBench, 393 ParseBench, 94 DP-Bench), each failure was traced to the stage
that made it. Each rule was then prototyped in memory and measured with each benchmark's pinned
scorer, called as the run calls it, on the dev documents alone; the harness first reproduced every
baseline dev number exactly. The 42 fee schedules were dumped with the rules and diffed against
0.1.0's dump.

- **One-page furniture.** On olmOCR's dev `headers_footers` pages, inkgrid passes 78 of 295 tests.
  - Every benchmark document is one page, and furniture is found only by recurrence (`04` § 3 item 4
    needs 2 pages), so none is ever found.
  - The furniture text of 204 of the 217 failing tests lies in one line of the page. 159 of those lines
    are the page's outermost, top or bottom, and 20 more the next one in.
  - OmniDocBench's truth labels headers, footers and page numbers: 472 of the 14,000 lines inkgrid
    reads on its dev pages. Position alone, the outermost line of a band, finds 386 of them (recall
    0.818) at precision 0.656: L8's lesson holds on one page too.
  - § 1's rule finds 213 (recall 0.451) at precision 0.973. Its 6 other lines are 4 captions or figure
    labels in small type at a page edge, and 2 browser print headers the truth labels as body.
  - As implemented at `87093ec`, labelling each line inkgrid reads by the truth box holding most of
    its words, S3 found 209 (recall 0.443) at precision 0.972; after the final review's fix pass
    (`1d31f4f`), 208 (recall 0.441) at precision 0.977. The pass gave up one running head (a
    Chinese `9` in heading type, its number among the words) and one equation ending in `C`.
  - Two benchmarks count furniture as text. DP-Bench's truth Markdown keeps 179 of its 181 headers
    and footers, and ParseBench's text rules ask for page numbers and running heads, so every piece of
    furniture § 1 finds costs those two.
- **Prose columns.** On OmniDocBench's dev pages, inkgrid's simplified-Chinese text Edit distance is
  0.512, against 0.293 in English, and olmOCR's dev `multi_column` pass rate is 0.613.
  - The layout stage found 545 gutter runs on those pages. Labelled by the truth's majority, 345 are
    prose and 138 tables; it accepted 96 of the prose runs as columns, and no table.
  - 160 of the 249 refused prose runs are Chinese, 4,815 rows. A Chinese line is one or two "words"
    (no spaces), under `prose_min_words` = 4, though its columns are 20 ems wide and their lines fill
    82–87% of it.
  - 53 refused runs hold good prose columns beside a stray column of one or two fragments: a page
    number in the margin, a mark beside one line.
  - 59 hold one good column beside a wide, sparse remainder: a newspaper, whose headline across some
    columns breaks the gutters between them.
  - olmOCR's dev pages show the same, and one more: a Latin "column" 58 ems wide holding three
    fragments a line, passed as prose on its words alone, reading three columns across.
- **Header runs.** On ParseBench's dev table pages, inkgrid's 53 tables without a header row score
  TableRecordMatch 0.192, against 0.418 for its 154 with one (GriTS-Con 0.669 against 0.704: the
  grids are alike).
  - 112 of its 172 unruled tables have no header row. For 63 of them a line shaped like a header row
    (two or more pieces over two or more of the table's columns) sits directly above the table, read
    as prose. OmniDocBench (18 of 34) and olmOCR (8 of 27) show the same.
  - Traced through the corridor stage, the header stops being reached for two reasons. It is set in
    other type than the table's rows (`2025 2024 2023` in 8 pt bold over 9 pt rows), and `07` § 3
    folds each size run on its own, so a table never reaches a header in another size. Or it does not
    align with the columns, and these rows are mostly not headers: data rows whose pieces merge two
    columns, wrapped description lines, rows of placeholders.
- **Measured and left out:**
  - a Type 3 font's size read without its font matrix (0.12 for 10 pt type, 2 dev documents);
  - text the PDF draws apart: accents as separate glyphs, unmapped ligatures, `…` where a test
    expects `...`; no rule may change these (G1);
  - headings the page sets as body text.

**Prototype result (dev).** Each rule alone, prototyped in memory over 0.1.0, scored by the
benchmark's own scorer on the dev documents. The Edit distances are lower-better, as are
OmniDocBench's text and order; the rest are higher-better.

| Dev number | 0.1.0 | § 1 alone | § 2 alone | § 3 alone |
|---|---|---|---|---|
| olmOCR headers and footers (295 tests) | 0.264 | 0.576 | 0.264 | 0.264 |
| olmOCR multi-column (328) | 0.613 | 0.622 | 0.671 | 0.613 |
| olmOCR tables (440) | 0.559 | 0.559 | 0.559 | 0.566 |
| olmOCR long tiny text (51) | 0.255 | 0.255 | 0.392 | 0.255 |
| OmniDocBench text, English (primary, 102 pages) | 0.293 | 0.233 | 0.279 | 0.293 |
| OmniDocBench text, simplified Chinese (93) | 0.512 | 0.502 | 0.408 | 0.512 |
| OmniDocBench table TEDS (69) | 0.521 | 0.521 | 0.520 | 0.521 |
| OmniDocBench reading order (195) | 0.274 | 0.280 | 0.237 | 0.274 |
| ParseBench GTRM (227 tables) | 0.496 | 0.495 | 0.496 | 0.506 |
| ParseBench TableRecordMatch (227) | 0.329 | 0.327 | 0.329 | 0.343 |
| ParseBench content faithfulness, five tags (148) | 0.835 | 0.828 | 0.850 | 0.835 |
| DP-Bench NID (94) | 0.903 | 0.896 | 0.909 | 0.903 |
| DP-Bench MHS (46) | 0.694 | 0.689 | 0.704 | 0.694 |

§ 1's losses are on benchmarks that count furniture as text (ParseBench, DP-Bench), and its small
table losses on ParseBench were one prototype's error: it compared a line's raw size with the
half-point body size, so a 6.96 pt header row under a 7.0 pt body read as smaller type. § 1 as
written compares sizes rounded alike. § 2's prototype held a column of more than a quarter of
busy lines to be no prose column, and measured prose by width and fill in any script; § 2 as written
takes half (a quarter turned a prose column with a few split lines into rows read across), measures
width and fill only in wide script, and leaves a section holding a value as 0.1.0 read it, after the
fee schedules' look-back found Latin tables read apart (§ 2's rejected options).

---

## 1 · A one-page document's furniture (`core/furniture.py`, amends `04` § 3)

- **S3. On a document of one page, a band's outermost line is furniture when the page says so.**
  Recurrence has nothing to count on one page; on every other document § 3 is unchanged. A line is S3
  furniture when all of these hold:
  1. The page holds at least `ONE_PAGE_MIN_LINES` (4) lines (`group_lines` over its horizontal words).
  2. Its median word centre lies in the top or bottom `furniture_band` (§ 3 item 3), and it is that
     band's outermost line: the highest by centre, or the lowest.
  3. **It is set apart:** the gap between it and the next line toward the body is at least the median
     height of the page's lines.
  4. **It is no footnote:** its first word is not a label that a superscript on the page calls (spec 09
     § 2.1), and it does not open, in type smaller than the body as item 5 measures it, with an
     enumerator (`(4)`, `1.`, `a)`) or a note mark (`*`, `†`). (Before the final review the bound
     was `footnote_size_ratio` × the body size, which let a 10 pt note under an 11 pt body through.)
  5. **It prints its role:** its type is smaller than the body size, or its first or last token is a
     page number.
     - Smaller: its size, rounded to 0.5 pt as `body_size` rounds, is below `body_size` over the
       page's horizontal words (`04` § 2).
     - A page number, once the line's leading and trailing dashes, brackets, bars, dots and colons
       are set aside: 1 to 4 digits, or two such joined by `/` (`2/5`), with those marks around it;
       a year (1900–2099) and an enumerator (`3.`, `(4)`) are not, and a number, a word and a year
       are a date (`12 March 2024`). A roman numeral as § 3 item 2 defines one counts only as the
       whole line (`xii`, `- iv -`): beside words it is as often a letter, a unit or a degree
       (`Appendix C`, `120 cm`, `Jane Doe, MD`, `I certify`).
     - In heading type (`heading_size_ratio` × the body size or more), the page number must stand
       apart, the whole line or a fragment of its own at the line's start or end, or come with the
       page count: two numbers joined by a word of at most `MAX_JOINT` (3) letters at the line's
       start or end (`Page 2 of 28`, `1 of 14`). A title sets its one number among its words
       (`Homework 3`, `Form 1040`, `Chapter 3`); a running head sets it apart, and a foot counts
       the pages.
     - So `- 7 -`, `Page 2 of 5`, `1 / 1`, `Vacuum 83` and `34 Observer #7` print their role, and
       any line in smaller type does.
  6. It lies in no ruled table (S1), and it is no row of an unruled one: it and the next line toward
     the body do not both hold `MAX_FRAGMENTS` (3) or more fragments with every fragment of it
     starting, ending or centring within `furniture_x_tol` of one of the other's.
- **Role** as § 3 item 6; its key is its own `line_key`.
- **Rejected:**
  - Position alone (items 2 and 3): precision 0.656 on OmniDocBench's dev pages.
  - Words for "page" in a list of languages (`page`, `Seite`): 3 more failing olmOCR tests found;
    inkgrid's rules name no language.
  - A number at a line's start counting only in smaller type, so that no numbered heading could be
    read as a running head: recall 0.424 against 0.468, and every line it gave up on OmniDocBench's
    dev pages is a running head (`922 Ding et al.`, a newspaper's masthead).
  - The two outermost lines of a band, each printing its role: 11 more failing olmOCR tests, at
    precision 0.952; the lines it adds are two-line captions.
  - § 3's shape rule, no line of `MAX_FRAGMENTS` fragments: of the 209 lines S3 found on
    OmniDocBench's dev pages that its truth labels furniture, 28 are running heads in three or more
    parts, and the rule removes none it found wrongly. Item 6 removes no line S3 finds on any dev
    page.
  - Item 6 for lines of two fragments: 6 of the 209, two-part running heads whose ends line up with
    a two-column page's columns.
  - In heading type, any line of a word and a number as a label: 6 of the 209 are Chinese footers,
    one run of characters and a page number set apart, which item 5 keeps. Item 5's own heading
    rule loses 1 of the 209; its roman and date rules none.
  - Set apart measured against the gap between the next two lines toward the body, so that a
    double-spaced page sets no line apart: 10 of the 209 (3 in body or larger type), on pages where a
    figure or a table makes that gap wide.
- **Limits:** each line is read as a running head or foot, its words owned as furniture and out of the
  Markdown, and the rejected rules above measure what telling it apart would cost.
  - A numbered heading (`1 Introduction`) that opens a one-page document, set apart from the text
    under it, prints a page number at its start. None of the dev pages has one.
  - A line in body type ending in a number at the top of the page: a caption label (`Table 23`, on
    one of spec 12's olmOCR table pages) or a title (`Homework 3`). Nothing on the page tells it from
    `Vacuum 83` without naming the word.
  - A two-column table's last row at the page's foot, set apart, ending in an integer (`Total 12`).
  - The last line of a double-spaced page, ending in a number.

## 2 · Prose columns (`core/layout.py`, amends `04` § 4 step 5)

- **A section holding a value** (a value piece, `07` § 1, in any column) is read as 0.1.0 read it:
  prose columns exactly when every column holds at least `column_min_lines` fragments with a mean of
  at least `prose_min_words` words, and none of the rules below applies. A table's columns stay its
  own, however wide or wordy its label column.
- **In a section holding no value, a prose column** is a column that:
  1. holds at least `column_min_lines` fragments;
  2. has at most `MAX_BUSY_SHARE` (half) of its lines holding two fragments or more: more, and it is
     several columns read across, not one;
  3. either has a mean of at least `prose_min_words` words per fragment, as before, or, when most of
     its characters are wide (Chinese, Japanese or Korean script, East Asian width wide or
     full-width), is at least `PROSE_MIN_WIDTH_EM` (10) × the body size wide, from its leftmost
     fragment's start to its rightmost's end, with its fragments' mean width at least
     `PROSE_MIN_FILL` (0.6) of that width. Such script sets no space between its words, so a line
     is one word and words per fragment cannot see its prose; a Latin column is prose only by its
     words, as 0.1.0 read it.
- **A section of prose columns, holding no value,** is:
  - one whose columns are all prose columns; or
  - one with at least one prose column whose every other column is a stray or a remainder, and which
    holds at least two prose columns, or a remainder:
    - a **stray** holds fewer than `column_min_lines` fragments: a margin's page number, a mark beside
      one line;
    - a **remainder**, laid out again on its own (steps 1–6 over its lines, the page's x-range its
      own), holds a section of prose columns: a newspaper's columns under a headline that breaks
      their gutters.

  A column laid out with no prose columns of its own, or strays beside a single prose column, refuse
  the section, and step 5's other rules then apply as before: a table's label column beside its
  text, or a short table's cells.
- **Regions:** each prose column is one `prose` region, as before; each stray and remainder gives the
  regions its own layout gives, in its column's place. Layout goes at most `MAX_DEPTH` (4) levels deep:
  deeper, a remainder holds no prose columns.
- **Rejected:**
  - Any prose column accepting the section: olmOCR's dev table pass rate fell from 0.559 to 0.534, as a
    table's description column passed and its value columns were read apart.
  - A value-free column laid out again without needing columns of its own: a two-column table of
    labels and text (OmniDocBench `eastmoney_8f87…`) read its labels apart, its text Edit distance
    0.006 to 0.391.
  - Strays beside a single prose column: a short table's label cells are strays too.
  - The new rules in a section holding values. The fee schedules' look-back found tables come apart
    when they applied: Euronext's two options (`0.65 bp | 0.45 bp`) beside a stray passed as
    columns, and NYSE Arca's labels passed by width and fill beside fees that passed by their words.
  - Width and fill for a column of any script. On Latin text it read short phrases as prose:
    Euronext's two-column table of text (`Standard fees apply`, 10.5 ems wide), and NYSE Arca's
    floor-fee labels beside fees of five tokens, no value piece by `07` § 1.

## 3 · A header run above a table (`core/tables/corridor.py`, amends `07` § 3)

- **H1. A short header run joins the size run below it.** A size run joins the run that follows it
  when all of these hold; § 3's upward walk then takes its rows when they align, as before:
  - it has at most `MAX_HEADER_ROWS` (3) lines, none holding a value-like piece (years are labels);
  - its last line holds pieces side by side: a column header, not a caption or a heading;
  - its last line sits directly above the next run's first line, the gap at most the taller line's
    height;
  - its type is no larger than that line's;
  - the next run folds into at least `MIN_ROWS` (2) value rows: a header gives a table its header
    row and never makes a table of a single row. A smaller line over one value row is as often a
    chart's labels over its numbers, or a note over a total, as a header (the final review's
    finding 4; on the dev pages, a chart's legend over its percentages beside a 10-K's one-row
    statement), and 0.1.0 leaves both as text.
- **Rejected:** aligning header rows more loosely. The dev tables' misaligned rows above a table are
  mostly data rows that merge two columns, wrapped description lines, or rows of placeholders.

## 4 · Cases

| Case | Input | Expected |
|---|---|---|
| FP1 | one page: three body lines, and `Page 1 of 1` 460 pt below them (`04` FU4's page) | S3 furniture, role `footer` |
| FP2 | one page: `Journal of Things 12`, body size, set apart above the body | `header` |
| FP3 | one page: a bare `7`, body size, set apart at the bottom; `- 7 -` | `page_number`; `page_number` |
| FP4 | one page: a running head in smaller type, no number, set apart | `header` |
| FP5 | one page: a title in body size, no number, set apart at the top | no furniture |
| FP6 | one page: `Page 2` at the bottom, closer to the last body line than a line height | no furniture |
| FP7 | one page: its bottom line in a ruled 2 × 2 grid with two other cells filled (S1), set apart | no furniture |
| FP8 (amended) | one page: a heading in larger type, no number, set apart; a bottom line in heading type with its page number set apart at the margin | not furniture; `footer` |
| FP9 | one page of three lines, the last `Page 1` set apart | no furniture |
| FP10 | one page: a smaller line set apart under a body-size top line | no furniture: not outermost |
| FP11 | one page: `(4) Applies to members` in 7 pt set apart at the bottom (`assemble` AS11) | no furniture |
| FP12 | one page: `1 Supported by grant` in 7 pt at the bottom, its `1` called by a superscript `1` in the body; the same with no call | no furniture; `footer` |
| FP13 | one page: `3. The driver sightlines …` in body size set apart at the top | no furniture |
| FP14 | one page: `Annual Report 2022` in body size set apart at the top | no furniture |
| FP15 | two pages, page 1 ending in `Page 1` set apart, page 2 without it | no furniture: S3 is for one page |
| FP16 | `inkgrid.read` of a one-page PDF with a smaller running head and `- 3 -` at its foot | both are furniture blocks, and the Markdown holds neither |
| FP17 | one page: 8 pt three-column fee rows 18 pt apart at the foot under the body; an 8 pt header row `Item Quantity Price` as the top line over 10 pt rows; a total row `Total 21.00 27` set apart under the rows | no furniture (item 6) |
| FP18 | one page: `(1) Prices exclude VAT`, `1. …`, `* …` in 10 pt at the foot of an 11 pt body | no furniture (item 4) |
| FP19 | `inkgrid.read` of a one-page PDF: five 10 pt body lines, then an 8 pt three-column fee table whose last row is the page's foot | no furniture block; the table holds the header and all five rows |
| FP20 | one page: `Jane Doe, MD` (16 pt), `Appendix C` (14 pt), `Office of the Mayor, Washington, DC`, `Homework 3` (16 pt), `Form 1040` (14 pt), `12 March 2024` at the top; `Overall width 120 cm`, `I certify that the statements above are true` at the foot | no furniture (item 5) |
| FP21 | one page: `Annals of Things` in 12 pt over a 10 pt body, `153` set apart at the right margin | `header` |
| FP22 | one page: an 8 pt footer in three parts, `Acme`, `Confidential`, `Page 3`, under prose | `footer`: its parts line up with no table row |
| FP23 | one page: `Page 2 of 28`, `1 of 14`, `- Page 5 of 5 -` in 10 pt at the foot of an 8 pt body | `footer` |
| FU4 (amended) | one page: `Acme Fee Guide` at the foot, body size, no number, set apart | no furniture: recurrence needs 2 pages |
| PC1 | two columns of Chinese prose, 8 lines each, each line one word of 20 characters | two `prose` regions, left then right |
| PC2 | a table of 8 rows of one-word cells in three narrow columns | one `rows` region, as before |
| PC3 | two prose columns, and a stray `12` beside one line in the right margin | left, right, then `12` |
| PC4 | a prose column beside a column of values | one `rows` region, as before |
| PC5 | a column of one-word labels beside a column of long text, 8 rows, no values | one `rows` region, as before |
| PC6 | a prose column beside a value-free column holding two prose columns whose gutter a headline breaks | the prose column, then the headline, then the remainder's two columns |
| PC7 | a prose column beside a column 60 ems wide whose lines hold three fragments each | the prose column, then the wide column's three columns, left to right |
| PC8 | a stray beside a single prose column, on its fourth line | as before: the three lines above it one `prose` region, the rest and the stray one `rows` region |
| PC9 | beside a prose column, a column with 4 of its 8 lines in two fragments; one with 5 of 8 | two `prose` regions; one `rows` region |
| PC10 | a Chinese column 10 ems wide, filled 0.6; one 9.5 ems wide | a prose column; not a prose column |
| PC11 | `inkgrid.read` of a one-page PDF of two columns of Chinese prose | the left column's text, then the right's, in the Markdown |
| PC12 | labels beside fees whose qualifiers make the fee column wide and full (`$100 charged-per-issue…`) | one `rows` region, as 0.1.0 read it |
| PC13 | two columns that pass the words test and hold values (`0.65 bp`), beside a stray | one `rows` region, as 0.1.0 read it |
| PC14 | labels that pass only by width and fill, beside fees that pass by their words and hold values (NYSE Arca's) | one `rows` region, as 0.1.0 read it |
| PC15 | beside a prose column, a Latin column of three-word lines 12.6 ems wide and full (Euronext's text table) | one `rows` region, as 0.1.0 read it |
| PC16 | Latin labels of three words, 13.6 ems wide, beside fees of five tokens (no value piece) | one `rows` region, as 0.1.0 read it |
| HR1 | `2025 2024 2023` in 8 pt bold directly above a 9 pt table of three value columns | the table's header row |
| HR2 | `2025 2024 2023` in 10 pt directly above a 9 pt table (and `07` EX1's bold heading) | not in the table: its type is larger |
| HR3 | an 8 pt one-piece caption directly above a 9 pt table | not in the table |
| HR4 | an 8 pt header row 20 pt above a 9 pt table | not in the table |
| HR5 | four 8 pt header lines directly above a 9 pt table | not in the table |
| HR6 | an 8 pt header row holding a value directly above a 9 pt table | not in the table |
| HR7 | `inkgrid.read` of a one-page PDF: `2025 2024 2023` in 8 pt bold over a 9 pt unruled table | the table's first row is its header, `<thead>` in its HTML |
| HR8 | an 8 pt line `Thank you for your business` / `Terms: net thirty days` directly above a 9 pt `Total due` / `$1,250.00`, prose around them | no table |

Every existing case keeps passing, but `04` FU4, amended above.

## 5 · Acceptance

**Measured** (2026-10-12, the three rules as written at `1d31f4f`, after the final review's fix pass;
dev documents only, each benchmark's pinned scorer called as the run calls it):

| Dev number | 0.1.0 | Spec 19 |
|---|---|---|
| olmOCR headers and footers (295 tests) | 0.264 | 0.556 |
| olmOCR multi-column (328) | 0.613 | 0.674 |
| olmOCR tables (440) | 0.559 | 0.566 |
| olmOCR long tiny text (51) | 0.255 | 0.392 |
| olmOCR baseline tests (281) | 1.000 | 1.000 |
| OmniDocBench text Edit distance, English (primary) | 0.293 | 0.235 |
| OmniDocBench text Edit distance, simplified Chinese (primary) | 0.512 | 0.386 |
| OmniDocBench table TEDS (primary) | 0.521 | 0.521 |
| OmniDocBench reading-order Edit distance (primary) | 0.274 | 0.233 |
| ParseBench GTRM | 0.496 | 0.504 |
| ParseBench TableRecordMatch | 0.329 | 0.342 |
| ParseBench content faithfulness, five tags | 0.835 | 0.832 |
| ParseBench content faithfulness, multi-column tag | 0.747 | 0.762 |
| ParseBench content faithfulness, multilingual | 0.615 | 0.612 |
| DP-Bench NID | 0.903 | 0.896 |
| DP-Bench TEDS | 0.682 | 0.682 |
| DP-Bench MHS | 0.694 | 0.692 |

Together the rules do better than any alone on olmOCR's multi-column tests (furniture no longer
breaks a passage) and on OmniDocBench's text. They cost ParseBench's simple and misc text tags and
DP-Bench's NID, whose truths count page numbers and running heads as text. Leaving a section that
holds a value as 0.1.0 read it, and measuring width and fill only in wide script, gave back some
Latin pages (olmOCR multi-column 0.695 and OmniDocBench English text 0.217 without either), to keep
every table the fee schedules' look-back found read apart. The final review's fix pass cost olmOCR's
headers and footers 0.563 to 0.556 (running heads in heading type with their number among their
words, `Beijing Language And Culture University 11`, which S3 now leaves as titles) and ParseBench's GTRM 0.506 to 0.504 (H1 no longer makes a 10-K's one-row statement a
table); every other dev number is as at `87093ec`. These are dev numbers: the tuned run's test half
is the measure of whether the rules carry.

- [x] Every case above has a test named `test_<CaseId>_<slug>`, and it failed before its code. The
      cases that guard what must not change (FP5, FP6, FP9, FP10, FP13, FP14, FP15, FU4, PC2, PC4,
      PC5, PC8, HR2 to HR6) passed before it; PC12 to PC16 also pass on 0.1.0's own layout code;
      HR2 to HR6, FP11's note mark, and PC7 and PC9's busy share each failed with its clause removed.
      The final review's cases (FP17 to FP20, FP23, HR8) failed before the fix pass; FP21 and FP22,
      which guard what it must not take, passed before it, and FP8 was amended to set its page
      number apart.
- [x] The dev numbers above are the rules as written, scored as the run scores them.
- [x] The fixture suite passes (`scripts/dev.sh` at `1d31f4f`: 2,152 tests, coverage 98%, every
      floor met), and every `OPENABLE` fixture, the five new ones among them, builds a valid document.
- [x] The 42 fee schedules (2026-10-12, `1d31f4f`): 974 pages, all 1,817,075 characters owned, none
      lost, the same 8 defects as 0.1.0, and every dump byte-identical to 0.1.0's. At `87093ec` three
      had read differently, H1 making a table of a header over one value row (Nasdaq Copenhagen's and
      Helsinki's `INSTRUMENT TYPE | DKK` over `Warrants and certificates | 0.25`, Nasdaq Stockholm's
      `VALUE BASED FEE` over `- | 0.204 bps`); since `ba0aa41` H1 makes no table of one row.
- [ ] Spec 12's ICDAR-2013 and olmOCR table sets and the held-out fee set run at the final commit, and
      each change in them is explained.
- [x] The tuned run reports the dev and test halves apart, labelled tuned
      (`bench/results/2026-10-16-dbc66fc-ocr/`, at `dbc66fc`, src as at `1d31f4f`; the other seven
      tools' readings carried over from the baseline). Whether the rules carry, inkgrid's tuned counts
      against 0.1.0's, paired by document with the report's own code over both runs' committed counts
      (`ocr_report.document`, 0.1.0's inkgrid read as a second tool; a `✱` marks an interval that
      excludes 0):

      | Metric | Dev half: 0.1.0 → tuned | Difference | Test half: 0.1.0 → tuned | Difference |
      |---|---|---|---|---|
      | olmOCR-bench headers and footers | 0.264 → 0.556 | +0.292 [+0.222, +0.370] ✱ | 0.304 → 0.606 | +0.302 [+0.235, +0.375] ✱ |
      | olmOCR-bench multi-column | 0.613 → 0.674 | +0.061 [+0.015, +0.115] ✱ | 0.617 → 0.651 | +0.034 [+0.009, +0.063] ✱ |
      | olmOCR-bench tables | 0.559 → 0.566 | +0.007 [+0.000, +0.023] | 0.535 → 0.542 | +0.007 [+0.000, +0.023] |
      | olmOCR-bench born-digital macro | 0.479 → 0.599 | +0.120 [+0.091, +0.151] ✱ | 0.486 → 0.600 | +0.114 [+0.090, +0.141] ✱ |
      | OmniDocBench text Edit distance, English ↓ | 0.293 → 0.235 | -0.058 [-0.092, -0.030] ✱ | 0.302 → 0.246 | -0.056 [-0.094, -0.025] ✱ |
      | OmniDocBench text Edit distance, Chinese ↓ | 0.512 → 0.386 | -0.126 [-0.179, -0.078] ✱ | 0.507 → 0.440 | -0.067 [-0.108, -0.031] ✱ |
      | OmniDocBench table TEDS | 0.521 → 0.521 | +0.000 [+0.000, +0.000] | 0.563 → 0.563 | +0.000 [+0.000, +0.000] |
      | OmniDocBench reading-order Edit distance ↓ | 0.274 → 0.233 | -0.041 [-0.069, -0.015] ✱ | 0.274 → 0.262 | -0.012 [-0.031, +0.004] |
      | ParseBench GTRM | 0.496 → 0.504 | +0.009 [+0.001, +0.019] ✱ | 0.535 → 0.544 | +0.009 [+0.003, +0.016] ✱ |
      | ParseBench TableRecordMatch | 0.329 → 0.342 | +0.013 [+0.002, +0.027] ✱ | 0.357 → 0.373 | +0.016 [+0.005, +0.029] ✱ |
      | ParseBench content faithfulness | 0.835 → 0.832 | -0.003 [-0.011, +0.006] | 0.858 → 0.855 | -0.003 [-0.010, +0.006] |
      | ParseBench text correctness | 0.879 → 0.869 | -0.009 [-0.014, -0.004] ✱ | 0.901 → 0.889 | -0.011 [-0.017, -0.006] ✱ |
      | ParseBench multilingual faithfulness | 0.614 → 0.612 | -0.003 [-0.011, +0.004] | 0.712 → 0.701 | -0.011 [-0.023, -0.002] ✱ |
      | DP-Bench NID | 0.903 → 0.896 | -0.007 [-0.016, +0.003] | 0.906 → 0.901 | -0.005 [-0.007, -0.003] ✱ |
      | DP-Bench TEDS | 0.682 → 0.682 | +0.000 [+0.000, +0.000] | 0.610 → 0.610 | +0.000 [+0.000, +0.000] |
      | DP-Bench MHS | 0.694 → 0.692 | -0.002 [-0.025, +0.027] | 0.657 → 0.639 | -0.018 [-0.048, +0.006] |

      Every dev-half gain recurs on the test half, which no rule was designed from, and so do the
      dev half's costs, the text the benchmarks count and inkgrid now leaves out as furniture:
      ParseBench's text correctness, DP-Bench's NID, and on the test half ParseBench's multilingual
      faithfulness. OmniDocBench's reading order, better on the dev half, is not distinguishable from
      0.1.0's on the test half.
