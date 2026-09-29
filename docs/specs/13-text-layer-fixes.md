# 13 · The text layer on public corpora: overprints, control codes, glyph names, boxes, marks (M5c-1)

**Implements:** the text-layer half of spec 11 § 5's "what stays reported", after M5b recorded the
baseline (`12-benchmark.md`, `DR-0023`). It amends `02-reader.md` (§§ 4, 6), `04-text-pipeline.md`
(§ 2), `10-verify.md` (§§ 3.2, 6), and `01-model.md` (`PageInfo`, `Ledger`, findings).
**Modules:**
- `read/words.py`: overprinted words (§ 1), control codes in Type 3 fonts (§ 2);
- `read/glyphs.py` (new, pure) and `read/pymupdf_reader.py`: glyph names (§ 3), the page box (§ 4);
- `core/lines.py`: a raised mark glued to its value (§ 5);
- `verify/ownership.py`: overprint copies (§ 1.3);
- `model/page.py`, `model/document.py`, `model/findings.py`, `model/verification.py`,
  `core/assemble.py`, `model/invariants.py`: the new counts and the finding.

**Tuned.** These rules were designed while looking at ICDAR-2013 and olmOCR-bench's failures. Any
benchmark result after them is labelled as tuned on those sets (DR-0023); the 42 fee schedules and
the fixture suite guard against regressions, and M5d's held-out set is the test no fix has seen.

---

## 0 · What was measured first (L19)

Each class was traced, on 2026-09-29, from both engines' raw readings (PyMuPDF `rawdict`,
`get_texttrace()`; PDFium's characters and flags), the content streams, and rendered crops; each rule
was prototyped in memory and run one document at a time over the three benchmark corpora and the 42
fee schedules.

- **Overprinted text (47 defects).** The same string is drawn twice at one place, and MuPDF returns
  both copies:
  - a banner painted twice under the same clip (competition us-020 pp. 1, 3, 5; us-021 pp. 1, 3),
    identical spans;
  - WordArt's shadow: five copies within 0.042 em of each other (olmOCR f86995);
  - stroke then fill at the same origin (`1 Tr … 0 Tr T*` under `0 TL`, olmOCR c8cdd4).

  MuPDF collapses glyph-by-glyph fake bold within one line, but never a whole string drawn again
  later. PDFium drops some copies heuristically (a text object equal to one of the previous five; a
  glyph within 0.07 em of one of the previous seven with the same code and font), partially and in
  order: f86995 keeps 3 of its 5 copies. **olmOCR 6fedb9 reports no defect, yet its whole Table 1 is
  drawn twice (652 characters):** PDFium keeps both copies too, so inkgrid's doubled table is
  invisible to the verifier.
- **The nearest legitimate same-text neighbours** are 0.166 em apart across the 1,570 benchmark pages
  and 0.205 em (`ll`) across the 974 fee-schedule pages. Practice us-022 prints `FY 2008` in white,
  covers it with an image, and prints `FY 2011` 0.44 pt away: a rule per character would read `11`.
  Practice us-008 p. 2 draws four different Type 3 picture glyphs at one origin, three of them U+FFFD.
- **Control codes (45 defects, olmOCR e247cacc).** Type 3 fonts with no ToUnicode name their digit
  glyphs `/0`…`/9`. MuPDF reads a decimal glyph name outside the Adobe Glyph List as that code point
  (`/1` → U+0001, `/9` → U+0009, `/65` → `A`), and the reader drops the Cc characters as invisible:
  48 characters of subscripts (`t₁`, `t₂`) and a citation `[9, 14]`. Outside Type 3 fonts, the only
  non-whitespace control characters in any corpus are 13 U+0007 that draw nothing, and a Dingbats
  space glyph MuPDF returns as a tab (olmOCR 1a67d1). The fee schedules have none.
- **Glyph names (5 DECODE).** olmOCR 529eeb's `ZapfDingbatsITC` subset encodes code 3 as `/a71`, with no
  ToUnicode: MuPDF reads `G` (the name's digits as a code point), PDFium reads `●`, and the page draws
  a red bullet. olmOCR 4fafd7's `LASY10` names a glyph `/a50`: MuPDF reads `2`, PDFium `✷` (it applies
  the Dingbats list to any font), and the page draws □. The Adobe Glyph List specification applies
  the ZapfDingbats list only to Zapf Dingbats fonts. Exactly these 5 characters meet § 3's condition
  in 2,544 pages; none in the fee schedules.
