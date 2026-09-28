"""olmocr.bench.benchmark as `bench/inkgrid_bench/scores/olmocr_driver.py` uses it (0.4.27)."""

from olmocr.bench.tests import BasePDFTest

def evaluate_candidate(
    candidate_folder: str,
    all_tests: list[BasePDFTest],
    pdf_basenames: list[str],
    force: bool = False,
) -> tuple[
    float,
    int,
    list[str],
    list[str],
    dict[str, list[float]],
    list[float],
    dict[str, dict[int, list[tuple[BasePDFTest, bool, str]]]],
]: ...
