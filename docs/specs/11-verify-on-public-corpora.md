# 11 · The verifier on public corpora (M5a)

**Implements:** `00-design.md` § 2 success criterion 1 (G1–G4 hold on every benchmark document: the
verification report is clean, or every defect in it is explained), for the first public benchmark
corpora, before the benchmark (M5b) scores anything. It amends `10-verify.md`.
**Modules:**
- `verify/ink.py`: character kinds (§ 1.1), surrogate pairs (§ 1.2);
- `verify/pdfium_reader.py`: surrogate pairs joined; clips through their forms (done: VR17);
- `verify/ownership.py`: ligatures (§ 2.1), second-chance pairing (§ 2.2), repair of greedy
  ownership (§ 2.3), decode disagreements (§ 2.4);
- `verify/checks.py`: value tokens (§ 3.1), overlays (§ 3.2);
- `model/verification.py`: `DefectCode.DECODE`, `PageCheck.ligature_chars` and `overlay_chars`;
- `read/camelot_reader.py`: a Camelot table that holds no cells (done: CM11).

**No reading changes.** Every fix here is in the verifier, apart from the Camelot crash, which
returned no document at all. inkgrid's own errors found on these corpora are the benchmark's to
measure: fixing them now, using the benchmark's test documents, would tune inkgrid on its own test
set. They are listed in § 5, stay reported, and are fixed after M5b records the baseline.

---

## 0 · What was measured first (L19)

inkgrid at `11871a7` (M4) read and verified, one document at a time, on 2026-09-28:

| Corpus | Documents | Pages | Tables | Defects (documents) | Crashes |
|---|---|---|---|---|---|
| ICDAR-2013 competition | 67 | 238 | 215 | 112 (19) | 0 |
| ICDAR-2013 practice | 58 | 170 | 118 | 174 (11) | 0 |
| olmOCR-bench tables | 188 | 188 | 188 | 338 (27) | 1 |

Every defect was classified by its mechanism, from both engines' raw readings and a rendered crop
(the 624 add up):

- **301 are engine differences or verifier bugs; inkgrid's output is right.** § 1–3 name them.
  - 161: glyphs PDFium reads as a control code with its map-error flag, where MuPDF reads U+FFFD.
  - 58: a verifier bug: object clips inside a scaled Form XObject read in the wrong space (VR17,
    fixed; 240 visible characters counted clipped on one page).
  - 14 each: glyphs the two engines decode differently (§ 2.4); the same character with boxes that
    disagree (§ 2.2).
  - 11: a diagonal watermark's ink inside table cells (§ 3.2).
  - 10: greedy ownership under overprinted titles (§ 2.3).
  - 9: math letters beyond U+FFFF, which PDFium reports as two surrogate code units (§ 1.2).
  - 8: ligatures (§ 2.1).
  - 6: value tokens PDFium runs together across a gap (§ 3.1).
  - 5: characters straddling the page edge that MuPDF keeps in a word (§ 2.2).
  - 4: glyph names MuPDF decodes and PDFium cannot (`⟲`, § 1.1).
  - 1: a FreeText annotation, whose appearance MuPDF reads and PDFium's text page does not (§ 5).
- **297 are inkgrid errors.** § 5 lists them.
- **26 are ambiguous page content:** Type 3 picture glyphs (17), an OCR text layer whose word boxes
  overlap by tens of points (5), a glyph whose name says `≏` and whose drawing is `∼` (4).
- **The crash:** Camelot returned a table whose rows hold no cells (CM11, fixed).

---

## 1 · Characters

### 1.1 Kinds

`char_kind` decides in this order (amending spec 10 § 1.1):

1. `generated` when `FPDFText_IsGenerated` is 1;
2. `hyphen` when `FPDFText_IsHyphen` is 1, or the code point is U+0002 **and** the map-error flag
   is 0 (a mapped glyph named `/difference` at code 2 came back U+0002 with the flag set);
