# 16 · The held-out fee set and the glyph-verified sample (M5d-2)

**Implements:** `00-design.md` § 11.2's domain set (fee schedules the library was never tuned on,
published as URL, SHA-256, and hand-verified ground truth) and its cell character error rate on a
human glyph-verified sample, scored for every tool of specs 12 and 15. It is the test no fix has seen
(DR-0023): its numbers carry inkgrid's headline claims, and the runs labelled as tuned do not.
**Everything in §§ 1–6 is fixed on 2026-10-01, before any tool reads a held-out document.** The only
reads before then were PyMuPDF's page text and drawing counts for § 1's rule, which score nothing.
**Modules:**
- `bench/heldout/manifest.toml`: the candidates, pinned by URL and SHA-256;
- `bench/heldout/<id>.json`: each document's ground truth (§ 2), committed;
- `bench/inkgrid_bench/heldout.py` (new, pure where it can be): selection, the ground truth's model,
  access paths, the glyph sample, and cell CER;
- `bench/inkgrid_bench/draft.py` (new): the drafting and review images (§ 3);
- `bench/inkgrid_bench/run.py`, `report.py`: the held-out run and its report (§ 6).

**FinTabNet.c is not measured.** Its annotations are CDLA-Permissive-2.0, but its PDFs came only from
IBM's Data Asset eXchange, retired; IBM's Hugging Face organizations hold no FinTabNet, Docling's
`FinTabNet_OTSL` holds page images, not PDFs, and the only PDFs are an unofficial 16.8 GB mirror
whose license is unclear (searched 2026-10-01). The user ruled to use an official source or none.

---

## 1 · The documents and pages (selection, fixed)

- **Candidates:** the 14 PDFs of `manifest.toml`, fetched from each exchange's or its clearing
  house's own site on 2026-10-01. Each is a fee schedule in English with a text layer on every page,
  from an exchange group none of the 42 tuning fee schedules comes from (NYSE/ICE, Nasdaq, Cboe, MIAX,
  LSEG, Euronext, SIX and BME, Deutsche Börse, Wiener Börse, GPW, JSE, Aquis, MEMX, LTSE, 24X, BOX,
  IEX). Euronext Athens is Euronext's, so it is not a candidate. Bursa Malaysia, CME Group, and an old
  JPX link refused the download and are not candidates.
- **One document per group:** the candidate with the most *numeric pages* (pages whose PyMuPDF text
  holds at least 20 tokens matching `\d[\d,.]*`), then the most pages, then the first by name.
- **Scored pages:** `random.Random(f"20261001:{id}").sample(numeric_pages, k=min(3, n))`, sorted.
  Every table on a scored page is in the ground truth; a scored page with no table has none, and a
  table a tool finds there is a false positive.

| Group | Document | Pages | Scored pages |
|---|---|---|---|
| ADX | `adx-csd` | 15 | 4, 7, 10 |
| ASX | `asx-trade` | 13 | 7, 8, 11 |
| B3 | `b3-equities` | 48 | 9, 16, 48 |
| Borsa Istanbul | `bist-data` | 9 | 4, 5, 8 |
| BVB | `bvb-participants` | 8 | 2, 3, 4 |
| JPX | `jpx-participant` | 11 | 2, 5, 6 |
| LuxSE | `luxse-listing` | 17 | 2, 4, 13 |
| NZX | `nzx-clearing` | 13 | 6, 7, 12 |
| PSX | `psx-trading-fee` | 5 | 1, 3, 4 |
| SET | `tfex-usd` | 2 | 1 |
| TMX | `tsx-trading` | 5 | 1, 3, 5 |

Eleven documents, 146 pages read by every tool, 31 pages scored. Every tool reads each whole
document, as a user would; only its tables on scored pages are scored.

## 2 · The ground truth (`bench/heldout/<id>.json`)

