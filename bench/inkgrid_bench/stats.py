"""The clustered bootstrap of spec 12 section 5: resample documents, recompute the metric.

A resample draws as many documents as there are, with replacement, and hands the metric their
counts; a table or a test never moves without its document. Documents are taken in sorted order of
their ids, so the draws depend only on the seed. A paired difference uses the same draws for both
tools. A resample whose metric is undefined (NaN) is left out of the percentiles.
"""

import math
import random
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass

from inkgrid_bench.scores.metrics import Counts, Metric

RESAMPLES = 10_000
SEED = 20260928
LOW, HIGH = 0.025, 0.975


@dataclass(frozen=True, slots=True)
class Interval:
    """A point estimate and its 95% percentile interval."""

    point: float
    low: float
    high: float


def _ids(docs: Mapping[str, Counts]) -> list[str]:
    if not docs:
        msg = "no documents to resample"
        raise ValueError(msg)
    return sorted(docs)


def _draws(n: int, resamples: int, seed: int) -> Iterator[list[int]]:
    rng = random.Random(seed)  # noqa: S311 - a reproducible resample, not a secret
    for _ in range(resamples):
        yield [rng.randrange(n) for _ in range(n)]


def _percentile(ordered: Sequence[float], q: float) -> float:
    """The q-th quantile of sorted values, interpolated linearly between the two nearest.

    Equal neighbours give exactly their value, so a constant metric's interval is the constant.
    """
    at = q * (len(ordered) - 1)
    j = int(at)
    if j + 1 >= len(ordered):
        return ordered[-1]
    lo, hi = ordered[j], ordered[j + 1]
    return lo if lo == hi else lo + (hi - lo) * (at - j)


def _interval(point: float, values: Sequence[float]) -> Interval:
    defined = sorted(v for v in values if not math.isnan(v))
    if math.isnan(point) or not defined:
        return Interval(point, math.nan, math.nan)
    return Interval(point, _percentile(defined, LOW), _percentile(defined, HIGH))


def bootstrap(
    docs: Mapping[str, Counts], metric: Metric, *, resamples: int = RESAMPLES, seed: int = SEED
) -> Interval:
    """A metric over the documents, with its interval over resampled documents."""
    ids = _ids(docs)
    ordered = [docs[i] for i in ids]
    point = metric(ordered)
    values = [metric([ordered[j] for j in draw]) for draw in _draws(len(ids), resamples, seed)]
    return _interval(point, values)


def paired(
    a: Mapping[str, Counts],
    b: Mapping[str, Counts],
    metric: Metric,
    *,
    resamples: int = RESAMPLES,
    seed: int = SEED,
) -> Interval:
    """The metric on `a` minus the metric on `b`, both over the same resampled documents."""
    if set(a) != set(b):
        msg = "a paired difference needs the same documents on both sides"
        raise ValueError(msg)
    ids = _ids(a)
    side_a, side_b = [a[i] for i in ids], [b[i] for i in ids]
    point = metric(side_a) - metric(side_b)
    values = []
    for draw in _draws(len(ids), resamples, seed):
        x = metric([side_a[j] for j in draw])
        values.append(x - metric([side_b[j] for j in draw]))
    return _interval(point, values)