3. `unmapped` when the map-error flag is 1 and the character is not U+0020 or U+00A0, or the code
   point is U+0000 or a C1 control (U+0080–U+009F). PDFium returns such codes for drawn glyphs its
   font cannot map (U+001F with the flag for a ligature; U+0083 and U+0099 for Wingdings bullets;
   U+0092, which is cp1252's `’`, from a broken ToUnicode). The test comes before the space test,
   because Python's `isspace` counts U+001C–U+001F as whitespace. A C0 control without the flag
   (U+0007) stays invisible, as the reader counts it (`02-reader.md` W-9);
4. `space`, `invisible`, `unmapped` (U+FFFD, a lone surrogate), `ink`, as before.

An unmapped character still pairs with any one character of the word that owns it (spec 10 § 3.1),
counted in `unmapped_chars`: neither engine's reading is confirmed there, and the report says so.

### 1.2 Surrogate pairs

PDFium reports a character beyond U+FFFF (`𝑑`, U+1D451) as two consecutive characters holding a
high and a low surrogate. The reader joins such a pair into one `InkChar`: the combined code point,
the union of the two boxes, and the first index. A surrogate without its partner stays U+FFFD
(`unmapped`).

| Case | Input | Expected |
|---|---|---|
| CK1 | kinds: U+001F and U+001C with the map error; U+0083; U+0092; U+0000; `A` with the map error | unmapped, each |
| CK2 | U+0020 with the map error; tab; U+001C and U+0007 without it; U+0002 with it; U+0002 without it | space; space; space; invisible; unmapped; hyphen |
| CK3 | the code units U+D835, U+DC51 at indexes 4 and 5 | one ink character `𝑑` at index 4, boxes united |
| CK4 | U+D835 followed by `A` | U+FFFD (unmapped), then `A` |

---

## 2 · Ownership

### 2.1 Ligatures

After exact pairs (spec 10 § 3.1 step 1), a word's remaining characters that spell a standard
ligature, `ffi`, `ffl`, `ff`, `fi`, `fl`, or `st` (longest first, and only where the word's text
holds the sequence), pair with one remaining ink character of the word that is unmapped, or that is
the ligature's own code point (U+FB00–U+FB06, compared by its NFKC decomposition). The pair counts
in `PageCheck.ligature_chars` (the ink characters, one per ligature). MuPDF expands a ligature
glyph into its letters (`02-reader.md` § 3), and PDFium reads it as one character.

### 2.2 Second-chance pairing

An ink character that no word contains is offered, before § 3.2's classes of spec 10:

- **at the page edge:** a character outside the frame goes to a word whose box contains its
  centre. MuPDF keeps a glyph straddling the page edge in its word (`zy`, whose box reaches past
  x 612), and the reader's `clipped_chars` counts only the characters it drops;
- **by overlap:** a character goes to a word whose box its own box overlaps and that still needs that
  exact character. The two engines' boxes for one glyph can disagree: MuPDF's box for a `−` was 1.6
  pt wide, PDFium's 4.6, and its centre fell outside the word.

A clipped character is still never offered (spec 10 § 2).

### 2.3 Repair

Pass 2's choice can be undone. When a word lacks a character `c` after pairing, and a character `c`
it contains went to another word that holds more `c` than it needs, the character moves to the
word that lacks it. The step repeats until nothing moves. Under `EXECUTIVE SUMMARY`, overprinted
by a banner and overlapping `APPENDIX A`, pass 2 gave EXECUTIVE's last `E` to APPENDIX, which then
left APPENDIX's own `E` lost.

### 2.4 Decode disagreements

A word left with `k` unpaired word characters and `k` unpaired ink characters, none of them
unmapped, has glyphs the two engines decode differently: MuPDF reads `•` where PDFium reads `ï`
(a bullet with no ToUnicode entry), or `G` where PDFium reads `●` (a Dingbats name MuPDF misreads).
The verifier cannot tell which engine is right, so the word gets one **DECODE** defect, holding the
word's characters and quoting both readings, instead of a LOST and an INVENTED. The ink characters
count as owned.

| Case | Input | Expected |
|---|---|---|
| OW6 | the word `Confirmed` over ink `Con`, an unmapped glyph, `rmed` | no defect; `ligature_chars` 1 |
| OW7 | the word `office` over ink `o`, U+FB03, `ce` | no defect; `ligature_chars` 1 |
| OW8 | the word `abc` over ink `a` and one unmapped glyph | INVENTED `c`: `bc` is no ligature, so the glyph pairs with one character |
| OW9 | the word `zy` whose box reaches past the page's right edge, over ink `z` inside and `y` centred outside | no defect; `outside_chars` 0 |
| OW10 | the word `5−3` with the `−` ink centred 0.5 pt left of the word's box, boxes overlapping | no defect |
| OW11 | `EXECUTIVE` and `APPENDIX` with overlapping boxes, at us-020's measured positions | no defect |
| OW12 | the word `•x` over ink `ïx` | one DECODE defect, text `•`, quoting `ï`; no LOST, no INVENTED |
| OW13 | the word `ab` over ink `cd`; the word `ab` over ink `c` | one DECODE defect; LOST `c` and INVENTED `ab` (not one for one) |

---

## 3 · Table and value checks

### 3.1 Value tokens

A token also ends where PDFium's order jumps: when the next ink character's box starts more than
half its height to the right of the previous one's end, lies to its left, or its centre is more
than half its height above or below. PDFium emits no separator between far-apart characters
(eu-029's column numbers `1 2 3 4 5 6 7`, 57 pt apart, came back `1234567`).

### 3.2 Overlays

Ink inside a cell rectangle owned by a word of another block is foreign ink (spec 10 § 4.3), unless
that word is neither horizontal nor the table's own orientation: a diagonal watermark (`ARTICLE IN
PRESS` at 45°) crossing a table is an overlay. Its characters count in `PageCheck.overlay_chars`
and are not a TEXT defect. The exemption applies to tables in frame 0, whose words are horizontal;
a table read in a turned frame keeps the strict rule.

| Case | Input | Expected |
|---|---|---|
| VF5 | the tokens `1` and `2` in two cells 57 pt apart with no separator between them | no VALUE |
| VF6 | `12` glued, 1 pt apart, in two cells | VALUE |
| TB16 | a non-horizontal paragraph word's ink in a frame-0 cell | no defect; `overlay_chars` = its characters in the cell |
| TB17 | the same in a frame-90 table | TEXT |

---

## 4 · The report

- `DefectCode.DECODE`, between INVENTED and VALUE in report order, names its block.
- `PageCheck.ligature_chars` and `overlay_chars`, non-negative, 0 on declared and unverified pages.
- The schema is exported again (`docs/schema/verification.schema.json`).

| Case | Input | Expected |
|---|---|---|
| RP7 | a DECODE defect with no block; with no text | invalid; invalid |
| RP8 | an unverified page with `ligature_chars` 1 | invalid |

---

## 5 · What stays reported

These defects are inkgrid's, and are the benchmark's to measure. Each class is fixed after M5b
records the baseline, with a failing test first:

| Class | Defects | Where |
|---|---|---|
| Table extent overreaches: a grid over a page frame, a page-scale rule, a heading, or a second table | 114 | practice us-021, us-022; olmOCR 1529b2, c45171, b8d3ad, 2d0e05; competition us-036 |
| Identical overprinted text read twice (fake bold, a banner painted twice, stroke then fill) | 47 | competition us-020, us-021; olmOCR f86995, c8cdd4 |
| Control-code glyphs dropped as invisible (Type 3 subscripts `t₁`, `t₂`) | 45 | olmOCR e247cacc |
| A drawn rule the grid misses (2.75 pt grey rules; a corridor across a rule) | 32 | practice us-008, us-012; olmOCR 008d1d |
| Furniture taken from inside a table | 27 | competition eu-001, us-007, us-017; practice us-006 |
| A chart read as a table | 17 | competition eu-012, eu-027, us-028, us-001; practice eu-018; olmOCR 2ad3ea, 83b820 |
| MuPDF decodes a Dingbats name or a raw code as a letter | 10 | olmOCR 529eeb, 4fafd7 (now DECODE) |
| A diagonal watermark bound into cells | 3 | olmOCR 1ec1f9 |
| A mark split from its value into a footnote | 1 | olmOCR 2d54e9 |
| A CropBox beyond the MediaBox taken as the page size | 1 | olmOCR 30c92c |
| A FreeText annotation's text, which the verifier cannot see (engine difference, not fixed here) | 1 | competition us-001 |

The ambiguous classes (26, § 0) stay reported as they are.

---

## 6 · Acceptance

- [ ] Every case above has a test named `test_<CaseId>_<slug>`, and it failed before its code.
- [ ] Re-verified, one document at a time: every defect on the three corpora is in § 5's classes, in
      § 0's ambiguous classes, or a DECODE; none is an engine difference § 1–3 name.
- [ ] Every `OPENABLE` fixture still verifies with no defect; the 42 fee schedules still report
      the same 8 cells (spec 10 § 0) and nothing else.
