# 10 · Verify (M4)

**Implements:** `00-design.md` § 10 (verification), § 5.3 (pypdfium2), § 7 (`inkgrid.verify`,
`inkgrid verify`), lesson L15, risk 5 (visibility rules), and the M4 exit criteria: zero defects on
the fixture suite, and the look-back corpus runs and reports.
**Modules:**
- `verify/ink.py` (new, pure): the verifier's page model: characters, rules, pages;
- `verify/rules.py` (new, pure): rules from path geometry, with the verifier's own thresholds (§ 1.4);
- `verify/pdfium_reader.py` (new, the only module that imports pypdfium2): a PDF into ink (§ 1);
- `verify/ownership.py` (new, pure): every character to one word, and the word comparison (§§ 2–3);
- `verify/checks.py` (new, pure): the table checks and value fidelity (§§ 4–5);
- `verify/report.py` (new, pure): the checks assembled into the report (§ 6);
- `model/verification.py` (new): the typed report, `inkgrid.verification/1` (§ 6);
- `api.py`: `inkgrid.verify`; `cli.py`: `inkgrid verify`; `render/inspector.py`: defect overlays.

**The report lives in `model`, not `verify`.** The inspector (`render`) draws defects, and `render`
may import only `model` and `read`. A typed report in `model` keeps the layer table as it is.

---

## 0 · What was measured first (L19)

A prototype verifier ran over every fixture in `pdf_factory.OPENABLE` and over the 42 fee schedules
of the look-back corpus (974 pages) on 2026-09-28, one process at a time.

- **The engines agree on the text layer.** Once the four disagreements below were named, every one
  of the 1,817,075 ink characters PDFium reads on the corpus's pages went to an inkgrid word holding
  it: no lost, invented, or doubled character in 974 pages.
  - **Line-end hyphens.** PDFium reports a hyphen that ends a line as U+0002, with
    `FPDFText_IsHyphen` set. The corpus has 653, each a word short of its `-` (`Non-` against
    `Non`) until it was mapped back.
  - **Glyph boxes.** PDFium's tight box hugs the glyph's ink, so a period sits near the baseline. A
    corridor row band ends above its words' bottom edge, and 13 characters, 11 of them periods and
    commas, fell into a different cell than their word (`$0.45` read as `$045`). PDFium's loose box
    is the font's box, the same box MuPDF builds words from: `$0.45` has loose boxes spanning
    exactly its MuPDF word box (323.76–346.40 × 283.93–293.98). The verifier places characters by
    their loose-box centre.
  - **Overprinted text.** Three documents' cover pages print `Fee Schedule` over `User Manual`, and
    the word boxes overlap. Nearest-centre assignment gave the `e`s of `Fee` to `User`. Assignment first gives
    each unambiguous character to its word, then gives a contested character to the word still
    missing it (§ 2).
  - **Unmapped glyphs.** MuPDF reads a glyph with no Unicode as U+FFFD (`02-reader.md` § 3); PDFium
    guesses from the character code (`ABC` for `��C`), or returns a lone surrogate. Either side's
    unmapped character matches any one character on the other side.
- **Visibility (risk 5).** PDFium's text page holds characters that MuPDF drops: the 7 characters of
  `clipped_text` hidden by a clip path, and the 18 of `outside_crop` beyond the CropBox. The
  verifier's own geometry classifies both, and its count agrees with the reader's `clipped_chars`
  on every fixture and corpus page. **Invisible counts do not agree:** PDFium drops the U+200B and
  U+F020 that the reader counts as invisible (10 on one page). The two engines agree that
  those characters are not ink, so LOST is net of them by definition, and the counts are not
  compared.
