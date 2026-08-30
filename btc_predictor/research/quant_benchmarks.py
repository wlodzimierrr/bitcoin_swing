"""Small opt-in performance benchmarks for the validated quantitative core."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from statistics import median
from time import perf_counter_ns
from typing import Any

import numpy as np
from numpy.typing import NDArray

from btc_predictor.quant import (
    risk_at_stop,
    rolling_mean,
    rolling_zscore,
    weighted_score,
)

QUANT_BENCHMARK_VERSION = "QUANT_BENCHMARK_V1"
QUANT_BENCHMARK_NAMES = (
    "rolling_mean_20",
    "rolling_zscore_60",
    "weighted_score_8",
    "risk_at_stop_4",
)


@dataclass(frozen=True)
class QuantBenchmarkResult:
    """One timing result; elapsed time is diagnostic and never a test gate."""

    name: str
    observation_count: int
    repeats: int
    best_seconds: float
    median_seconds: float
    observations_per_second: float
    checksum: float
    benchmark_version: str = QUANT_BENCHMARK_VERSION

    def as_record(self) -> dict[str, str | int | float]:
        return {
            "benchmark_version": self.benchmark_version,
            "name": self.name,
            "observation_count": self.observation_count,
            "repeats": self.repeats,
            "best_seconds": self.best_seconds,
            "median_seconds": self.median_seconds,
            "observations_per_second": self.observations_per_second,
            "checksum": self.checksum,
        }


def run_basic_quant_benchmarks(
    *,
    observation_count: int = 100_000,
    repeats: int = 3,
    seed: int = 49,
) -> tuple[QuantBenchmarkResult, ...]:
    """Time representative kernels without imposing environment-specific limits."""

    _positive_integer(observation_count, "observation_count")
    _positive_integer(repeats, "repeats")
    _non_negative_integer(seed, "seed")
    generator = np.random.Generator(np.random.PCG64(seed))
    returns = generator.normal(0.0005, 0.025, size=observation_count)
    scores = generator.normal(50, 15, size=(observation_count, 8))
    notionals = generator.uniform(500, 10_000, size=(observation_count, 4))
    entries = generator.uniform(80_000, 120_000, size=(observation_count, 4))
    stops = entries * np.float64(0.9)
    weights = {f"component_{index}": 0.125 for index in range(8)}
    component_names = tuple(weights)

    cases: tuple[tuple[str, Callable[[], Any]], ...] = (
        (
            "rolling_mean_20",
            lambda: rolling_mean(returns, window=20, min_periods=20),
        ),
        (
            "rolling_zscore_60",
            lambda: rolling_zscore(returns, window=60, min_periods=60),
        ),
        (
            "weighted_score_8",
            lambda: (
                weighted_score(
                    scores,
                    weights,
                    component_names=component_names,
                ).scores
            ),
        ),
        (
            "risk_at_stop_4",
            lambda: risk_at_stop(notionals, entries, stops, side="long"),
        ),
    )
    return tuple(
        _measure_case(
            name,
            operation,
            observation_count=observation_count,
            repeats=repeats,
        )
        for name, operation in cases
    )


def _measure_case(
    name: str,
    operation: Callable[[], Any],
    *,
    observation_count: int,
    repeats: int,
) -> QuantBenchmarkResult:
    operation()
    elapsed: list[float] = []
    output: Any = None
    for _ in range(repeats):
        start = perf_counter_ns()
        output = operation()
        elapsed.append((perf_counter_ns() - start) / 1_000_000_000)
    best = min(elapsed)
    return QuantBenchmarkResult(
        name=name,
        observation_count=observation_count,
        repeats=repeats,
        best_seconds=best,
        median_seconds=median(elapsed),
        observations_per_second=observation_count / best,
        checksum=_checksum(output),
    )


def _checksum(values: Any) -> float:
    array: NDArray[np.float64] = np.asarray(values, dtype=np.float64)
    return float(np.nansum(array, dtype=np.float64))


def _positive_integer(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be an integer >= 1")


def _non_negative_integer(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=int, default=100_000)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=49)
    arguments = parser.parse_args(argv)
    results = run_basic_quant_benchmarks(
        observation_count=arguments.observations,
        repeats=arguments.repeats,
        seed=arguments.seed,
    )
    print(json.dumps([result.as_record() for result in results], indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI boundary
    raise SystemExit(main())