- **The page box (1 defect, olmOCR 30c92c).** `/CropBox [0 -4.3 602.29 841]` overhangs `/MediaBox [0
  0 596 841]`. The reader takes 602.29 × 845.3; PDF 32000-1 § 14.11.2 reduces any box that extends
  past the MediaBox to their intersection, which PDFium uses, so the page is UNVERIFIED. MuPDF already
  measures text from the intersection's corner; only the width and height are wrong. Two pages in all
  corpora overhang (the other, olmOCR bdb0c0, by 0.47 pt); none in the fee schedules.
- **A raised mark (1 defect, olmOCR 2d54e9).** A cell prints `.54` with a raised 5.56 pt mark, glued
  on the same MuPDF line. `group_lines` clusters page-wide in centre order, and the mark, reached
  before its row, overlaps the next column's reference line by 3.13 pt (more than half its height), so
  it joins that line and becomes a footnote with no body. A rule moving any smaller glued word moved
  107 words in skewed OCR layers; § 5's superscript-only rule moves 2 words in all corpora (both
  correct), none in the fee schedules.

**Prototype result:** all 99 defects of these classes gone, none new; the fee schedules read exactly
as before (8 cells reported, every rule counter 0).

---

## 1 · Overprinted text

### 1.1 The rule (`read/words.py`, amends `02-reader.md` § 4)

- **W8. An overprinted word is read once.** After tokens become words and before they are numbered,
  a word W is dropped as a copy of an earlier kept word K on the same page (`rawdict` order; W is
  compared with kept words only, so copies never chain) when all of these hold:
  1. W and K have equal `text`, `font`, `size` (2 dp), `hidden`, `horizontal`, and `superscript`;
  2. the text holds no U+FFFD, and the font is not a Type 3 font (picture glyphs share codes);
  3. each of W's four box edges lies within `0.1 × W.size` of K's matching edge.

  The unit is the word, never the character. A dropped word's characters are counted as
  `overprinted_chars`. W8 applies to the clipped and the unclipped readings alike, so `clipped_chars`
  (the unclipped reading's characters minus the clipped reading's) never counts a copy.
- **Why 0.1 em:** the largest copy offset measured is 0.042 em, and PDFium's own glyph test uses
  0.07 em; the nearest legitimate same-text neighbour is 0.166 em apart. A whole word can come nearer
  than that to its own copy only by being drawn twice.
- **What stays two words:** the same value in two cells; `ll` and dot leaders; a hidden word under
  its visible twin (an OCR layer: `hidden` differs); us-022's two years (the text differs); a shadow
  further than 0.1 em (kept, and reported DOUBLED if PDFium collapses it); Type 3 pictures. W7's clip
  copies are removed before W8 runs.

### 1.2 The count and the finding