- A document's file holds its `id`, its scored `pages`, and its `tables`. A table has a `page`, a
  `bbox` (PDF points, origin at the page box's top left, unrotated, as spec 12 § 3.1), `stub_cols`
  (how many leading columns are row labels), and `cells`: each an anchor (`row`, `col`), a span
  (`rows`, `cols`), its `text`, `header` (a column-header cell), and its `box` (points, as `bbox`).
  The cells tile the table (spec 12's `NTable`); a header cell lies in the table's leading header
  rows; every box lies inside the table's.
- `drafted` names who drafted it and when; `verified` is `null` until the user has checked every
  table, then names the user, the date, and how many tables were corrected. **No held-out number is
  computed from a file whose `verified` is `null`.**
- **Access paths** (binding, spec 12 § 4.4) come from the ground truth: every non-empty cell outside
  the header rows and the stub columns is a value; its row labels are the non-empty stub cells covering
  its row, left to right, and its column labels the non-empty header cells covering its column, top to
  bottom (outermost first, as the practice set's). A dimension without a label is left out; a value
  with no label at all has no path.

## 3 · Drafting (Claude, never inkgrid)

- Each scored page is rendered at 150 DPI with a ruler in points; Claude reads the rendering and
  states each table's grid as its row and column boundaries in points, its spans, its header rows, and
  its stub columns.
- A cell's text is the PDF's words (PyMuPDF `get_text("words")`) whose centres lie in the cell's box,
  in reading order, joined by one space. **inkgrid's reading is never consulted**; the drafter does not
  run inkgrid, or any benchmarked tool, on a held-out document before § 6's run.
- Each draft is drawn over its page (cell boxes and their text) and checked by Claude against the
  rendering before it goes to the user.

## 4 · Verification (the user)

- The user reviews every table in a review page: the page's rendering with the drafted cells drawn
  over it, beside the table as a grid. For each table they mark it correct, or say what is wrong
  (a split or merged cell, a header row, a stub column, a word in the wrong cell, a missing table).
- Claude applies every correction and the corrected table is reviewed again. A document is verified
  when all its tables, and its table count per page, are marked correct.

## 5 · The glyph-verified sample and cell CER

- **The sample:** 200 cells drawn by `random.Random("20261001:cer").sample` from all non-empty
  ground-truth cells of the verified set (all of them if fewer). For each, the user sees its crop
  rendered at 400 DPI beside its claimed text and confirms it character by character, or corrects it.
  The confirmed text is the cell's truth for CER; a correction also corrects the ground truth.
- **Cell CER** of a tool: for each sampled cell with truth `g`, the tool's table on that page matched
  to the cell's ground-truth table (binding's region match), and `d` the least Levenshtein distance
  between `g` and any of that table's cell texts (any table on the page when none matches; `len(g)`
  when the tool has no table there), capped at `len(g)`. Texts compare after NFKC and collapsing
  whitespace runs to one space; case and punctuation count. CER is `Σ d / Σ len(g)`, pooled, with the
  clustered bootstrap over documents.

## 6 · Scoring and the run

- **Metrics:** the ICDAR-2013 competition scorer's structure and region F (`dataset-tools`, the
  ground truth rendered as its XML), binding over § 2's access paths, cell CER over § 5's sample,
  seconds per page, and crashes and timeouts. Only tables on scored pages are scored.
- **Tools:** every tool of specs 12 and 15 (the ground truth read as a tool is a check, as on ICDAR).
- **Frozen reading:** the run refuses to start unless `src/inkgrid` is identical to the tuned run's
  commit (`7f70dd6`), so the held-out numbers are the reading the tuned run measured.
- `run.py --datasets heldout` reads only the held-out documents and writes
  `bench/results/<date>-<commit>-heldout/`, whose report says in its title and first paragraph that no
  fix has seen these documents and that 11 documents give wide intervals.

---

## 7 · Cases

| Case | Input | Expected |
|---|---|---|
| SL1 | the manifest's candidates with their numeric-page counts | one per group, by § 1's order |
| SL2 | `scored_pages("x", [3, 5, 9, 12])` twice; with one numeric page | the same 3 sorted pages both times; that page |
| GT1 | a ground-truth file whose cells overlap; a header cell below a body row; a cell box outside its table; `verified` null | each refused, with the reason; scoring refuses an unverified file |
| GT2 | a table with 2 header rows (a spanning group label), 1 stub column | access paths with column labels outer then leaf, row labels; an empty header cell skipped |
| GT3 | a value with no label; a table of headers only | no path; no path |
| GS1 | 3 documents' cells, sample of 200 | every non-empty cell when fewer; the same sample twice |
| CE1 | truth `0.10%`, tool cells `0.1O%`, `0.10 %`, `fee` | distance 1 (the closest); whitespace collapsed |
| CE2 | a tool with no table on the page; a tool cell much longer than the truth | `len(g)`; capped at `len(g)` |
| RN1 | `--datasets heldout` with `src/` changed since the tuned run | refused, naming the commit |
| RN2 | `--datasets heldout` | only held-out readings; results under `<date>-<commit>-heldout/`; the report's title says held out |
| DR1 | words and a drafted grid | each word in the cell holding its centre, in reading order |

## 8 · Acceptance

- [ ] Every case above has a test named `test_<CaseId>_<slug>`, and it failed before its code.
- [ ] Every table of the 31 scored pages is drafted and verified by the user; every ground-truth file
      records its verification.
- [ ] The glyph sample is confirmed by the user.
- [ ] The held-out run completes for every tool; its results are committed; README states its numbers
      as the headline, labelled held out, and claims only what the intervals support.
