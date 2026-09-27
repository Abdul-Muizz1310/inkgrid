# 09 · Notes, footnote calls, and continuation (M3)

**Implements:** `00-design.md` § 4.3 stages 5 (joins) and 6 (links), lessons L7 and L12, and the M3 exit
criteria: the twenty footnote-call cases pass, and the continuation fixture carries its header.
**Modules:**
- `read/words.py`: a raised, smaller run of characters opening a word is a word of its own (§ 1.3);
- `core/notes.py` (new, pure): note openers and titled note grids become footnote blocks (§ 1);
- `core/calls.py` (new, pure): call candidates, the drafting conventions, and resolution (§§ 2–3);
- `core/joins.py` (new, pure): table and paragraph continuation (§§ 4–5);
- `core/tables/proto.py`: carried cells; `core/tables/grid.py`: carried cells into the `Grid`;
- `core/assemble.py`: links and `call_unresolved` findings;
- `core/pipeline.py`: notes, then joins, after the glossary pass; `header_not_found` after joins.

No model or schema change: `Link`, carried cells, and `call_unresolved` exist since M0 (`01-model.md`).

---

## 0 · What was measured first (L19)

The 42 fee schedules (974 pages) were read with M2c's output on 2026-09-28.

- **Calls.** 873 superscript words sit in non-footnote blocks. 721 of them had no footnote block to
  point at, because most documents print their notes in forms M1 does not type as footnotes:
  - **openers smaller than their text**: LSE's `¹⁴ The charge per security…`, a 6 pt number opening
    8 pt prose. MuPDF flags a character superscript only against the line's first character, so a
    number that opens a line is never flagged (`02-reader.md` § 3). 407 blocks open this way, and 232
    of them carry a label that some superscript of the document calls. SIX's 151 are clause numbers
    no superscript calls: an opener is a note only when its label is called;
  - **openers at their text's size**: Cboe Europe's endnotes (`2 Each month a Participant's …`) and
    MIAX's marks below each table (`^ Contra to Priority Customer…`, `# For orders…`, and `*`, which M1
    read as a bullet). 53 more, each checked by eye;
  - **glued openers**: PHLX's `1A surcharge for NDX…` and IEX's `3Fees for…` and `21G physical ports`
    (note 2, then `1G`). The mark is raised and smaller (7.31 pt on a baseline 3.5 pt above 8.78 pt
    text) but unflagged, so W3 joins it to the next word. The prototype counted 64 corpus notes set
    this way;
  - **titled note grids**: Cboe prints its 54 notes as four ruled tables (`Footnotes:` /
    `Footnotes (Continued):`, `Footnote Number | Description`, then `1 | Per contract side, including
    FLEX.`), with a hidden third column, so M2c's two-column note-list rule never saw them. They are
    the register Cboe's 286 parenthetical calls resolve to.
