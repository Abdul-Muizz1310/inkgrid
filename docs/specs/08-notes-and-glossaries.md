# 08 · Note lists and glossaries (M2c)

**Implements:** `00-design.md` § 4.3 stage 3 ("a two-column grid of (number, prose) is a note list … of
(short term, prose) a glossary") and stage 4 ("definition: a hanging-indent glossary entry"), and the
deferral in `04-text-pipeline.md` § 5 ("Definitions from hanging-indent glossaries arrive in M2 together
with glossary grids, because both share the term-and-body test"). It closes M2 with the exit criterion's
ICDAR-2013 smoke run (§ 0).

**Modules:**
- `core/glossary.py` (new, pure): definition scopes, terms in prose, and grids that dissolve into notes and
  definitions;
- `core/lexicon.py`: the definitions vocabulary and the defining verbs;
- `core/prose.py`: `ProtoBlock` gains the `definition` kind, carrying its term's lines;
- `core/assemble.py`: `Definition` blocks;
- `core/pipeline.py`: the glossary pass, over the whole document, between prose and assembly.

---

## 0 · What was measured first (L19)

A sketch of these rules ran over the 42 fee schedules on 2026-09-27.

- **Definitions live in sections.** 20 of the 42 documents have one, under a heading such as
  `Definitions`, `2 Definitions`, `4.2.1.1 DEFINITIONS`, `Market Data Definitions`, or
  `I. Definitions (applicable for purposes of fees and credits):`. Their entries come in three forms:
  - a **quoted term** opening a paragraph (US exchanges): `“ABBO” means the best bid(s) …`, with alternates
    (`“Electronic Exchange Member” or “EEM” means …`) or a parenthetical (`“Dedicated” (cross-connect)
    means …`). The sketch read 194;
  - a **bold term** (Euronext `Available for Distribution: Instruments that …`; `Distributor. Any entity …`):
    34;
  - a **hanging term** in a column of its own, the body in a second column (SIX's `Access | Connection of
    physical data line …`, set between horizontal rules): 47. Neither gridder takes these rows: they have
    no vertical rules and no values. Prose today runs each term into its body.
- **Outside those sections**, 8 paragraphs open with a quoted term followed by a defining verb (`“SMQ Payout”
  shall mean …`, `“TCADV” refers to …`). A quoted opening without such a verb outside a section is not
  evidence of a definition.
- **Numbered definitions** (`1. “CADV” means …`, 39) are list items and stay list items: their numbering
  is part of the document.
- **A plain `Term:` opening is not a term.** The sketch's one hit inside a section was a sentence
  (`2 These transaction fees do not apply to:`). The colon counts only when the term is bold.
- **Grids.** No two-column grid holds numbered notes. One ruled grid (Deutsche Börse) under a `Legend`
  banner holds five terms (`Tier A | Metro areas of Amsterdam, …`) and four notes labelled `X1`–`X4`, the
  superscript marks its tables use (`EMDI^X2`). The other nine two-column grids of short text beside prose
  are fee tables (`Tier 1 | Participant adds …`, `Sales Value Fee | Per Executed Sell Contract …`): a grid
  is a glossary only in a definitions context, or those tables would be lost.
- **The ICDAR-2013 smoke run (M2's exit criterion).** All 67 competition documents read into valid
  documents with `combined` and with `vector`; the scores are in
  `knowledge/research/RR-0016-lattice-engines-end-to-end.md`.

---

## 1 · Definition scopes

- A **heading** opens a scope when its text, without a leading section number (`2`, `4.2.1.1`, `A.`,
  `I.`), has at most 8 words, one of them a definitions word, and no dot leader (`..`, a contents line).
  The **definitions words** (`core/lexicon.py`): `definition`, `definitions`, `glossary`, `legend`,
  `interpretation`, `interpretations`, `abbreviation`, `abbreviations`, and the phrase `defined terms`;
  matched case-insensitively against whole words, ignoring trailing `:`.
- The scope holds the blocks after it, across pages, up to the next heading whose level is the same or
  higher (a level number at most its own). A sub-heading inside it (a larger level number) keeps the scope.
- A **table** opens a scope over its own rows when its first row is a banner (one cell spanning every
  column) whose text passes the heading test.

| # | case | expected |
|---|---|---|
| SC1 | heading `Definitions`, a `“Fee” means …` paragraph, then a heading of the same size, then `“Fee” applies to …` | a definition, then a heading, then a paragraph |
| SC2 | `2 Definitions` (level 2), a level-3 sub-heading, a `“Fee” applies to …` paragraph, then a level-2 heading and another | a definition inside the sub-heading; a paragraph after the level-2 heading |
| SC3 | a contents line `Definitions ........ 4` as a heading, then `“Fee” applies to …` | a paragraph |
| SC4 | a heading of nine words that mentions `definitions` | no scope |
| SC5 | a scope opened on page 1, entries on page 2 | the page-2 entries are definitions |
| SC6 | `4.2.1.1 DEFINITIONS`; `I. Definitions (applicable for purposes of fees):`; `Legend` | each opens a scope |

---

## 2 · Terms in prose

A **paragraph** becomes a definition when it opens with a term, by the first of these forms that applies,
and at least one word follows the term. Headings, list items, and footnotes are never re-typed.

1. **Quoted.** The first word opens with a quotation mark (`“ " ‘ '`). The term runs to the first word
   whose text, without trailing `.,:;`, ends with a closing mark (`” " ’ '`), at most 12 words in; then
   through `or`, `and`, or `/` followed by another quoted phrase, as often as they chain; then through one
   parenthetical of at most 6 words (`(cross-connect)`, `(“MEI”)`). Inside a scope, any quoted opening is a
   term. Outside one, only when the body opens with a **defining verb** (`core/lexicon.py`): `means`,
   `mean`, `shall mean`, `refers to`, `refer to`, `is defined`, `are defined`, `has the meaning`, `have the
   meaning`, `shall have the meaning`.
2. **Bold or italic** (inside a scope). The first line opens with 1 to 12 bold words, or 1 to 12 italic
   words, and holds a word that is not bold (or not italic) after them. The term is those words
   (`Available for Distribution:`, `Distributor.`). MIAX sets its market data definitions' terms in
   italic.
3. **Hanging** (inside a scope). The first line's first fragment holds 1 to 8 words and is followed by a
   gap of at least 2 em (of the line's size) to the next word, and every later line of the paragraph
   starts within 2 pt of that next word's x: the body's column. The term is the first fragment. A term
   that is a single note label (`1`, `(a)`, `*`) is a note's number, not a term, and the paragraph stays.

The term is its words' rendered text; the body is the rest of the paragraph's.

| # | case | expected |
|---|---|---|
| DF1 | in a scope: `“ABBO” means the best bid(s) or offer(s) …` | term `“ABBO”`, body `means the best bid(s) …` |
| DF2 | `“Electronic Exchange Member” or “EEM” means the holder …` | term `“Electronic Exchange Member” or “EEM”` |
| DF3 | `“Dedicated” (cross-connect) means cross-connect that …` | term `“Dedicated” (cross-connect)` |
| DF4 | outside a scope: `“SMQ Payout” shall mean …`; `“Purge Ports” provide …` | a definition; a paragraph |
| DF5 | in a scope: bold `Available for Distribution:`, then regular `Instruments that can be offered …` | term `Available for Distribution:` |
| DF6 | in a scope: a paragraph bold throughout | a paragraph |
| DF7 | in a scope: `Access` at x 57, `Connection of physical data line …` at x 190, its second line at x 190 | term `Access`, body from `Connection` |
| DF8 | the same, with the second line at x 57 | a paragraph |
| DF9 | in a scope: `1` at x 57, `Trade activity on days when …` at x 100, its second line at x 100 | a paragraph |
| DF10 | in a scope: a list item `1. “CADV” means …` | a list item |
| DF11 | in a scope: `2 These transaction fees do not apply to:` (regular), then more words | a paragraph |
| DF12 | in a scope: `“Fee is charged per trade and more words than twelve without a closing quote …` | a paragraph |
| DF13 | a quoted term with nothing after it: `“ABBO”` | a paragraph |
| DF14 | `Document.to_markdown()` of DF1's definition | `**“ABBO”** means the best bid(s) …` |
| DF15 | in a scope: `Access`, then its body 1.5 em after it, the second line in the body's column | a paragraph |
| DF16 | in a scope: `“Fee” or charges apply to all trades` | term `“Fee”`, body `or charges apply …` |
| DF17 | in a scope: `“Fee” (as charged per trade …` with no closing parenthesis within 6 words | term `“Fee”` |
| DF18 | in a scope: italic `Distributor.`, then regular `Any entity that receives …`; outside a scope | term `Distributor.`; a paragraph |

---

## 3 · Grids that are note lists or glossaries

A table **dissolves** into blocks when it has exactly 2 columns and each of its rows is one of:

- a **banner** row, one cell spanning both columns and holding no more words than a heading may
  (`heading_max_words`): a heading block with its text;
- a **note** row: the first cell is one word, either a `note_label` (`1`, `(3)`, `*`) or a word that some
  superscript word of the document spells (`X2`, where a table prints `EMDI^X2`), that keeps some text
  without `().` (a mark `)` labels nothing), and the second cell is prose: a footnote block labelled
  with that word;
- a **term** row, only in a definitions scope (§ 1): the first cell holds at most 8 words and no value, and
  the second cell is prose: a definition block, whose term is the first cell and whose body is the second.

A row without words is passed over, and at least one note or term row must remain. A cell spanning
rows keeps the table whole. A cell is **prose** when it holds at least 3 words, is not a value, and its first word is not a strong value
(`€1.20 per contract` is a fee, not prose). Any other row keeps the table whole: a fee table like
`Tier 1 | Participant adds …` outside a scope stays a table. The blocks take the table's place in reading
order, row by row, and each owns its row's words, so no word changes stage (the table stage claimed them).

| # | case | expected |
|---|---|---|
| NL1 | a ruled grid: banner `Legend`, `Tier A \| Metro areas of Amsterdam …`, `X2 \| Connection rebate: the monthly fees …`, on a page whose table prints `EMDI` with a superscript `X2` | a heading `Legend`, a definition `Tier A`, a footnote `X2`, in that order; no table |
| NL2 | a ruled grid under a `Definitions` heading: `Access \| Connection of physical data line …`, `bp \| Basis points (1/100th of a percentage point).` | two definitions |
| NL3 | NL2's grid with no heading | a table |
| NL4 | a ruled grid outside a scope: `1 \| Applies to members trading …`, `2 \| Excludes orders routed …` | two footnotes, labelled `1` and `2` |
| NL5 | NL2's grid with a row `Monthly fee \| CHF 250` | a table |
| NL6 | a three-column grid under a `Definitions` heading | a table |
| NL7 | `X2 \| Connection rebate: …` rows outside a scope, and no superscript `X2` in the document | a table |
| NL8 | a note row whose second cell is `$0.25 per contract` | a table |
| NL9 | NL1's page read end to end | a valid `Document`: every word in exactly one block |
| NL10 | a grid whose full-width first row holds 16 words, then note rows | a table |
| NL11 | note rows `1` and `2` with an empty row between them | two footnotes |
| NL12 | a first cell `)` that a superscript `)` spells, beside prose | a table |
| NL13 | a note row `1 \| Applies to …`, then a row `2 \|` whose second cell is empty | a table |

---

## 4 · Blocks

- A **definition's** `term` is the rendered text of its term words, `body` of the rest, and `text` is
  `term + " " + body` (`01-model.md` 8c). Its words run term first; its hyphen joins are the term's and
  the body's.
- A note row's **footnote** has `label` = its label word without `().` (8b). A banner's **heading** takes
  its level from its size, as every heading does.
- `Document.to_markdown()` already renders a definition as `**term** body` (`05` § 2).

---

## 5 · Pipeline

After prose has built every page's blocks, the glossary pass walks the document in reading order,
tables among blocks, tracking the scope. It re-types paragraphs (§ 2) and dissolves tables (§ 3), and
returns each page's blocks and tables. Assembly then numbers the blocks and proves the partition as before.

| # | case | expected |
|---|---|---|
| GP1 | `definitions_section`: a `Definitions` heading; quoted, bold, and hanging entries; a ruled grid of two terms beside prose; then `Fees` and a quoted paragraph, read end to end | five definitions in reading order, the grid's in its place; a heading; a paragraph |
| GP2 | `definitions_section` and `legend_grid`, which join `OPENABLE` (so RD1 and CP5 read them with every fixture) | a valid `Document` that survives a JSON round trip |

---

## 6 · Acceptance

- [ ] SC1–SC6, DF1–DF18, NL1–NL13, and GP1–GP2 pass.
- [ ] The seven fee schedules read without error, and the sketch's definitions (§ 0) come out as
      definition blocks: SIX's glossary, Euronext's bold terms, and the US exchanges' quoted terms.
- [ ] Every M0, M1, M2a, and M2b case still passes.