- `PageInfo.overprinted_chars: NonNegativeInt = 0` (the reading and the document), and
  `Ledger.overprinted_chars` (the document's sum). The ledger invariant: `overprinted_chars` equals
  the sum over pages.
- A new info finding, **`overprinted_text`**, on each page with `overprinted_chars > 0`; its detail
  gives the count. It is page finding 4a, after `clipped_text` (`02-reader.md` § 6).
- The text rule (G2) is unchanged: every word of the document is owned exactly once. A dropped copy
  was never a word; it is accounted for like a clipped or invisible character, by count.

### 1.3 The verifier (`verify/ownership.py`, amends `10-verify.md` § 3.2)

PDFium keeps some copies and drops others, so a page where inkgrid now reads a string once can still
show PDFium two or more copies:

- **Overprint copies.** A character that would be LOST, of kind ink or unmapped, unowned or left over
  in a word, is an **overprint copy** when an owned ink character has the same code point, a loose box
  of the same width and height within 0.5 pt, and a centre within `0.1 ×` that box's height of its
  own. The class is accepted while the page's overprint copies number at most the reader's
  `overprinted_chars`; beyond that, every one of them is LOST.
- `PageCheck.overprint_chars` counts them, and joins the verified page's sum: `ink = owned + lost +
  outside + clipped + soft_hyphens + overprint`. A declared or unverified page counts none.
- The class is bounded by the reader's own count, like clipped characters and soft hyphens: a copy
  the reader dropped that PDFium also sees is benign, and a character the reader lost is still LOST.

---

## 2 · Control codes in Type 3 fonts (`read/words.py`, amends `02-reader.md` § 4)

- **Character classes, amended.** In a span whose font is a Type 3 font, a character of category Cc
  (U+0000–U+001F and U+007F–U+009F, the whitespace controls U+0009–U+000D and U+001C–U+001F
  included) is a **glyph with no Unicode**: it reads U+FFFD, is a word character, and counts in
  `unmapped_chars`. Every Type 3 code runs a glyph procedure, so the character is drawn; MuPDF's code
  point came from a glyph name no Unicode mapping defines.
- Outside Type 3 fonts, a control character stays invisible (and a whitespace control stays
  whitespace): the measured ones draw nothing.
- `build_words` takes the page's Type 3 font names.

---

## 3 · Glyph names outside the Adobe Glyph List (`read/glyphs.py`, `read/pymupdf_reader.py`)

- **The condition.** A character of an embedded Type 1 font (`Type1`, `MMType1`, or `Type1C`) with no
  ToUnicode, whose glyph name — with any `.suffix` removed — matches `a?[0-9]+` and is not in the Adobe
  Glyph List (`fz_unicode_from_glyph_name_strict` returns 0).
- **The reading.** If the font's name, subset tag removed, contains `Dingbats` and the glyph name is in
  Adobe's ZapfDingbats glyph list (`zapfdingbats.txt`, BSD-3-Clause, shipped as data in
  `read/glyphs.py`), the character is that list's code point. Otherwise it is U+FFFD (a glyph with no
  Unicode), counted in `unmapped_chars`.
- **Finding the name.** The glyph name comes from the font program: `get_texttrace()` gives each
  character's glyph id, and MuPDF names it (`fz_get_glyph_name2` on the extracted font). A trace
  character is matched to a `rawdict` character by font and origin. Only pages that use a font whose
  encoding or character set names such a glyph are traced, so a document without one pays nothing.
- Without this rule MuPDF invents a letter from the name's digits (G1); PDFium's own reading of a
  non-Dingbats font is no better, so DECODE there is resolved by U+FFFD on inkgrid's side, which the
  verifier pairs with any character (spec 10 § 3.1).

---

## 4 · The page box (`read/pymupdf_reader.py`, amends `02-reader.md` § 6)

- **Geometry, amended.** `width` and `height` are those of the **CropBox clipped to the MediaBox**
  (PDF 32000-1 § 14.11.2), and coordinates are measured from its top-left corner. One helper computes
  it in PDF coordinates, `(crop.x0, media.y1 − crop.y1, crop.x1, media.y1 − crop.y0)` intersected
  with the MediaBox, since PyMuPDF gives `cropbox` from the top left and `mediabox` in PDF
  coordinates; the page frames and the copy Camelot reads use the same box.
- A CropBox that does not meet the MediaBox leaves no page: `unreadable_page` (error), and no words.

---

## 5 · A raised mark glued to its value (`core/lines.py`, amends `04-text-pipeline.md` § 2)

- **After clustering,** a superscript word glued on its left to a non-superscript word v moves to v's
  line when clustering put it on another line, unless it is also glued to a word of its own line.
  *Glued*: `−1.0 ≤ w.x0 − v.x1 ≤ 0.6` pt, and a vertical overlap of at least `0.3 ×` the smaller
  height (W3's join geometry). MuPDF sets the superscript flag against the mark's own line, so a
  flagged mark glued to v was read on v's line.
- Lines are re-sorted after the move; the word keeps its id and its box.

---

## 6 · Cases

| Case | Input | Expected |
|---|---|---|
| OP1 | `HIGHLIGHTS FROM` drawn, then `between` elsewhere, then `HIGHLIGHTS FROM` again at the same place | each word once; `overprinted_chars` 14; an `overprinted_text` finding; verification clean |
| OP2 | `PRESS` stroked (mode 1), then filled at the same origin | one `PRESS` |
| OP3 | typed words: a copy of `Fee` offset by 0.10 × size; by 0.11 × size | dropped; kept |
| OP4 | typed words: `FY 2008` then `FY 2011` 0.44 pt away; `1.00` twice 40 pt apart | `FY`, `2008`, `2011`; both `1.00` |
| OP5 | typed words: a hidden word under its visible twin; two U+FFFD words at one place | both kept; both kept |
| OP6 | a shadow drawn five times within 0.03 em (WordArt's `Tf 1` with a 30 × matrix) | the text once; verification clean (overprint copies accepted) |
| OP7 | a clipped reading and an unclipped reading of a page with a copy | `clipped_chars` 0 |
| OP8 | the ledger of a document with copies on two pages | `overprinted_chars` is their sum; a wrong sum fails validation |
| VO1 | PDFium shows three copies where the reader kept one and counted two | owned 1 copy's characters, overprint 2 copies' |
| VO2 | the same page with the reader's count one short | every overprint copy LOST |
| VO3 | a copy 0.6 pt wider than the owned character | LOST |
| VO4 | `PageCheck` with `overprint_chars` left out of the sum | fails validation |
| T31 | a Type 3 font with no ToUnicode naming `/1` and `/9`: `t`, a lowered `1`, then `[`, `9`, `,` | words `t`, `�`, `[�,`; `unmapped_chars` 2; verification clean |
| T32 | typed: a Cc character in a non-Type-3 span; a tab in a Type 3 span | invisible; U+FFFD |
| GN1 | a `ZapfDingbatsITC` subset encoding code 3 as `/a71`, no ToUnicode | the word `●`; verification clean |
| GN2 | the same font named `LASY10`, code 50 as `/a50` | U+FFFD; `unmapped_chars` 1; verification clean |
| GN3 | typed: `a71` in a Dingbats font; `a71` elsewhere; `a71.alt`; `A`; `uni2022` | `●`; None (U+FFFD); `●`; not applicable; not applicable |
| CB1 | MediaBox 600 × 800, CropBox `[-50 -50 650 850]`, text at x = 100 | 600 × 800; the word at x = 100; verification clean |
| CB2 | CropBox `[0 -4.3 602.29 800]` over MediaBox 600 × 800 | 600 × 800 |
| CB3 | a CropBox beyond the MediaBox entirely | `unreadable_page`; no words |
| MK1 | a 9 pt `.54` with a glued raised `*`, and a line in the next column 7 pt higher that the `*` overlaps by more than half its height | the `*` on `.54`'s line; no footnote block |
| MK2 | typed: a raised mark glued to its value that also glues to a word of its own line | stays |
| MK3 | typed: a non-superscript small word glued to a value on another line | stays |
| MK4 | property: every word is in exactly one line after the move (LN8) | holds |

Every existing case keeps passing: W-1…W-23, X1…X19, LN1…LN9, OW1…OW5, and the verifier's.

## 7 · Acceptance

- [x] Every case above has a test named `test_<CaseId>_<slug>`, and it failed before its code (OP7,
      MK2, MK3, and MK4 guard what must not change, and passed before it).
- [x] On the named documents, one at a time: the defects of these classes are gone (us-020, us-021,
      f86995, c8cdd4, e247cacc, 529eeb, 4fafd7, 30c92c, 2d54e9), none is new, and olmOCR 6fedb9 reads
      its table once.
- [x] The 42 fee schedules read exactly as before (the M5c gate's full-text dumps), with their 8
      cells.
- [x] Every `OPENABLE` fixture verifies with no defect; `docs/schema/` is regenerated; README,
      CHANGELOG, and the amended specs say what changed.

**Measured** (2026-09-29, the M5c gate at `2761d07` against the baseline at `4a900cf`, one document
at a time): the 31 named documents' defects fall from 316 to 217, exactly the 99 of these classes,
on exactly the nine documents above; no other document's count moves. Of the others, only practice
us-022's text changes, and rightly: its overprinted `FY` reads once (`FY 2008 2011`, not `FY FY 2008
2011`). The 42 fee schedules' dumps are byte-identical.
