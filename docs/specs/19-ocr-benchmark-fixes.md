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

**Prototype result (dev):** PLACEHOLDER

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
     § 2.1), and it does not open, in type at most `footnote_size_ratio` × the body size, with an
     enumerator (`(4)`, `1.`, `a)`) or a note mark (`*`, `†`).
  5. **It prints its role:** its first or last token is a page number, or its type is smaller than the
     body size (`body_size` over the page's horizontal words, `04` § 2). The line's leading and
     trailing dashes, brackets, bars, dots and colons are set aside first. A page number is 1 to 4
     digits, two such joined by `/` (`2/5`), or a roman numeral as § 3 item 2 defines one, with those
     marks around it; a year (1900–2099) and an enumerator (`3.`, `(4)`) are not. So `- 7 -`,
     `Page 2 of 5`, `1 / 1`, `Vacuum 83` and `34 Observer #7` print their role, and any line in smaller
     type does; a line in larger type prints it only by a page number.
  6. It lies in no ruled table (S1).
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
- **Limit:** a numbered heading (`1 Introduction`) that opens a one-page document, set apart from the
  text under it, prints a page number at its start and is read as a running head. None of the dev
  pages has one.

## 2 · Prose columns (`core/layout.py`, amends `04` § 4 step 5)

- **A prose column** is a column of a gutter section that:
  1. holds at least `column_min_lines` fragments;
  2. has at most `MAX_BUSY_SHARE` (a quarter) of its lines holding two fragments or more: more, and it
     is several columns read across, not one;
  3. either has a mean of at least `prose_min_words` words per fragment, as before, or is at least
     `PROSE_MIN_WIDTH_EM` (10) × the body size wide, from its leftmost fragment's start to its
     rightmost's end, with its fragments' mean width at least `PROSE_MIN_FILL` (0.6) of that width.
     A Chinese line is one word.
- **A section of prose columns** is:
  - a gutter section whose columns are all prose columns, as before; or
  - one with at least one prose column whose every other column is a stray or a remainder, and which
    holds at least two prose columns, or a remainder:
    - a **stray** holds fewer than `column_min_lines` fragments: a margin's page number, a mark beside
      one line;
    - a **remainder** holds no value piece (`07` § 1) and, laid out again on its own (steps 1–6 over its
      lines, the page's x-range its own), holds a section of prose columns: a newspaper's columns under
      a headline that breaks their gutters.

  A column holding a value piece, or one laid out with no prose columns of its own, refuses the
  section, as do strays beside a single prose column; step 5's other rules then apply as before. These
  are a table's value columns beside its wordy column, and a table's label column beside its text.
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

## 3 · A header run above a table (`core/tables/corridor.py`, amends `07` § 3)

- **H1. A short header run joins the size run below it.** A size run joins the run that follows it
  when all of these hold; § 3's upward walk then takes its rows when they align, as before:
  - it has at most `MAX_HEADER_ROWS` (3) lines, none holding a value-like piece (years are labels);
  - its last line holds pieces side by side: a column header, not a caption or a heading;
  - its last line sits directly above the next run's first line, the gap at most the taller line's
    height;
  - its type is no larger than that line's.
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
| FP8 | one page: a heading in larger type, no number, set apart; a bottom line in larger type ending in a page number | not furniture; `footer` |
| FP9 | one page of three lines, the last `Page 1` set apart | no furniture |
| FP10 | one page: a smaller line set apart under a body-size top line | no furniture: not outermost |
| FP11 | one page: `(4) Applies to members` in 7 pt set apart at the bottom (`assemble` AS11) | no furniture |
| FP12 | one page: `1 Supported by grant` in 7 pt at the bottom, its `1` called by a superscript `1` in the body; the same with no call | no furniture; `footer` |
| FP13 | one page: `3. The driver sightlines …` in body size set apart at the top | no furniture |
| FP14 | one page: `Annual Report 2022` in body size set apart at the top | no furniture |
| FP15 | two pages, page 1 ending in `Page 1` set apart, page 2 without it | no furniture: S3 is for one page |
| FP16 | `inkgrid.read` of a one-page PDF with a smaller running head and `- 3 -` at its foot | both are furniture blocks, and the Markdown holds neither |
| FU4 (amended) | one page: `Acme Fee Guide` at the foot, body size, no number, set apart | no furniture: recurrence needs 2 pages |
| PC1 | two columns of Chinese prose, 8 lines each, each line one word of 20 characters | two `prose` regions, left then right |
| PC2 | a table of 8 rows of one-word cells in three narrow columns | one `rows` region, as before |
| PC3 | two prose columns, and a stray `12` beside one line in the right margin | left, right, then `12` |
| PC4 | a prose column beside a column of values | one `rows` region, as before |
| PC5 | a column of one-word labels beside a column of long text, 8 rows, no values | one `rows` region, as before |
| PC6 | a prose column beside a value-free column holding two prose columns whose gutter a headline breaks | the prose column, then the headline, then the remainder's two columns |
| PC7 | a prose column beside a column 60 ems wide whose lines hold three fragments each | the prose column, then the wide column's three columns, left to right |
| PC8 | a stray beside a single prose column | one `rows` region, as before |
| PC9 | a column with 2 of its 8 lines in two fragments; one with 3 of 8, both beside a prose column | a prose column; not a prose column |
| PC10 | a Chinese column 10 ems wide, filled 0.6; one 9.5 ems wide | a prose column; not a prose column |
| PC11 | `inkgrid.read` of a one-page PDF of two columns of Chinese prose | the left column's text, then the right's, in the Markdown |
| HR1 | `2025 2024 2023` in 8 pt bold directly above a 9 pt table of three value columns | the table's header row |
| HR2 | a 10 pt bold heading directly above a 9 pt table (`07` EX1) | not in the table |
| HR3 | an 8 pt one-piece caption directly above a 9 pt table | not in the table |
| HR4 | an 8 pt header row 20 pt above a 9 pt table | not in the table |
| HR5 | four 8 pt header lines directly above a 9 pt table | not in the table |
| HR6 | an 8 pt header row holding a value directly above a 9 pt table | not in the table |
| HR7 | `inkgrid.read` of a one-page PDF: `2025 2024 2023` in 8 pt bold over a 9 pt unruled table | the table's first row is its header, `<thead>` in its HTML |

Every existing case keeps passing, but `04` FU4, amended above.

## 5 · Acceptance

- [ ] Every case above has a test named `test_<CaseId>_<slug>`, and it failed before its code.
- [ ] The dev numbers of § 0's prototype hold for the implementation, scored as the run scores them.
- [ ] The fixture suite passes, and every `OPENABLE` fixture verifies with no defect.
- [ ] The 42 fee schedules read as 0.1.0 read them, or each change is explained.
- [ ] Spec 12's ICDAR-2013 and olmOCR table sets and the held-out fee set run at the final commit, and
      each change in them is explained.
- [ ] The tuned run reports the dev and test halves apart, labelled tuned.
