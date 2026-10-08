"""Each reported number as a function of per-document counts (spec 12 sections 4 and 5).

Every scorer reduces a document to named counts (numerators and denominators); a metric recomputes
its number from any list of documents, so the bootstrap can resample documents and call it again.
An undefined number (a zero denominator) is NaN, never 0.
"""

import math
from collections.abc import Callable, Mapping, Sequence

Counts = Mapping[str, float]
Metric = Callable[[Sequence[Counts]], float]


def _total(docs: Sequence[Counts], key: str) -> float:
    return math.fsum(d[key] for d in docs)


def pooled(num: str, den: str) -> Metric:
    """The sum of `num` over the sum of `den`, over all documents."""

    def metric(docs: Sequence[Counts]) -> float:
        den_total = _total(docs, den)
        return _total(docs, num) / den_total if den_total else math.nan

    return metric


def mean_of(num: str, den: str) -> Metric:
    """The mean of each document's `num / den`; a document whose `den` is 0 is left out (SC2)."""

    def metric(docs: Sequence[Counts]) -> float:
        ratios = [d[num] / d[den] for d in docs if d[den]]
        return math.fsum(ratios) / len(ratios) if ratios else math.nan

    return metric


def harmonic(a: Metric, b: Metric) -> Metric:
    """The harmonic mean of two metrics (the competition's F from mean precision and recall)."""

    def metric(docs: Sequence[Counts]) -> float:
        x, y = a(docs), b(docs)
        if math.isnan(x) or math.isnan(y):
            return math.nan
        return 2 * x * y / (x + y) if x + y else 0.0

    return metric


def dice(num: str, a: str, b: str) -> Metric:
    """Twice the sum of `num` over the sums of `a` and `b` (Soric et al.'s F1 forms)."""

    def metric(docs: Sequence[Counts]) -> float:
        den = _total(docs, a) + _total(docs, b)
        return 2 * _total(docs, num) / den if den else math.nan

    return metric


def macro(*metrics: Metric) -> Metric:
    """The mean of several metrics, each weighted alike (olmOCR-bench's born-digital macro)."""

    def metric(docs: Sequence[Counts]) -> float:
        values = [m(docs) for m in metrics]
        return math.nan if any(math.isnan(v) for v in values) else math.fsum(values) / len(values)

    return metric