- **Resolution, simulated** with those notes and forward-only matching (a label printed once in the
  document at any distance, a repeated label on the call's page or the next): 454 of 882 superscript
  calls resolve. Of the notes that answer a call, 179 are on the call's own page, 27 on the next, 6 two
  pages on, and a tail of endnote sections further away.
- **Superscripts that are not calls**: ordinal suffixes (`1st`, `2nd`, `3rd`, `9th`) and trade marks
  (`®`, `SM`). Call texts: digits (429), lists (`1,3,5`, `2)(3`), marks (`*`, `†`, `#`, `^`, `~`, `◊`,
  `◼`, `+`), letters (`a`–`g`), and codes (`X2`).
- **Parenthetical calls.** 1,166 `(n)` in the corpus; 290 point forward to Cboe's register. The
  prototype's decision D-21 (`docs_new/08-decisions.md`) settled how they are told from the
  parenthesised integers legal prose is full of: register membership alone admitted 48 false calls on
  Cboe, and six named drafting conventions account for all of them. Its test file carries the nineteen
  text cases of § 2.2 verbatim.
- **Table continuation.** 88 pairs of a table ending one page and a table opening the next: 51 with
  aligned columns, 35 of them with no header of their own (Nasdaq's 13-page chain on pp. 29–43, JSE's
  CDM tables), and a group that reprints the parent's header on every page (`Fee Code | Description |
  Fee/(Rebate)`). The rest are different tables that happen to meet at a page break.
  Measured column-edge offsets between the parts (same column count, footnotes and furniture skipped):
  continuations at most 1.8 pt (most under 0.4 pt; one corridor table drifts 3.84 pt), different tables
  from 18.96 pt. Half the tables' median word size, 2.6 to 6 pt on these documents, lies between.
- **Paragraph continuation.** 43 pairs of a paragraph ending a page without terminal punctuation and
  one opening the next page in lower case; every one is a sentence broken by the page.
- **Result, after M3** (the 42 documents, 974 pages, all read into valid documents): 572 of 885
  superscript calls resolve (none could before); 280 parenthetical calls resolve, 24 stay unresolved,
  and 398 candidates are rejected by a named convention; 9 named calls resolve and 6 do not. 46 tables
  continue a part on the previous page, 20 of them carrying its header, and 42 paragraphs join across
  a page break. The final review read the parenthetical calls resolved outside Cboe: the in-sentence
  enumerations it found (`has (1)`, `either (1)`) are rejected since (FC21, FC22); citations that read
  like calls remain (`Rule 900.2NY(4)`, `Article 6 (1) b)`, `Criteria (2)`). Of the 313 unresolved
  superscript calls, about half have a note printed as a text-size enumerator (`5.` … under a table),
  which § 1.1 leaves a list item.
- **Not in M3:**
  - the prototype's **inverse** class (a note that names the fee codes it applies to, `Applicable to the
    following fee codes: B, V and Y`). It links a note to codes, not a call to a note, has no `Link`
    kind, and fires on no measured document (the prototype's F-38); the twentieth prototype case
    records its absence (FC20);
  - a paragraph continued in the next **column** of the same page: every measured break is a page break;
  - continuation of **list items and footnotes** across a page: the design names paragraphs.

---

## 1 · Notes

A **note** is a footnote block. M1 types some (small type opening with a label, `04` § 5), M2c dissolves
note-list grids (`08` § 3), and M3 adds three forms. A label is **called** when some superscript call
of the document (§ 2.1) carries it.

### 1.1 Note openers

A paragraph or list item becomes a footnote when its first line opens with a label and:

1. the label is a `note_label` (`1`, `(3)`, `a)`, `*`, `†`), a **mark** (a run of up to 4 of `*`, `†`, `‡`,
   `§`, `¶`, `#`, `^`, `~`, `+`, `!`, `&`, or symbols such as `◊` and `◼`, or any geometric shape (U+25A0–U+25FF) and `⧫`: MIAX calls with `^`, `~`, `◊`, `◼`, `⧫`), or a
   single letter;
2. the label is called, and the label word is not flagged superscript (a flagged word opening a line is a
   call wrapped onto it, never a note: calls and notes stay disjoint);
3. at least 3 words follow it on its first line;
4. it is set smaller than the text after it (at most 0.92 × the median size of the rest of the line), or,
   for a bare number (no `.` or `)`) or a mark, no larger (at most 1.05 ×); a single letter must be smaller;
5. the text after it is not larger than the body (at most 1.05 × `body_size`) and not mostly bold: a
   heading's number is large and its title bold.

The footnote's `label` is its first word without `().` (`01-model.md` 8b).

| # | case | expected |
|---|---|---|
| OP1 | a 6 pt `14` opening 8 pt prose, `14` printed raised after a fee elsewhere | a footnote, label `14` |
| OP2 | the same, with no superscript `14` anywhere | a paragraph |
| OP3 | a 10 pt `2` opening 10 pt prose, `2` called | a footnote |
| OP4 | a 10 pt `^` opening 10 pt prose, `^` called; a 10 pt `*` list item, `*` called; `◼`, `⧫`, `◊` likewise | footnotes |
| OP5 | a 10 pt `1)` opening 10 pt prose, `1` called | a list item (an enumerator at text size) |
| OP6 | a 7 pt `1)` opening 10 pt prose, `1` called | a footnote, label `1` |
| OP7 | a flagged superscript `3` opening a line of prose, `3` called elsewhere | not a footnote |
| OP8 | a 12 pt bold `1` opening 14 pt bold `Transaction Fees Apply` | not a footnote |
| OP9 | a 6 pt `7` opening two words | not a footnote |
| OP10 | a 7 pt `a` opening 9 pt prose, `a` called; a 9 pt `a` opening 9 pt prose, `a` called | a footnote; a paragraph |

