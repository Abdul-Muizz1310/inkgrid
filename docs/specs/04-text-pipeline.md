# 04 · The text pipeline: furniture, layout, prose, assembly (M1)

**Implements:** `00-design.md` § 4.3 stages 1, 2, 4, and 7, § 6 (configuration), § 8.4 (text
rendering). Tables (stage 3), joins (stage 5), and links (stage 6) are M2 and M3. Until they land,
every non-furniture word is prose.
**Modules:**
- `model/config.py`: the `Profile` and `Lexicon` value types;
- `core/lexicon.py`: token classification;
- `core/lines.py`: lines, fragments, and the body size;
- `core/furniture.py`: running headers, footers, and page numbers;
- `core/layout.py`: column sections and reading order;
- `core/prose.py`: blocks and their kinds;
- `core/assemble.py`: text, keys, ledger, and the `Document`;
- `core/pipeline.py`: the stages in order.

**Input:** a `Reading` (`01-model.md` § 4). **Output:** a `Document` (`01-model.md` § 5).

---

## 0 · What was measured first (L19)

On 2026-09-26 the M0 reader ran over seven public fee schedules: Cboe US Options, SIX, Nasdaq,
Nasdaq PHLX, Euronext, LSE, and JSE, 304 pages in all. Every number below comes from that run.

- **Word gaps are not bimodal around one threshold.** Within a line, the median word gap is
  0.23–0.35 em. Between 1 and 2 em sit *both* labels tab-separated from their text (`1.2 ⇥ Market
  maker tariff`, `■ ⇥ the member …`, `ii. ⇥ If …`) and the narrowest table column gaps (`Investment
  Strategy Group B | Investment Strategy Group C`, 1.6 em). So a gap alone cannot decide a column.
  Columns need a gutter that persists over several lines *and* prose on both sides. Everything else
  keeps row order, which is right for tables and for hanging-indent lists.
- **Line gaps are bimodal.** The gap between consecutive lines, over the page's median gap, peaks
  at 1.0 inside paragraphs, with a valley near 1.5 and a second mode at 2 and above for paragraph
  breaks. The break threshold is 1.75, which the prototype measured independently at 1.8.
- **Body size varies from 5.3 pt (Cboe) to 10.4 pt**, so every size rule is relative to the
  document's own body size.
- **Furniture** repeats as the prototype found:
  - Cboe (`Cboe Exchange, Inc.`, 24/24 pages);
  - SIX (three lines, 70/70);
  - Euronext (45/46);
  - LSE (14/15);
  - JSE page numbers (32/34).
  PHLX and Nasdaq show none, and Nasdaq genuinely has no running header.
- **The M0 reader** read all seven in 22–63 ms a page, with no findings.

---

## 1 · Configuration (`model/config.py`)

Both types are frozen models with an `id` that the `Producer` records. `Profile.default()` and
`Lexicon.default()` return the defaults.

**A changed configuration needs a new id.** A `Profile` or `Lexicon` whose `id` is the default id
but whose fields differ from the defaults is rejected, because the `Producer` would then record a
configuration that did not run. A variant is built by construction,
`Profile(id="custom/1", paragraph_gap_ratio=2.0)`. `model_copy(update=…)` skips validation, so
`inkgrid.read` revalidates whatever it is given.

### `Profile` (geometry only)

| field | default | meaning |
|---|---|---|
| `id` | `"default/1"` | recorded in `Producer.profile` |
| `line_overlap` | 0.5 | two words share a line when their vertical overlap exceeds this share of the smaller height |
| `fragment_gap_em` | 1.0 | a gap wider than this × the pair's larger font size splits a line into fragments |
| `gutter_min_em` | 1.0 | the narrowest column gutter, × the document body size |
| `column_min_lines` | 3 | lines a gutter must persist over before it defines columns |
| `prose_min_words` | 4.0 | the mean words per fragment every column needs for the section to read as prose columns |
| `paragraph_gap_ratio` | 1.75 | a line gap above this × the page's median line gap starts a block |
| `paragraph_gap_floor` | 2.0 | pt; the paragraph-gap threshold is never smaller |
| `size_change_ratio` | 0.1 | a font-size change above this share of the previous line's size starts a block |
| `heading_size_ratio` | 1.1 | a heading's size is at least this × body size, unless it is bold |
| `heading_max_words` | 15 | |
| `heading_max_lines` | 2 | |
| `footnote_size_ratio` | 0.9 | a footnote's first line is at most this × body size |
| `furniture_share` | 0.4 | the share of pages a line key must occur on, with a floor of 2 pages |
| `furniture_band` | 0.1 | the top and bottom share of the page's content height where furniture is counted |
| `furniture_x_tol` | 3.0 | pt; a numeric-only key must recur at the same x within this |
| `long_document_pages` | 8 | more pages than this with no furniture raises `no_furniture_long_document` |

