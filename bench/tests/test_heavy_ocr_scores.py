"""Heavy: each OCR benchmark's pinned scorer, run as the OCR run runs it, on two of its documents.

Spec 18 s. 8, SC5. Run with `uv run pytest -m heavy --no-cov`; it needs the fetched benchmarks
(`run.py --datasets ocr prepare`) and builds or reuses each scorer's environment.
"""

from pathlib import Path

import pytest

from inkgrid_bench import ocr_run, run
from inkgrid_bench.adapters import inkgrid_read

pytestmark = pytest.mark.heavy


@pytest.mark.parametrize("benchmark", ocr_run.BENCHMARKS)
def test_SC5_each_scorer_scores_inkgrids_pages_as_the_run_calls_it(
    tmp_path: Path, benchmark: str
) -> None:
    cfg = run.config()
    docs = ocr_run.checked(benchmark, cfg)
    picked = [docs[0], docs[-1]]  # ParseBench's ids sort its tables before its text
    markdown = {d.id: inkgrid_read.read(d.pdf).markdown for d in picked}
    counts = ocr_run.SCORERS[benchmark](tmp_path / "work", cfg, picked, markdown)
    assert sorted(counts) == sorted(d.id for d in picked)
    first, last = (counts[d.id] for d in picked)
    match benchmark:
        case "olmocr":
            assert all(sum(v for k, v in c.items() if k.endswith("_tests")) for c in (first, last))
        case "omnidocbench":
            assert any(c["omni_text_len"] for c in (first, last))
        case "parsebench":
            assert first["pb_grits_trm_composite_n"] == 1
            assert last["pb_content_faithfulness_n"] == 1
            assert last["pb_content_faithfulness"] > 0
        case "dpbench":
            assert all(c["dp_nid_n"] == 1 and c["dp_nid"] > 0 for c in (first, last))
