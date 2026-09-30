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

A run after inkgrid's fixes for errors found on these datasets is labelled `--label tuned`
(DR-0023): its results go to `bench/results/<date>-<commit>-tuned/`, and its report says it is
tuned on these documents in its title and first paragraph. The baseline's results stay beside it.

Everything it fetches and writes lives in `~/.cache/inkgrid-bench/`; each stage skips the documents
an earlier run of it finished. The datasets and tools take about 0.6 GB there; uv builds each tool's
and scorer's environment on first use (PyTorch's CPU build among them). It runs one document at a
time, niced, in about two and a half hours.

Datasets are the property of their publishers: ICDAR-2013 (Göbel, Hassan, Oro and Orsi, 2013);
olmOCR-bench (ODC-BY-1.0, Poznanski et al., arXiv 2502.18443); Soric et al.'s ICDAR-2013 ground truth
(KDD '26).