Validators: every ratio and length is positive, `line_overlap` and the two shares lie strictly
between 0 and 1, and every count is at least 1.

### `Lexicon` (what a token is)

| field | default |
|---|---|
| `id` | `"generic/1"` |
| `bullets` | `•` `▪` `◦` `■` `□` `●` `○` `‣` `⁃` `∙` `·` `–` `—` `-` `*` (U+2022 U+25AA U+25E6 U+25A0 U+25A1 U+25CF U+25CB U+2023 U+2043 U+2219 U+00B7 U+2013 U+2014 U+002D U+002A) |

`bullets` is a non-empty tuple of single characters, with no repeats.

The Symbol-font bullet U+F0B7 is not in the list, because it can never reach it. It is a private-use
code point, and the reader drops those as invisible (`02-reader.md` W-9). A list set in that font
reads as paragraphs until the benchmark shows a signal that recovers it.

`core/lexicon.py` classifies a single token:

- **`is_bullet(token, lexicon)`**: the token is exactly one of `bullets`.
- **`enumerator(token) -> str | None`**: the token is a list or note label, returned as printed.
  - The labels match `(\d{1,3}|[a-z]|[ivxlc]{1,6}|[A-Z])[.)]` or `\((\d{1,3}|[a-z]|[ivxlc]{1,6})\)`,
    matched against the whole token.
  - That covers `1.`, `12)`, `(3)`, `a)`, `(b)`, `iv.`, `(ii)`, and `A.`.
  - A bare `1`, a bare `(12`, and `$1.` are not labels.
- **`section_number(token) -> str | None`**: `\d+(\.\d+)*\.?` or `[A-Z]\.`, matched against the whole
  token.
  - A four-digit number from 1900 to 2099 with no dot is a year, not a section number.
- **`note_label(token) -> str | None`**: a footnote label. That is an `enumerator`, 1–3 digits, or
  1–3 of `* † ‡ § ¶ #`.

The Lexicon grows in M2 (numbers, money, ranges).

| # | case | expected |
|---|---|---|
| CF1 | `Profile()` and `Lexicon()`; `Profile.default()` and `Lexicon.default()` | ids `default/1` and `generic/1`; `default()` equals the no-argument instance |
| CF2 | `Profile(paragraph_gap_ratio=0)`; `Profile(furniture_share=1.5)`; `Profile(line_overlap=1.0)`; `Profile(column_min_lines=0)` | `ValidationError` |
| CF3 | `Profile(paragraph_gap_ratio=2.0)` (default id); `Lexicon(bullets=("*",))` (default id) | `ValidationError` naming the id |
| CF4 | `Profile(id="custom/1", paragraph_gap_ratio=2.0)` | valid |
| CF5 | `Lexicon(id="x/1", bullets=())`; `bullets=("**",)`; `bullets=("*", "*")` | `ValidationError` |
| CF6 | `is_bullet` on `•`, `-`, `■`, `--`, `a` | T, T, T, F, F |
| CF7 | `enumerator` on `1.`, `12)`, `(3)`, `a)`, `(b)`, `iv.`, `(ii)`, `A.` | returned as given |
| CF8 | `enumerator` on `1`, `(12`, `$1.`, `1.5`, `abc.`, `(1)(2)`, `1234.` | `None` |
| CF9 | `section_number` on `2.`, `2.1`, `2.1.10`, `C.`, `2026`, `1999.`, `2.a` | `2.`, `2.1`, `2.1.10`, `C.`, None, `1999.`, None |
| CF10 | `note_label` on `3`, `(3)`, `*`, `†‡`, `12a`, `1234` | `3`, `(3)`, `*`, `†‡`, None, None |

---

## 2 · Lines and fragments (`core/lines.py`, pure)