- **Table checks.** No ORPHAN, DOUBLE, VRULE, or HRULE on the corpus once rules were merged and a
  crossing rule had to span its cell (§ 4.4). The first version flagged 21 VRULE cells in Cboe's
  schedule, where a rule of the next row reached into the cell's loose boxes, and 15 HRULE cells,
  among them underlines and `≥` signs drawn as `>` over a short rule. A plain comparison of each
  cell's characters with the ink in its rectangle fails on 66 cells; the rules of § 4.3 leave 7:
  - 84 characters belong to words that overflow their cell into a neighbour, the word's own cell
    holding most of it (`OR,` with its comma past the edge, `Re|moved`). Their binding is right; the
    report counts them as overflow;
  - 7 cells are real disagreements. Six are words split exactly in half: `Trade-by-Trade` 7/14 in
    three documents, and `Charge` 3/6 three times in `Remove Charge & Fee Code`, one ruled cell on
    the page that the grid cuts at column rules other rows draw. One is
    `$0.00061/share**$0.00061/share***`, two values from two columns that MuPDF read as one word.
- **Value fidelity.** 35,302 value tokens. One is bound to two cells: `charges⁵`, whose note mark
  the grid put in the next column of a row where no rule divides the columns.
- **Known miss.** JSE's tiers 5 and 6 share one grid row (`R50bn - R100bn R100bn - R999bn`, `0.44
  0.39`). No rule separates the tiers on the page: the one thin rectangle between them is a white
  fill under one column. The verifier checks the output against the page's ink and drawn rules; a
  merge with no drawn rule is for M5's binding metric.
- **Speed.** The prototype took 105 s for 974 pages; its ownership was quadratic, and Cboe's 24
  pages took 15.6 s. The implementation indexes words and cells by 20 pt band.

**The implementation, on the same 42 documents** (2026-09-28, one at a time): all 974 pages verified;
all 1,817,075 ink characters owned; the same 7 TEXT defects and 1 VALUE defect as above, 84
overflow characters, and 2 ORDER advisories (Cboe's `Penny Classes` over `Non-Penny Classes`, and
`BBO` stacked over `Maker`); 52 s in all, 0.05 s per page, and Cboe's 24 pages in 4.8 s.

---

## 1 · The verifier's reading

`read_ink(data, password) -> Ink` opens the PDF with PDFium and returns one `InkPage` per page
PDFium counts. It never imports the reader or the core. Everything past it is pure.

### 1.1 Characters

Each character of `FPDFText_LoadPage` becomes an `InkChar(index, char, box, kind, clipped)`:

- `index` is PDFium's character index; `box` is `FPDFText_GetLooseCharBox`, in the frame (§ 1.2);
- `kind` is decided in this order:
  1. `generated` when `FPDFText_IsGenerated` is 1: PDFium's own spaces and line breaks;
  2. `hyphen`, char `-`, when `FPDFText_IsHyphen` is 1 or the code point is U+0002: a hyphen that
     ends a line. PDFium reports a hard `-` and a soft hyphen (U+00AD) there alike, while MuPDF
     keeps the first and counts the second as invisible (measured: `hard-` against `soft`);
  3. `space` for whitespace (`str.isspace`);
  4. `invisible` for categories Cc, Cf, Co, and Cn: never a word character (`02-reader.md` § 4);
  5. `unmapped` for U+FFFD, a lone surrogate (Cs), or `FPDFText_HasUnicodeMapError` = 1. A lone
     surrogate reads as U+FFFD: it is not text, and a report holding one could not be written as
     JSON;
  6. `ink` otherwise.

Characters of kind `ink`, `hyphen`, and `unmapped` are **ink**: what a word could hold. The rest
are not.

### 1.2 The frame

A page's frame is PDFium's page box (`FPDF_GetPageBoundingBox`: the CropBox clipped to the
MediaBox), unrotated, with y growing down: `(x - box.x0, box.y1 - y)`. This is the frame of
`PageInfo` and every `Rect` in a document. A page whose frame size differs from the document's
`PageInfo` by more than `FRAME_TOL = 0.5` pt in width or height is not compared (§ 3.4).

### 1.3 Visibility

- **Outside:** the character's centre is outside the frame: `x < 0`, `x >= width`, `y < 0`, or
  `y >= height`.
- **Clipped:** the character's text object has a clip path (`FPDFPageObj_GetClipPath`), and the
  character's centre lies outside at least one of its paths. A path is the polygon through its
  segment points; inside is the even-odd crossing test.

A character's *centre* is its loose box's centre, everywhere in this spec.

### 1.4 Rules

Path objects are read with their matrices applied: the object's matrix, then each enclosing Form
XObject's matrix, outermost last (`FPDFFormObj_GetObject`). A path is:

- **stroked** when its draw mode strokes and its stroke alpha is above 0;
- **filled** when its fill mode is not 0 and its fill alpha is above 0.

`extract_rules(paths) -> tuple[InkRule, ...]` (`InkRule(axis, at, start, end)`, in the frame). The
thresholds differ from the reader's (`02-reader.md` § 5) on purpose, so agreement is evidence:

| | reader | verifier |
|---|---|---|
| slant allowed along the axis | 0.5 | `SLANT_MAX = 1.0` |
| shortest rule | 2.0 | `MIN_LENGTH = 3.0` |
| thickest filled rule | 2.5 | `THIN_MAX = 3.0` |

- A stroked path gives a rule for each straight segment between consecutive points (a Bézier
  segment breaks the run; the closing segment of a closed subpath counts) with `|dy| <= 1.0` and
  `|dx| >= 3.0` (an `h` rule at the mean y), or the same with the axes exchanged (a `v` rule).
- A filled path gives a rule for each subpath of at least 4 points (a fill closes every subpath)
  whose box is at most 3.0 on its thin side and at least 3.0 on its long side, along the long side,
  at the middle. A wider filled box is shading.
- **Merging:** rules on one axis whose `at` values lie within `MERGE_AT = 0.5` of the group's first
  (by `at`) form a group. Within a group, spans that overlap or come within `MERGE_GAP = 1.0` of
  each other merge into one rule at the group's first `at`. A table drawn cell by cell, with one
  rectangle per cell edge, becomes whole rules.

### 1.5 Pages PDFium cannot load

A page PDFium cannot load becomes `InkPage(number, error=<PDFium's message>)` with no characters and
no rules. A password PDFium refuses raises `PasswordRequired` when none was given and
`WrongPassword` otherwise (`inkgrid.errors`, which every layer may import). A PDF PDFium cannot open
for any other reason gives `Ink(pages=(), error=<PDFium's message>)`.

| Case | Input | Expected |
|---|---|---|
| VR1 | `simple_text` | every ink character's centre lies in the box of a word the reader read |
| VR2 | `offset_mediabox`; `cropbox` | as VR1: the frame's origin is the page box's corner |
| VR3 | `rotated`; `landscape` | as VR1: the frame is unrotated |
| VR4 | kinds: a generated space; U+0002; `IsHyphen` on `-`; U+0020; U+00A0 | generated; hyphen `-`; hyphen `-`; space; space |
| VR5 | kinds: U+200B, U+00AD, U+E000, U+0007; U+FFFD, U+D800, a map error on `A`; `A` | invisible; unmapped (U+D800 as U+FFFD); ink |
| VR6 | `clipped_text` | the 7 characters of `clipped` are clipped; `inside` is not |
| VR7 | `outside_crop` | 18 ink characters are outside the frame |
| VR8 | `ruled_grid` | every reader rule lies on a verifier rule: same axis, `at` within 1.0, and its extent covered within 1.0 |
| VR9 | stroked segments: slant 0.9 and 1.1 over 20; length 2.9 and 3.0 | a rule; none; none; a rule |
| VR10 | filled closed boxes 3.0 × 40 and 3.1 × 40; a stroked 40 × 20 box; alpha 0; a Bézier | a rule; none; 4 rules; none; none |
| VR11 | collinear segments with a gap of 0.8 and 1.2; with `at` 0.4 and 0.6 apart | one rule; two; one; two |
| VR12 | `formed_rules`: a ruled grid drawn in a Form XObject at half scale | as VR8 |
| VR13 | `ruled_encrypted("u")` with its password; with none; with a wrong one | pages; `PasswordRequired`; `WrongPassword` |
| VR15 | bytes that are not a PDF | `Ink` with an error and no pages |
| VR14 | `null_second_kid` | page 2 has an error and no characters |

---

## 2 · Ownership: every character to one word

`own_page(page, words, *, clipped_chars, invisible_chars) -> PageOwnership` assigns each ink
character of a page to at most one of the page's words. A character outside the frame or clipped
(§ 1.3) is not offered to any word: MuPDF never read it, and a clipped glyph under a visible word
would otherwise count against that word; § 3.2 classes it. A word *contains* a character when its box contains the character's centre, half-open:
`x0 <= x < x1` and `y0 <= y < y1` (L15). A box of zero width or height is closed on that axis
(`x0 <= x <= x1`), so a zero-width glyph's word still contains it.

1. **Pass 1:** a character contained by exactly one word goes to that word.
2. **Pass 2, in PDFium's order:** a character contained by several words goes to the one that still
   needs it: a word needs a character while it holds that character, or a U+FFFD, more times than
   it has been given; an unmapped character is needed by any word still short of characters. Ties go
   to the word whose vertical centre is nearest the character's, then the nearest horizontally, then
   the lowest id.
3. A character no word contains is **unowned**.

| Case | Input | Expected |
|---|---|---|
| OW1 | ink made from any built document's words (a property) | every ink character goes to the word it was made from |
| OW2 | a character centred exactly on `x1` of one word and `x0` of the next | the next word |
| OW3 | `Fee Schedule` over `User Manual`, boxes overlapping as measured | each word gets its own characters |
| OW4 | two words both needing a contested `e`, centres 2 and 1 from it vertically | the word 1 away |
| OW5 | a word of zero width and a character centred on its left edge | the word |

---

## 3 · Document checks

### 3.1 The word comparison

Each word's characters are compared with the ink it owns, as multisets:

1. an owned character equal to a word character pairs with it;
2. an unmapped owned character, or a word's U+FFFD, pairs with any remaining character on the
   other side (counted as `unmapped`);
3. a remaining owned character is **LOST**: ink the word's box holds but the word does not. A
   remaining `hyphen` is a **soft hyphen** instead (§ 3.2);
4. a remaining word character is **DOUBLED** when an ink character equal to it, contained by this
   word, went to another word; otherwise it is **INVENTED**: text that is not on the page.

### 3.2 Unowned characters

- **outside** or **clipped** (§ 1.3): benign, the reader's `clipped_text`. The class is accepted
  while the page's outside and clipped characters number at most its `clipped_chars`; beyond that,
  every one of them is LOST, since the reader stated a smaller count than the page shows.
- a `hyphen`: a **soft hyphen**, benign, which the reader counted as invisible. The class is accepted
  while the page's soft hyphens, unowned or left over in a word, number at most its
  `invisible_chars`; beyond that, every one of them is LOST.
- otherwise **LOST**.

LOST characters are reported as runs: LOST characters with no other ink character between them, in
PDFium's order, form one defect, whose text is the run's characters (so the texts add up to the
page's `lost_chars`), whose box is the union of their boxes, and whose detail quotes the run with
its spaces. DOUBLED and INVENTED characters
form one defect per word, whose text is the missing characters in word order and whose box is the
word's.

### 3.3 Declared pages

A page is **declared** when the document carries an `unreadable_page` finding for it, or when it is
beyond the document's pages and the document carries an `unreadable_page` finding with no page. The
reader already said it could not read the page (G4), so its ink is counted as `declared` and
nothing else about it is checked.

### 3.4 Unverified pages

A page the document read is **unverified**, with an UNVERIFIED defect, when PDFium does not count
it, cannot load it, or disagrees on its size (§ 1.2). A page PDFium counts beyond the document's
pages, and not declared, is checked as a page with no words: its ink is LOST. If PDFium cannot load
it either, it is unverified.

| Case | Input | Expected |
|---|---|---|
| DC1 | two adjacent stray ink characters `xy` no word contains | one LOST defect, text `xy` |
| DC2 | a stray `q` inside the box of the word `Fee` | LOST `q` |
| DC3 | the word `Fee` with no `F` in the ink | INVENTED `F` |
| DC4 | the word `Fee` twice, same box, over one `Fee` of ink | DOUBLED `Fee` on the second |
| DC5 | the word `�B` over ink `AB`; the word `AB` over ink `�B` (unmapped) | no defect; `unmapped` 1 each |
| DC6 | one stray character outside the frame; the page's `clipped_chars` 1, then 0 | outside 1; then LOST |
| DC7 | as DC6, clipped instead of outside | clipped 1; then LOST |
| DC13 | the word `soft` with a `hyphen` after it; the page's `invisible_chars` 1, then 0 | soft hyphen 1; then LOST |
| DC14 | the word `hard-` over ink `hard` and a `hyphen` | no defect |
| DC8 | a page with an `unreadable_page` finding and ink | status declared; its ink declared; no defect |
| DC9 | a document page PDFium cannot load; a page PDFium does not count | UNVERIFIED each |
| DC10 | an extra PDFium page with ink; the same with a pageless `unreadable_page` finding | LOST; declared |
| DC11 | a page whose frame is 1.0 pt narrower than its `PageInfo` | UNVERIFIED |
| DC12 | `nested_graphics_states`, `count_mismatch`, `null_second_kid` read and verified | declared ink; no defect |

---

## 4 · Table checks

Each table is checked on its page, in its grid's frame: a character's centre is turned into the
frame (`turn_rect` of its box, by `grid.frame`), and each cell's rectangle is `grid.cell_rect(cell)`.
A table on a declared or unverified page is not checked. The table's **extent** is the union of the
rectangles of its cells that are not carried.

### 4.1 ORPHAN and DOUBLE

- **ORPHAN:** an ink character inside the extent that no cell rectangle contains: it sits in a gap
  between bands. One defect per table, holding its orphans.
- **DOUBLE:** an ink character inside two cell rectangles. A valid `Grid` cannot produce one: its
  bands are sorted and never overlap, and its cells tile the positions. The check is a second
  statement of that invariant, tested on rectangles directly.

### 4.2 Placement

A character's **home** is the one cell rectangle containing it. A word of a cell is **placed** when
its cell is the home of strictly more than half of the characters it owns. The characters it owns
elsewhere are **overflow**: the word runs past its cell's edge, and its binding stands.

### 4.3 TEXT

A cell has a TEXT defect when:

- one of its words is not placed: most of its ink lies in another cell, or it is split exactly in
  half, so the page does not say which cell it belongs to; or
- its rectangle holds ink owned by a word that is not in this table (**foreign ink**). A carried
  cell owns no words, so any foreign ink in its rectangle is a defect.

Ink owned by a word of another cell of the same table is that cell's overflow, or that cell's
defect. Unowned ink is LOST (§ 3.2) and is not counted again.

### 4.4 VRULE and HRULE

A merged rule (§ 1.4), turned into the frame, **cuts** a cell when:

- it lies strictly inside the cell by more than `CROSS_MARGIN = 1.0` (a `v` rule's `at` between
  `x0 + 1.0` and `x1 - 1.0`);
- it spans the cell along its length within `EDGE = 2.0` of both edges (a `v` rule's `start` at most
  `y0 + 2.0` and its `end` at least `y1 - 2.0`);
- the cell's own characters (its words' characters whose home it is) lie on both sides of it.

A cut by a `v` rule is VRULE; by an `h` rule, HRULE: the cell merges ink the page divides. An
underline, or a `≥` drawn as `>` over a short rule, spans only part of the cell and cuts nothing.

### 4.5 ORDER (advisory)

A cell with no TEXT defect and no U+FFFD whose words' characters, in the verifier's reading
sequence, differ from its words' texts concatenated in order. It is an advisory, never a defect:
two labels stacked in one cell have no unambiguous order.

The **reading sequence** (L15): characters sorted by their centre's y; a character joins the current
line when its box overlaps the line's vertical extent by more than half the smaller height;
otherwise it starts a line. Lines are read top to bottom, and each left to right by `x0`, in the
frame.

| Case | Input | Expected |
|---|---|---|
| TB1 | ink made from any built table's words (a property) | no defect, no advisory |
| TB2 | a character in the gap between two row bands, inside the extent | ORPHAN |
| TB3 | two overlapping rectangles and a character in both (rectangle level) | DOUBLE |
| TB4 | the word `Rate`'s ink moved wholly into the next cell's rectangle | TEXT on `Rate`'s cell |
| TB5 | `Charge` with 4 of 6 characters in its cell and 2 past the edge | no defect; overflow 2 |
| TB6 | `Charge` with 3 of 6 characters on each side | TEXT |
| TB7 | a paragraph's ink inside a cell rectangle; the same in a carried cell's rectangle | TEXT; TEXT |
| TB8 | a cell whose words read `Maker BBO` while its ink reads `BBO Maker` | ORDER advisory; no defect |
| TB9 | a `v` rule through a cell's middle, spanning it, characters on both sides | VRULE |
| TB10 | as TB9, the rule spanning half the cell's height; the rule 0.8 inside the cell's edge | none; none |
| TB11 | an `h` rule spanning a cell with lines above and below; an underline under the first line | HRULE; none |
| TB12 | a table in frame 90 with ink made from its words; then TB4 in that frame | no defect; TEXT |

---

## 5 · Value fidelity

The verifier makes its own **tokens**: maximal runs of ink characters that are consecutive in
PDFium's order. Any character that is not ink (whitespace, generated, or invisible) ends a token.
A **value token** holds a decimal digit (category Nd). Every value token whose characters are all
owned must be bound to one block and, inside a table, to one cell: the owners of its characters must
belong to one block and one cell. A token bound to more than one is a VALUE defect: `$1.20` as `$1`
in one cell and `.20` in the next. Where a value token lies against cell rectangles is TEXT's
business; value fidelity checks the binding.

| Case | Input | Expected |
|---|---|---|
| VF1 | the token `1.20%` whose characters are owned by words of two cells | VALUE |
| VF2 | the token `27` whose characters are owned by words of two blocks | VALUE |
| VF3 | `Fees` (no digit); `12` with an unowned `2` | no VALUE; no VALUE (LOST reports it) |
| VF4 | `12` and `34` separated by a generated space, in two cells | no VALUE |

---

## 6 · The report (`inkgrid.verification/1`)

```python
class DefectCode(StrEnum):   # the closed set; ORDER is the only advisory
    LOST, DOUBLED, INVENTED, VALUE, ORPHAN, DOUBLE, TEXT, VRULE, HRULE, UNVERIFIED, ORDER

class Defect(Frozen):
    code: DefectCode
    page: PositiveInt
    block: BlockId | None = None      # every table code names its table
    cell: Anchor | None = None        # TEXT, VRULE, HRULE and ORDER name their cell
    text: str = ""                    # the characters concerned
    bbox: Rect | None = None          # where, in the page's unrotated frame
    detail: NonEmpty

class PageCheck(Frozen):
    number: PositiveInt
    status: Literal["verified", "declared", "unverified"]
    ink_chars, owned_chars, lost_chars, outside_chars, clipped_chars, soft_hyphens,
    unmapped_chars, declared_chars, overflow_chars, rules: NonNegativeInt

class Verifier(Frozen):
    inkgrid: str; pypdfium2: str; pdfium: str

class VerificationReport(Frozen):
    schema: Literal["inkgrid.verification/1"]
    source: Source                    # the document's
    verifier: Verifier
    pages: tuple[PageCheck, ...]      # 1..n, every page either engine counts
    defects: tuple[Defect, ...]       # by page, then code, then position
    advisories: tuple[Defect, ...]
    ok: bool                          # property: no defect
```

Its invariants are validators:

- a verified page's ink is fully accounted for: `ink = owned + lost + outside + clipped +
  soft_hyphens`, where `owned` counts the characters paired with a word character, and
  `declared = 0`; a declared page has `ink = declared` and nothing else; an unverified page has
  every count 0;
- a page's `lost_chars` equals the length of its LOST defects' text;
- `advisories` holds only ORDER, and `defects` never does;
- ORPHAN, DOUBLE, TEXT, VRULE, HRULE and ORDER name a block; TEXT, VRULE, HRULE and ORDER name a cell;
- every page named by a defect is in `pages`; UNVERIFIED is on, and only on, unverified pages.

| Case | Input | Expected |
|---|---|---|
| RP1 | a verified page with `ink` one more than its parts | invalid |
| RP2 | a LOST defect of 2 characters on a page with `lost_chars` 3 | invalid |
| RP3 | ORDER in `defects`; TEXT in `advisories` | invalid; invalid |
| RP4 | TEXT with no cell; ORPHAN with no block | invalid; invalid |
| RP5 | UNVERIFIED on a verified page; an unverified page without it | invalid; invalid |
| RP6 | any report from the fixture suite | round-trips through JSON; `docs/schema/verification.schema.json` is current |

---

## 7 · API and command line

`inkgrid.verify(doc, source, *, password=None) -> VerificationReport` reads `source` (a path,
bytes, or binary stream) with PDFium and grades `doc` against it. It never raises for a defect.

- `TypeError` when `doc` is not a `Document`;
- `SourceMismatch` when the PDF's SHA-256 is not `doc.source.sha256`: the boxes would be compared
  with the wrong pages. Like every inkgrid error it subclasses `InkgridError` and never `ValueError`
  (`03-cli-and-packaging.md` A3);
- `PdfOpenError`, `PasswordRequired`, `WrongPassword` as for `read`. A PDF PDFium cannot open for any
  other reason gives a report whose every document page is unverified.

`inkgrid verify in.pdf doc.json [-o report.json] [--pretty] [--inspector out.html]
[--password-stdin]` verifies the document `inkgrid read` wrote:

- prints the report as JSON (`-o` writes it to a file);
- exit **0** with no defect (advisories allowed); exit **1** with any defect, after one stderr line
  `inkgrid: verify: N defects: text 2, value 1` (codes in `DefectCode` order);
- exit **2**, one stderr line, when `doc.json` cannot be read or is not an `inkgrid.document/1`, when
  it was read from a different PDF, and for the input errors of `inkgrid read`;
- `--inspector` also writes the inspector with the report's overlays (§ 8).

| Case | Input | Expected |
|---|---|---|
| VA1 | every fixture of `OPENABLE`, read then verified (the M4 exit) | no defect |
| VA2 | a document verified against another fixture's PDF | `SourceMismatch` naming both hashes |
| VA3 | `verify("doc", pdf)` | `TypeError` |
| VA4 | `ruled_encrypted("u")`: its password; none; a wrong one | a report; `PasswordRequired`; `WrongPassword` |
| VA5 | `table_between_paragraphs`' document with its last paragraph removed (the composed flow) | LOST, the paragraph's text, on its page |
| VC1 | `inkgrid verify` on `ruled_grid` and its document | exit 0; stdout is a report with `ok` |
| VC2 | VA5's document | exit 1; stderr `inkgrid: verify: 1 defect: lost 1` |
| VC3 | `doc.json` that is not JSON; valid JSON that is not a document; a missing file | exit 2, one line each |
| VC4 | VA2 through the command line | exit 2 |
| VC5 | `-o r.json --pretty --inspector i.html` | `r.json` indented; `i.html` has the overlays |

---

## 8 · Inspector overlays

`inspector_html(doc, pages_png, report=None)` and `build_inspector(doc, source, password=None,
report=None)`:

- each defect with a box draws `<rect class="defect d-<code>">` over its page, labelled with its
  code; an advisory draws `class="advisory"`;
- the page's column lists its defects and advisories (code, block, cell, and detail), and states an
  unverified or declared page;
- the header states `verified: N defects, M advisories`; with no report, the page is exactly as
  before;
- a report whose `source.sha256` is not the document's raises `ValueError`.

| Case | Input | Expected |
|---|---|---|
| VI1 | a report with one TEXT defect on page 1 | a `d-text` rect on page 1; the detail in page 1's column |
| VI2 | no report | no defect markup, style, or summary: the page is as before |
| VI3 | a report of another document | `ValueError` |
| VI4 | a defect whose detail holds `<b>` | escaped |

---

## 9 · Acceptance

- [ ] Every case above has a test named `test_<CaseId>_<slug>`, and it failed before its code.
- [ ] `pypdfium2` is a direct dependency; only `verify/pdfium_reader.py` imports it (a new
      architecture case); its stubs are in `typings/pypdfium2/`.
- [ ] Every `OPENABLE` fixture verifies with no defect (VA1).
- [ ] The 42 fee schedules verify one at a time, and the result is recorded in § 0's form.
- [ ] `docs/schema/verification.schema.json` is exported; README, ARCHITECTURE and CHANGELOG
      describe `verify`.