### 1.2 Titled note grids

A table dissolves into footnotes when:

- its header rows hold a **notes word** (`note`, `notes`, `footnote`, `footnotes`, whole words, ignoring
  case and trailing `:`), and no value;
- it has at least 2 body rows (rows below the header), and each holds exactly two filled cells: a
  single-word label in column 0 that is a `note_label`, and text beside it, in column 1 or spanning
  from it, that is not a value.

Each header row becomes a heading block (its cells' lines, left to right), and each body row a footnote
whose first word is its label. The blocks take the table's place (`08` § 5). A note's text may be short:
Cboe's notes 32 and 51 read `Reserved.`.

| # | case | expected |
|---|---|---|
| NG1 | `Footnotes:` over `Footnote Number \| Description`, then `1 \| Per contract side, including FLEX.` and `2 \| Reserved.`, with an empty third column | two headings, then footnotes `1` and `2` |
| NG2 | the same without a notes word in its header | a table |
| NG3 | a notes header over `B \| 1.20%` and `C \| 0.95%` | a table |
| NG4 | a notes header over rows of three filled cells | a table |

### 1.3 Glued openers (the reader)

W3 (`02-reader.md` § 3) gains a condition: a run does not join the next run when it is smaller (at most
0.92 × the next run's size) and raised: its box's bottom sits above the next run's by more than 0.2 × the
next run's size. (The raw characters carry boxes, not baselines; a smaller run on the same baseline, such
as small capitals, sits only its smaller descent higher, about 0.04 × the size.) The raised run becomes a word of its own; its `superscript` stays MuPDF's flag, so a glued
opener reads as an opener (§ 1.1), not a call.

| # | case | expected |
|---|---|---|
| W-22 | a 7.31 pt `1` whose box bottom sits 3.79 pt above an 8.78 pt `A surcharge`'s, one line, no space | words `1`, `A`, `surcharge`; `1` is not superscript |
| W-23 | a 7 pt `2` whose box bottom sits 0.4 pt above a 10 pt `Fee`'s (small capitals, not raised); a raised 10 pt `2` before a 10 pt `Fee` | one word `2Fee`; one word `2Fee` (not smaller) |

---

## 2 · Call candidates

Calls are found in every non-furniture block's words and text; in a table, cell by cell (`from.cell` is
the cell's anchor), skipping carried cells. A footnote's first word is its label, not a call, and a note
never calls its own label.

### 2.1 Superscript calls

Each superscript word is split at `,` and between `)(`, and each part is stripped of `().`. A part is a
call unless it is empty, longer than 4 characters, an ordinal suffix (`st`, `nd`, `rd`, `th`), or a
trade mark (`®`, `™`, `©`, `SM`, `TM`). Its method is `superscript`.

| # | case | expected |
|---|---|---|
| SP1 | `$0.40` then a superscript `2` | a call `2` |
| SP2 | a superscript `1,3,5`; a superscript `(2)(3)` | calls `1`, `3`, `5`; `2`, `3` |
| SP3 | `2` then a superscript `nd`; `Nasdaq` then a superscript `SM` | no call |
| SP4 | a footnote `^ Contra to …` whose first word `^` is superscript | no call from its label |
| SP5 | `Fee` then a superscript `(52)`, note `52` in the register | one call, by superscript (the parenthetical scan reads only words set at the text's level) |

### 2.2 Parenthetical calls (D-21)

In the text of each block (each cell, for a table), leaving out its superscript words (a raised `(52)` is a
superscript call, § 2.1), every `(n)` with 1 to 3 digits is a candidate when
the document holds a note labelled `n`; with no note labelled `n` there is nothing to admit it, and it
is no candidate at all. The tests run in this order, and the first that applies decides. Let `before`
be the text before `(n)`, `pb` it with trailing spaces removed, and `word` the last alphabetic word of
`pb`:

| # | reason | condition |
|---|---|---|
| 1 | `clause-initial` | `pb` is empty |
| 2 | `sub-clause-enumerator` | `pb` ends in `,`, `;`, or `:` |
| 3a | `statutory-citation` | `pb` ends in `)`, no space precedes `(n)`, and the group before it is one lower-case letter or a lower-case roman numeral (`[ivxl]{1,4}`) |
| 3b | accept | `pb` ends in `)` otherwise: a marker run, or a marker after an aside |
| 4 | `attached-to-number` | no space precedes `(n)` and `pb` ends in a digit |
| 5 | `spelled-number-gloss` | `word`, case-folded, spells `n` (`one` … `twenty`, `thirty` … `sixty`) |
| 6 | `function-word` | `word` is lower case and a function word (`and`, `or`, `except`, `excluding`, `including`, `than`, `that`, `if`, `of`, `to`, `for`, `in`, `by`, `with`, `the`, `a`, `an`, `is`, `are`, `be`, `as`, `at`, `on`, `from`, `provided`, `least`, `plus`, `per`, `over`, `under`, `between`; and, beyond D-21, `has`, `have`, `had`, `either`, `both`, `whether`) |
| 7 | `no-anchor` | `pb` does not end in a letter, digit, `%`, `.`, `]`, or `}` (beyond D-21: Cboe's `{FF} (11)`) |
| 8 | accept | otherwise: a marker attached to a noun phrase, a value, or a capital letter |

Test 6 is case-sensitive: `Underlying Symbol List A (34)` anchors on a capital `A`. An accepted candidate
is a call with method `parenthetical`; a rejected one becomes a `rejected` link carrying its reason. The
nineteen text cases, each against a register holding every label from `1` to `54` (so the convention
decides):

| # | text | calls |
|---|---|---|
| FC1 | `AIM Agency/Primary (19)` | `19` |
| FC2 | `Customer (2)(8)(9)` | `2`, `8`, `9` |
| FC3 | `Sector Indexes (47)(11)` | `47`, `11` |
| FC4 | `$0.00 (47)` | `47` |
| FC5 | `Volume Incentive Program (VIP)(6)(23)(36)` | `6`, `23`, `36` |
| FC6 | `Surcharge Fee (14) (Also applies to GTH)(37)(42)` | `14`, `37`, `42` |
| FC7 | `Rate Table - All Products Excluding Underlying Symbol List A (34) and Binary Options` | `34` |
| FC8 | `Underlying Symbol List A (34) (except RLG, RLV, RUI, and UKXM)` | `34` |
| FC9 | `involves a complex order with at least five (5) different series` | none (`spelled-number-gloss`) |
| FC10 | `for a period of two (2) years from the date of enrollment` | none (`spelled-number-gloss`) |
| FC11 | `as that term is defined in Section 202(a)(11) of the Investment Advisers Act` | none (`statutory-citation`) |
| FC12 | `transaction fees in all products except (1) Underlying Symbol List A (34), DJX` | `34`; `1` rejected (`function-word`) |
| FC13 | `(2) volume executed in open outcry, (3) volume executed via AIM Responses` | none (`clause-initial`, `sub-clause-enumerator`) |
| FC14 | `organization; (2) if the trading floor reopens mid-month` | none (`sub-clause-enumerator`) |
| FC15 | `calendar month; and (9) the AIM Contra Surcharge` | none (`function-word`) |
| FC16 | `(1) TPH has SPX Customer capacity volume during the month` | none (`clause-initial`) |
| FC17 | `Fees are assessed only on items that are (1) lost or (2) damaged` | none (`function-word`) |
| FC18 | `payable in 2026 (99) and thereafter` | none: `99` is in no note, so it is no candidate |
| FC19 | `Please see Customer Large Trade Discounts table and footnote 27 for details` | `27` (named, § 2.3) |
| FC20 | `Add/Remove Volume Tiers. Applicable to the following fee codes: B, V and Y.` in a note | no link (the inverse class is not in M3, § 0) |
| FC21 | `a Member has (1) a Tape B ADAV of at least 0.10%` (MEMX; not a prototype case) | none (`function-word`) |
| FC22 | `collected from either (1) a Participant or (2) a Member`; `whether (1) the order` (BOX) | none (`function-word`) |
| FC23 | `Firm Facilitated Rebate {FF} (11)` (Cboe) | `11` |

### 2.3 Named calls

`footnote n` or `footnotes n` (any case, `n` 1 to 3 digits) is a call with method `named`, whether or
not a note carries `n`: the word says what it is.

---

## 3 · Resolution

The register is the document's notes in reading order. A call resolves **forward only**, to a note
after the calling block (documents restart their numbering per table, so a note before the call
answers a different call):

1. when the call's label is carried by exactly one note of the document, that note, however far on;
2. otherwise, the first note with the label after the calling block, on the call's page or the next. A
   superscript call's page is its word's (so a call in a joined paragraph's second part looks from
   its own page); the other calls take their block's first page. For a table that continues (§ 4),
   the window runs to the page after its chain's last part: a long table's notes follow its end.

A note is never taken from a page before the call's own. `call_unresolved` names the page the call is
printed on.

A call that resolves is a `resolved` link to the note; one that does not is `unresolved`. Each page with
unresolved calls raises one `call_unresolved` (warning) naming how many and their labels. A block that
calls one label twice by one method gives one link. Links follow their blocks' reading order; within a
block, superscript calls come first, then parenthetical, then named, each in the order they are printed.

| # | case | expected |
|---|---|---|
| FR1 | a call `3` on page 1, note `3` on page 4, no other note `3` | resolved to it |
| FR2 | calls `1` on pages 1 and 3, notes `1` at the foot of pages 1 and 3 | each to its own page's note |
| FR3 | a call `1` on page 1 and notes `1` on pages 3 and 5 | unresolved; one `call_unresolved` on page 1 |
| FR4 | a note `2` on page 1, then a call `2` on page 2, no later note `2` | unresolved (never backward) |
| FR5 | a table continuing over pages 4 and 5 calling `1`, notes `1` on pages 5 and 9 | resolved to page 5's |
| FR6 | FC12's text in a paragraph, with notes `1` and `34` later | one resolved link `34`; one rejected link `1`, reason `function-word` |
| FR7 | a table cell `Fee^2` (row 1, column 1), note `2` below the table | a link from `{table, cell (1, 1)}` |
| FR8 | a note `27` whose text says `see footnote 27` | no link (a note never calls itself) |
| FR9 | a paragraph calling `2` twice by superscript, note `2` later | one link |
| FR10 | a paragraph joined across pages 1 and 2, its page-2 part calling `1`; notes `1` at the foot of both pages | resolved to page 2's note |
| FR11 | a table continued from page 1 to 2 whose page-1 cell calls `4`, with no note `4` | `call_unresolved` on page 1 |

---

## 4 · Table continuation

A table **continues** onto the next page when:

- the parent is the last block of its page and the child the first of the next, counting neither
  furniture nor footnotes (a page's notes sit below its body and belong to no flow; L12's lowest *block*,
  not lowest text);
- both are tables in the same frame with the same number of columns, and every column edge of the child
  lies within half their median word size of the parent's (L10);
- and either:
  - **the child prints no header** (`header_rows == 0`): it carries the parent's header (below), or
    nothing when the parent prints none either; or
  - **the child reprints the parent's header**: its header rows' texts equal the parent's, row by row,
    with spaces normalised. Nothing is carried.

A continuation is a `continuation` link from the child to the parent. A chain links each part to the one
before it.

**What is carried.** For each header cell of the parent (`row < header_rows`), the child gains a cell at
the same row, column, and spans: a carried cell with the parent cell's text and the parent cell as its
`source`, or an empty cell when the parent's is empty. The child's `header_rows` becomes the parent's,
and its body rows move down by as many. The carried rows get bands directly above the child's first
row, with the parent's header heights scaled by `min(1, room / their total)`, where `room` is the
distance from the child's top to the bottom of the nearest block or furniture line above it on its page
(or the page top), so a carried band never lies over the running header.
A parent that carries its own header passes those cells on, so a chain's header is always the first
part's. `header_not_found` is raised after continuation, so a child with a carried header raises none.

| # | case | expected |
|---|---|---|
| TC1 | `continued_table`: `Fee \| Rate` over two rows at a page's foot, two headerless rows opening page 2 | page 2's table has carried cells `Fee`, `Rate`, `header_rows = 1`, and a link to page 1's table |
| TC2 | TC1 with a paragraph after page 1's table | no continuation |
| TC3 | TC1 with a footnote under page 1's table | a continuation |
| TC4 | TC1 with a heading above page 2's table | no continuation |
| TC5 | TC1 with page 2's table in 3 columns | no continuation |
| TC6 | TC1 with page 2's columns 20 pt to the right | no continuation |
| TC7 | TC1 with page 2's table printing `Fee \| Rate` again | a continuation, nothing carried |
| TC8 | TC1 with page 2's table printing `Band \| Charge` | no continuation |
| TC9 | TC1 over three pages | page 3 links to page 2 and carries `Fee`, `Rate`, sourced from page 2's carried cells |
| TC10 | TC1 whose page 1 header is two rows, one an empty cell | page 2 carries the non-empty cells and has an empty cell where the parent's is empty |
| TC11 | TC1 read end to end | a valid `Document`; no `header_not_found` for page 2's table |
| TC12 | a table whose `continues` names a table missing from the document | `InvariantError` (a bug, never a silently dropped link) |
| TC13 | TC1 whose page 1 table prints no header either | a continuation, nothing carried |
| TC14 | TC1 with a running header line ending 2 pt above page 2's table | the carried band lies below the header line |

---

## 5 · Paragraph continuation

A paragraph **continues** onto the next page when it is the last block of its page and the first block
of the next is a paragraph (counting neither furniture nor footnotes, as § 4), its text does not end in
`.`, `:`, `;`, `?`, or `!`, and the next paragraph's first word opens in lower case. The two become one
block, the first's lines then the second's, with one region per page; its text is rendered across the
break, so a hyphen at the page's foot joins a lower-case continuation (`04` § 6). A chain of pages joins
into one block.

| # | case | expected |
|---|---|---|
| PJ1 | `continued_paragraph`: `… the fee is charged per` at page 1's foot, `executed order.` opening page 2 | one paragraph, two regions (pages 1 and 2) |
| PJ2 | PJ1 ending `per order.` | two paragraphs |
| PJ3 | PJ1 with page 2 opening `Executed orders …` | two paragraphs |
| PJ4 | PJ1 ending `execu-` and opening `tions are billed.` | one paragraph `… executions are billed.`, the join recorded |
| PJ5 | PJ1 with a heading opening page 2 | two paragraphs |
| PJ6 | PJ1 with a footnote at page 1's foot below the paragraph | one paragraph; the footnote stays a block of its own |

---

## 6 · Pipeline

After the glossary pass (`08` § 5): notes (§ 1), then table and paragraph continuation (§§ 4–5), then
`header_not_found` for every table, then assembly, which numbers the blocks, finds and resolves calls
(§§ 2–3), and builds the links and `call_unresolved` findings before the `Document` validates them.

| # | case | expected |
|---|---|---|
| LK1 | `footnoted_table`: a table whose fee carries a raised `1`, then a 7 pt `1 Applies to …` below it | a resolved link from the fee's cell to the footnote |
| LK2 | `glued_notes`: a raised 7 pt `1` glued to `A surcharge …` at 9 pt, called above | a footnote labelled `1`; the call resolved |
| LK3 | every `OPENABLE` fixture | a valid `Document` |

---

## 7 · Acceptance

- [ ] OP1–OP10, NG1–NG4, W-22–W-23, SP1–SP5, FC1–FC23, FR1–FR11, TC1–TC14, PJ1–PJ6, and LK1–LK3 pass.
- [ ] The twenty call cases (FC1–FC20) pass, and `continued_table` carries its header (the M3 exit).
- [ ] The seven fee schedules and the 42-document corpus read without error, and each document's
      resolved, unresolved, and rejected calls are counted and compared with § 0.
- [ ] Every M0–M2 case still passes.