- **`group_lines(words, profile) -> tuple[Line, ...]`**:
  - Take the words, sorted by vertical centre, then `x0`, then id.
  - A word joins the first existing line whose current vertical extent overlaps the word by more
    than `line_overlap` × the smaller of the two heights, and the line's extent grows to cover it.
  - Otherwise the word starts a new line.
  - After clustering, a superscript word glued on its left to a non-superscript word on another
    line moves to that word's line, unless it is glued to a word of its own line (spec 13 § 5).
  - Lines come out sorted by their top, and each line's words by `x0`, then id.
  - Clustering by overlap rather than a fixed band is L15.
- **`Line`**: its words, `top`, `bottom`, `x0`, `x1`, the median `size`, and `bold` (at least half
  its characters are in bold words).
- **`fragments(line, profile) -> tuple[Line, ...]`**: the line split wherever the gap between
  consecutive words exceeds `fragment_gap_em` × the larger size of the pair. A fragment is a `Line`.
- **`body_size(words) -> float`**: the size that carries the most characters, with sizes rounded to
  0.5 pt and ties going to the smaller size. It is taken over the document's non-furniture words, and
  requires at least one word.
- **Hidden words take part like any other word.** They are text-layer content, and the OCR finding
  already says what they are.

| # | case | expected |
|---|---|---|
| LN1 | two words on one baseline, a third 20 pt lower | two lines, top to bottom |
| LN2 | a superscript `2` raised 3.5 pt beside `$0.40`, both 10 pt high | one line |
| LN3 | two words whose boxes overlap vertically by 40% of the smaller | two lines |
| LN4 | words given in reverse x order | each line sorted by `x0` |
| LN5 | line words with gaps of 0.3 and 2.0 em | two fragments |
| LN6 | `bold` for a line of 3 bold 3-letter words and 1 regular 12-letter word | False (9 of 21 characters) |
| LN7 | `body_size` over 40 characters at 10 pt and 12 at 14 pt; a tie of 10 at 9 pt and 10 at 11 pt | 10.0; 9.0 |
| LN8 | property: every input word is in exactly one line and in exactly one fragment | holds |
| LN9 | two words with the same text and box (a doubled text layer) | one line holding both |

### The upright page (`core/view.py`)

`upright(page) -> PageModel` returns the page as its reader sees it. The page model's coordinates
are unrotated (`02-reader.md`), so a landscape page (a `/Rotate` of 90 or 270 whose text is upright
on screen) holds nothing but vertical words.

- A page is turned upright when its `/Rotate` is not 0 **and** most of its characters are in
  non-horizontal words. Otherwise it is returned unchanged: text that is sideways on screen keeps
  the unrotated frame.
