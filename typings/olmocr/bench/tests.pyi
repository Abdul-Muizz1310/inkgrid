"""olmocr.bench.tests as `bench/inkgrid_bench/scores/olmocr_driver.py` uses it (olmocr 0.4.27)."""

class BasePDFTest:
    id: str
    pdf: str
    page: int
    type: str

def load_tests(jsonl_file: str) -> list[BasePDFTest]: ...
