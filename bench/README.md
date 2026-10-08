# inkgrid's benchmark

The harness behind `docs/specs/12-benchmark.md`. It lives in the repository and ships in neither the
wheel nor the sdist.

- `sources.toml` pins every dataset, scorer, and tool; `olmocr-tables.sha256` lists olmOCR-bench's table
  PDFs. `inkgrid_bench.fetch` downloads them into `~/.cache/inkgrid-bench/` and checks every hash.
  Nothing downloaded is committed.
- Adapters run inside each tool's own pinned environment and write a normalized table per document.
- The scorers are the datasets' own: the ICDAR-2013 competition's jar (under a Temurin 17 JRE), Soric et
  al.'s evaluator at v1.0.0, and olmOCR-bench's scorer (`olmocr` 0.4.27).
- `bench/results/` holds the committed results; `latest.md` is the newest report.

Run it from the repository root, on a clean tree (results name the commit they measure):

```bash
PYTHONPATH=bench uv run python -m inkgrid_bench.run all   # or: prepare, read, verify, score, report
```

The heavy competitors of `docs/specs/15-heavy-competitors.md` (Docling, marker, unstructured) each
run in one process per tool, their models loaded once, from PyTorch's CPU build and with every
dependency resolved as of the date `sources.toml` pins; `prepare` builds the pinned Tesseract into the
cache with micromamba (no root needed). With them, a full run takes about eight to ten hours on a
16-thread CPU: in the run of 2026-10-02 the tools read for 6.1 hours (Docling's two runs 4.5 of them,
unstructured 0.9), and scoring took 1.6.

A run after inkgrid's fixes for errors found on these datasets is labelled `--label tuned`
(DR-0023): its results go to `bench/results/<date>-<commit>-tuned/`, and its report says it is
tuned on these documents in its title and first paragraph. The baseline's results stay beside it.

The held-out fee set of `docs/specs/16-held-out-fee-set.md` runs on its own:

```bash
PYTHONPATH=bench uv run python -m inkgrid_bench.run all --datasets heldout
```

It refuses to start unless `src/inkgrid` is the tuned run's and every ground truth in `heldout/` is
verified, and it writes `bench/results/<date>-<commit>-heldout/`. Its 11 documents take about two
hours, nearly all of it the heavy tools.

The OCR benchmarks of `docs/specs/18-ocr-benchmarks.md` (born-digital text and tables only, from
olmOCR-bench, OmniDocBench, ParseBench and DP-Bench) run on their own too:

```bash
PYTHONPATH=bench uv run python -m inkgrid_bench.run prepare --datasets ocr   # then read, score, report
```

`bench/ocr/` holds the census manifests, which fix the 2,238 scored documents, and the listings of
the files each benchmark is fetched as. Every stage refuses data or a census other than the pinned
ones, and a run labelled baseline refuses an `src/inkgrid` other than 0.1.0's. Each scorer runs
unmodified at its pin in its own environment; the results go to `bench/results/<date>-<commit>-ocr/`.
`uv run pytest -m heavy --no-cov` runs each scorer on two documents first (SC5).

Everything it fetches and writes lives in `~/.cache/inkgrid-bench/`; each stage skips the documents
an earlier run of it finished. The datasets and tools take about 0.6 GB there; uv builds each tool's
and scorer's environment on first use (PyTorch's CPU build among them). It runs one document at a
time, niced; without the heavy tools, in about two and a half hours.

Datasets are the property of their publishers: ICDAR-2013 (Göbel, Hassan, Oro and Orsi, 2013);
olmOCR-bench (ODC-BY-1.0, Poznanski et al., arXiv 2502.18443); Soric et al.'s ICDAR-2013 ground truth
(KDD '26); OmniDocBench (OpenDataLab, research use); ParseBench (LlamaIndex, Apache-2.0); DP-Bench
(Upstage, MIT, through opendataloader-bench, Apache-2.0).