- Turning maps every word box by the rotation, with `W` and `H` the unrotated CropBox size: 90 →
  `(H − y, x)`, 180 → `(W − x, H − y)`, 270 → `(y, W − x)` (PyMuPDF's `rotation_matrix`, measured).
  Width and height swap for 90 and 270, the rotation becomes 0, and each word's `horizontal` flag
  flips, because the reader flags only the direction `(1, 0)`.
- The upright page carries no rules. M2 maps rules when it first reads them.
- Furniture, layout, and prose run on upright pages. Assembly takes every word's box from the
  reading, so the `Document` keeps unrotated coordinates.

| # | case | expected |
|---|---|---|
| VW1 | a word at (10, 20, 30, 30) on a 612 × 792 page, `/Rotate` 90, 180, and 270, with every word vertical | boxes (762, 10, 772, 30), (582, 762, 602, 772), (20, 582, 30, 602); page sizes 792 × 612, 612 × 792, 792 × 612 |
| VW2 | a `/Rotate` 90 page whose words are mostly horizontal | returned unchanged |
| VW3 | a `/Rotate` 0 page of vertical words | returned unchanged |

---

## 3 · Furniture (`core/furniture.py`, pure, document-wide)

`find_furniture(pages, profile) -> FoundFurniture`. The result holds `lines`, each with its page,
`Line`, `role`, and key, plus the set of `word_ids`. The rules are design stage 1, made exact:

1. **Lines** are `group_lines` over each page's horizontal words.
2. **The key** of a line: every token (a word's text) has each digit run replaced by `#`. A roman
   numeral here is a well-formed one of 1–6 letters in any case, such as `iv` or `XII`, but not
   `civil`.
   - If no token holds a word (every token is `#`, a roman numeral, or has no letter at all), the
     roman numerals become `#` as well: a roman page number is a page number.
   - Otherwise, if some token holds three letters in a row, leading and trailing tokens that are `#`
     or a roman numeral are stripped.
   - The tokens join with single spaces.
3. **Candidates** are lines whose median word centre lies in the top or bottom `furniture_band` of
   the page's content height (the minimum to maximum y over all its words), with two exceptions,
   because a table printed near the page edge is content:
   - a line of three or more fragments is column-shaped, a table row, and is never a candidate;
   - a line whose key recurs in the same band of the same page at the same position (an `x0`,
     `x1`, or centre within `furniture_x_tol`) is not a candidate there. The rows of a tier table
     differ only in their digits and stack in one column; a running header prints once, and a page
     number beside a stray note label sits apart from it.
4. **Frequency.** A key is furniture when it occurs as a candidate on at least
   `max(2, ceil(furniture_share × pages))` distinct pages, where `pages` counts every page of the
   document.
5. **Marking.**
   - An alphabetic key (one with a letter) is marked **wherever it occurs** on a page, in the band or
     not. The prototype's sparse last pages hold footers mid-page.
   - A numeric-only key (`#`, `# of #`, `- # -`) is marked only as a candidate, and only when its
     line sits in a column the key keeps: its `x0`, its `x1`, or its centre is within
     `furniture_x_tol` of the same measure on candidate occurrences of the key on at least the
     frequency threshold's number of pages (its own page included). A lone number is also how a
     note label renders, so position decides. The three measures cover page numbers set flush left,
     flush right (whose `x0` moves with the digit count, as JSE's do), or centred; counting pages
     per position covers mirrored numbering, flush left on even pages and flush right on odd.
6. **Role.**
   - `page_number` when the key has no letter;
   - otherwise `header` when the line's centre is in the upper half of the page, else `footer`.

Decisions are per line, never per block (L9). Non-horizontal words are never furniture.

| # | case | expected |
|---|---|---|
| FU1 | 5 pages each opening with `Acme Fee Guide` and closing with `Page N of 5` | both lines furniture on every page; roles header and footer |
| FU2 | a footer `Acme Fee Guide N`, with N at the head on odd pages, at the tail on even pages, and `i` on page 1 | one key; all five marked |
| FU3 | a key on 1 page of 5 | not furniture |
| FU4 | a 1-page document with a footer | no furniture (the floor of 2 pages) |
| FU5 | bare page numbers at x = 300 on 4 pages, plus a bare `3` at x = 72 in the bottom band of one page | the four marked `page_number`; the `3` is not |
| FU6 | an alphabetic footer key that sits mid-page on a sparse last page | marked there too |
| FU7 | a mixed line (the footer key plus a body word on the same baseline) | the line's key differs, so it is not marked (per line, never partial) |
| FU8 | no repeated edge lines | an empty result |
| FU10 | right-aligned page numbers 1–12, so `x0` moves left by a digit's width from page 10 on | all twelve marked `page_number` |
| FU11 | 3 pages, each with a running header and 5 tier rows `Tier N volume rate` in the bottom band | the header is furniture; no tier row is |
| FU12 | a 3-column header row `Tier  Volume  Rate` at the top of every page | not furniture |
| FU13 | 12 pages numbered flush left on even pages and flush right on odd pages | all twelve marked `page_number` |
| FU9 | `line_key` on `Page 3 of 12`; `- 4 -`; `iv Annual civil fees`; `2026 Fee schedule 7`; `xiv`; `- ii -` | `Page # of`; `- # -`; `Annual civil fees`; `Fee schedule`; `#`; `- # -` |

---

## 4 · Layout: column sections and reading order (`core/layout.py`, pure, per page)

`layout(words, profile, body_size) -> tuple[Region, ...]`, over one page's non-furniture words. A
`Region` is a sequence of lines, with a `kind` of `prose` or `rows`:

- `prose`: a single column of running text;
- `rows`: row order, for tables and anything column-shaped that is not prose. It is also the table
  candidate that M2's grid stage takes.

The algorithm:

1. **Lines.** `group_lines` over the page's horizontal words, and `fragments` for each line.
2. **Free space.** For each line, `free(line)` is the part of the page's x-range that its fragments do
   not cover. The page's x-range spans all of the page's horizontal words.
3. **Gutters.** For a run of consecutive lines, `G` is the intersection of their free spaces, and a
   gutter is a maximal interval of `G` at least `gutter_min_em × body_size` wide that lies strictly
   between the run's leftmost fragment start and rightmost fragment end.
4. **Sections.** Walk the lines top to bottom. From line `i`, extend the run while the run still has
   a gutter. A run with a gutter and at least `column_min_lines` lines is a **gutter section**, and the
   walk continues after it. Otherwise line `i` is a **plain line**, and the walk continues at `i + 1`.
   Consecutive plain lines form one plain section.
   - **A run starts where its columns do.** When a run's first row holds fragments in only one of
     its columns and its second row in two or more, the first row is the last line of the text above
     (a paragraph's short last line, a date set flush right): it is a plain line, and the run starts
     one row later.
5. **Classification.**
   - The gutters of a section cut it into columns, and each fragment goes to the column that holds
     its centre.
   - The section is **prose columns** when it has at least 2 columns, every column holds at least
     `column_min_lines` fragments, and every column's mean words per fragment is at least
     `prose_min_words`.
   - Prose columns become one `prose` region per column, left to right. Within a column, each source
     line contributes one line: its words in that column.
   - **A table beside the columns is cut away.** A row is *busy* when one of the section's columns
     holds two or more of its fragments: a table row whose value columns share one side of the
     gutter. In a gutter section that is not prose columns, the rows before the first busy row, or
     those after the last one, become prose columns when there are at least `column_min_lines` of
     them and they are prose columns on their own gutters. The rest of the section is walked again as
     sections of its own.
   - Any other gutter section becomes one `rows` region.
   - A plain section becomes one `prose` region.
6. **Reading order.** Sections go top to bottom; within a prose-column section, columns go left to
   right; within a region, lines go top to bottom; within a line, words go by `x0`.
7. **Non-horizontal words** (rotated labels, vertical text) become one `rows` region per maximal run
   of consecutive word ids, after the page's other regions. Each such region is one line, in id
   order.

| # | case | expected |
|---|---|---|
| LY1 | one column of 8 prose lines | one `prose` region, lines in order |
| LY2 | two prose columns of 6 lines each, gutter 24 pt, baselines aligned | two `prose` regions: all of the left column, then all of the right |
| LY3 | LY2 with the columns' baselines offset by half a line | the same two regions |
| LY4 | LY2 under a full-width title and above a full-width closing paragraph | title region, left, right, closing region, in that order |
| LY5 | a 3-column unruled table of 5 rows (a label and two values) | one `rows` region, reading row by row |
| LY6 | a hanging-indent list (labels at x = 72, text at x = 90, 5 items) | one region in row order; each label stays before its text |
| LY7 | two prose columns only 2 lines tall | fewer than `column_min_lines`: one `prose` region in row order |
| LY8 | a short last paragraph line followed by full-width lines | no gutter section; one `prose` region |
| LY9 | a vertical (rotated) label beside a paragraph | a separate `rows` region after the others |
| LY10 | property: every input word is in exactly one region | holds |
| LY11 | a dense page of 1500 lines in three columns of values | finishes in under 2 s |
| LY12 | two prose columns directly above a table whose value columns sit right of the gutter | left, right, then the table as `rows` |
| LY13 | the same table directly above the columns | the table as `rows`, then left, right |
| LY14 | a full-width paragraph whose short last line sits directly above two columns | the whole paragraph in one region, then left, right |
| LY15 | a full-width paragraph whose short last line sits directly above a 3-column table | the whole paragraph in one region, then the table as `rows` |
| LY16 | a date set flush right directly above two columns | the date, then left, right |

---

## 5 · Prose blocks (`core/prose.py`, pure)

`page_blocks(regions, lexicon, profile, body_size, gaps) -> tuple[ProtoBlock, ...]`, where `gaps` is `line_gaps` over the document. A `ProtoBlock` holds
its kind, its lines, its size (its first line's size), and its kind fields. Stage 4 claims every word
it receives. `rows` regions follow the same rules as `prose` regions: M2's table stage claims the
tables among them first, and what is left, such as hanging-indent lists, is prose.

**Breaks.** Within a region, a new block starts at a line when any of these holds:
1. its gap to the previous line (`top − previous bottom`) exceeds `max(paragraph_gap_ratio × the
   line gap of the previous line's size, paragraph_gap_floor)`. **Line gaps** are measured over the
   whole document, per size class (the size rounded to 0.5 pt), from consecutive lines of one size
   within a region: each gap is clamped at 0, and the line gap is the lower quartile, the element at
   index `(n − 1) // 4` of the sorted gaps (`line_gaps(regions)`). A size class with fewer than 4
   gaps takes the lower quartile over all sizes, or 0 when there are none:
   - clamped, because MuPDF's line boxes span the font's full ascent and descent (13.7 pt for 10 pt
     Helvetica), so lines set at ordinary leading overlap;
   - a lower quartile, because on a page of short paragraphs most gaps *are* paragraph breaks (SIX's
     numbered clauses, one or two lines each), so a median lands on a break;
   - document-wide, because a page of one-line paragraphs has no line gap of its own;
   - per size, because each type size is set with its own leading (L10): Nasdaq sets its 10.44 pt
     prose 2.8–3.5 pt apart beside 6.96 pt tables at 0, and one estimate for both splits the prose;
   - except where the sentence runs on: when the previous line ends without terminal punctuation
     (`.`, `:`, `;`, `?`, `!`) and the line opens with a lower-case letter, the gap is leading, not a
     break. JSE sets one list item at 4 pt gaps among 10 pt lists set at 0; the design's paragraph
     joins (stage 5) read the same signal;
2. its size differs from the previous line's by more than `size_change_ratio` × the previous size;
3. its `bold` state differs from the previous line's;
4. its first word `is_bullet` or is an `enumerator`.

**Kinds**, decided in this order:
5. **`footnote`:** the first line's size is at most `footnote_size_ratio × body_size`, and its first
   word is a `note_label` or a superscript word whose text, stripped of `(`, `)`, and `.`, is not
   empty. `label` is that stripped text (`01-model.md` invariant 8b).
6. **`heading`:** at most `heading_max_lines` lines and `heading_max_words` words; the first word is
   not a bullet; the last word does not end in `.`, `;`, or `,`; and the size is at least
   `heading_size_ratio × body_size`, or every line is `bold`.
   - `number` is `section_number(first word)`.
   - `level` is set during assembly: 1 plus the count of distinct heading sizes (rounded to 0.5 pt)
     in the document that are larger than this heading's.
7. **`list_item`:** the first word is a bullet or an `enumerator`. `label` is that word.
8. **`paragraph`:** anything else.

Definitions from hanging-indent glossaries arrive in M2 together with glossary grids, because both
share the term-and-body test: `08-notes-and-glossaries.md` types them after this stage.

| # | case | expected |
|---|---|---|
| PB1 | two paragraphs 10 pt apart in lines 2 pt apart | two paragraphs |
| PB2 | a 14 pt bold line above 10 pt text | a heading, then a paragraph |
| PB3 | `2.1 Transaction fees` in bold, over 10 pt body | heading, `number = "2.1"` |
| PB4 | `2026 Fee schedule` in bold | heading, `number = None` |
| PB5 | three `•` items, then a paragraph after a paragraph gap | three list items (label `•`), then a paragraph |
| PB6 | `a) The charge …` spanning 2 lines, then `b) …` | two list items, labels `a)` and `b)` |
| PB7 | 7 pt text opening `3 Applies to …` under 10 pt body | a footnote, label `3` |
| PB8 | a raised superscript `*` opening a 7 pt line | a footnote, label `*` |
| PB9 | a bold 10 pt line ending in `.` | a paragraph (rule 6 fails) |
| PB10 | a 7 pt line opening `(3)` | a footnote, label `3` (rule 5 before rule 7) |
| PB11 | a bold `• Item` line | a list item, not a heading |
| PB12 | a 12-word bold block of 3 lines | a paragraph (over `heading_max_lines`) |
| PB13 | a hanging-indent `rows` region of 3 items, each 2 lines | three list items |
| PB14 | a body-size line opening with a superscript word | a paragraph (the size rule fails) |
| PB16 | a document whose page 1 holds multi-line paragraphs and whose page 2 holds one-line clauses 8 pt apart | each clause its own paragraph |
| PB18 | a 10 pt item whose lines run on mid-sentence 4 pt apart, among tight 10 pt lines; then a line ending `.` and one opening upper case, 4 pt apart | the item is one block; the sentence end breaks |
| PB17 | loose 10 pt paragraphs (4 pt line gaps, 16 pt breaks) beside tight 7 pt rows (0 pt gaps) | the paragraphs are not split at their 4 pt gaps, and split at 16 pt |
| PB15 | the `spaced_paragraphs` fixture, read by the reader: Helvetica 10/12 with blank-line breaks, and Times 10/12 with 8 pt paragraph space | three paragraphs on each page |

---

## 6 · Assembly (`core/assemble.py`) and the text rule

`assemble(reading, pages, furniture, lexicon, profile, lattice) -> Document`, where `pages` holds
each page's `ProtoBlock`s in reading order.

**Block text (design § 8.4).** Words join with one space within a line, and lines join with one
space. When a line's last word ends in `-`, is longer than one character, and the next line's first
word starts with a lower-case letter, the two close up with the hyphen dropped, and the join is
recorded in `hyphen_joins`. No other transform exists.

**Markers:** the texts of the block's superscript words, in reading order (`01-model.md`
invariant 8d).

**Heading levels:** as § 5 rule 6, over all headings in the document.

**Order.** On each page, in order:
1. header furniture lines, top to bottom;
2. the content blocks in reading order;
3. footer and page-number furniture lines, top to bottom.

Each furniture line is its own `Furniture` block.

**Identity.** `id` is `b1..bn` in order, and `key` comes from `assign_keys((kind, text))`.

**Regions:** one per page the block touches, the union of its words there.

**Ledger:**
- `content_chars` and `furniture_chars` come from the words;
- `invisible_chars` and `clipped_chars` are the page sums.

**Findings:** the reading's findings, plus `no_furniture_long_document` when there are more than
`long_document_pages` pages and no furniture word.

**Producer:**
- versions from `reading.reader`;
- `camelot` and `pypdfium2` are `None` in M1;
- `lexicon.id`, `profile.id`, and the `lattice` setting.

**Proof.** Assembly builds the `Document`. If validation fails, it raises `InvariantError` carrying
pydantic's error text, never a `ValidationError`, because an invalid document is a bug in inkgrid.

**The pipeline (`core/pipeline.py`).** `build_document(reading, *, lexicon, profile, lattice)` runs
every page upright, furniture over the document, takes the body size over the non-furniture words, runs `layout` for
each page, takes the line gaps over every page's regions, runs `page_blocks` for each page, and
assembles. A page with no content words contributes no blocks. A
document with no words at all has no blocks, which is valid: the partition of zero words is empty.

| # | case | expected |
|---|---|---|
| AS1 | two lines `execu-` / `tions are billed` | text `executions are billed`; one join |
| AS2 | two lines `pre-` / `Market` | text `pre- Market`; no join |
| AS3 | a line ending in `-` alone (a dash) | no join |
| AS4 | the superscript `2` in `$0.40 2` | `markers == ("2",)` |
| AS5 | a page with a header, a paragraph, and a footer | block order header, paragraph, footer |
| AS6 | 9 pages without furniture; 8 pages without furniture | `no_furniture_long_document`; none |
| AS7 | a word in two proto blocks (a deliberate bug) | `InvariantError` naming the word |
| AS8 | the ledger of FU1's document | furniture characters equal the header and footer word characters |
| AS9 | headings at 18, 14, and 14 pt, and bold 10 pt | levels 1, 2, 2, and 3 |
| AS10 | two headings with the same text on one page | keys `k…` and `k…:2`; a valid `Document` |
| AS11 | a page with a `•` item, an `a)` item, and a 7 pt `(4)` note | a list item labelled `•`, one labelled `a)`, and a footnote labelled `4`, in a valid `Document` |
| PL1 | `build_document` for every `OPENABLE` fixture | a valid `Document` |
| PL2 | the `two_column` fixture | the title, then every left-column block, then every right-column block |
| PL3 | the `furnished` fixture | header and footer furniture on every page; body text in paragraphs |
| PL4 | `image_only` and `blank` | no blocks, and a valid `Document` |
| PL5 | a page whose only words are furniture | no content blocks on that page; a valid `Document` |
| PL6 | the `landscape` fixture: a `/Rotate` 90 page whose bold title and two paragraphs are upright on screen | a heading, then two paragraphs, with regions in unrotated coordinates |
| PL7 | the `rotated` fixture: horizontal text on a `/Rotate` 90 page, sideways on screen | read in the unrotated frame, as before |

---

## 7 · Acceptance

- [ ] CF1–CF10, LN1–LN9, FU1–FU13, LY1–LY16, PB1–PB18, AS1–AS11, VW1–VW3, and PL1–PL7 pass.
- [ ] Every M0 fixture assembles to a valid `Document` (the M1 exit criterion, through
      `inkgrid read`; `05-read-and-inspector.md`).
- [ ] The two-column fixture reads in column order (M1 exit criterion).
- [ ] `core/` imports only `model` and the stdlib (architecture test).
