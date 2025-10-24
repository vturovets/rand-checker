"""Performance helpers for benchmarking and profiling data pipelines."""

from __future__ import annotations

import cProfile
import io
import statistics
import timeit
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterable, Iterator, Mapping, Sequence

from .analysis import merge_test_results
from .app import RandomnessCheckerApp
from .io import classify_entries
from .tests.base import TestResult


def benchmark_classification(entries: Iterable[str], *, repeat: int = 5) -> Mapping[str, float]:
    """Benchmark :func:`classify_entries` for the provided ``entries``."""

    entries_tuple = tuple(entries)
    timer = timeit.Timer(lambda: classify_entries(entries_tuple))
    runs = timer.repeat(repeat=repeat, number=1)
    return {
        "min": min(runs),
        "max": max(runs),
        "mean": statistics.fmean(runs),
    }


def benchmark_merge(weighted_results: Sequence[tuple[str, float, TestResult]], *, repeat: int = 5) -> Mapping[str, float]:
    """Benchmark :func:`merge_test_results` on ``weighted_results``."""

    cached_results = tuple(weighted_results)
    timer = timeit.Timer(
        lambda: merge_test_results(cached_results, confidence_threshold=0.5)
    )
    runs = timer.repeat(repeat=repeat, number=1)
    return {
        "min": min(runs),
        "max": max(runs),
        "mean": statistics.fmean(runs),
    }


def profile_application(input_path: Path, config_path: Path, *, repeat: int = 1) -> str:
    """Profile the end-to-end application pipeline using :mod:`cProfile`."""

    app = RandomnessCheckerApp()
    profiler = cProfile.Profile()
    for _ in range(repeat):
        profiler.runcall(app.run, input_path, config_path, None, False)
    stream = io.StringIO()
    stats = _build_stats(profiler, stream)
    stats.strip_dirs().sort_stats("cumulative").print_stats(25)
    return stream.getvalue()


@contextmanager
def capture_profile(
    app: RandomnessCheckerApp | None = None,
) -> Iterator[tuple[RandomnessCheckerApp, Callable[[int], str]]]:
    """Context manager capturing profiling data for manual inspection.

    The yielded tuple contains the :class:`RandomnessCheckerApp` instance to use
    for the profiled operations and a callable that returns a formatted profile
    summary when invoked.
    """

    profiler = cProfile.Profile()
    target_app = app or RandomnessCheckerApp()
    profiler.enable()

    def exporter(limit: int = 25) -> str:
        profiler.disable()
        stream = io.StringIO()
        stats = _build_stats(profiler, stream)
        stats.strip_dirs().sort_stats("cumulative").print_stats(limit)
        return stream.getvalue()

    try:
        yield target_app, exporter
    finally:
        profiler.disable()


def _build_stats(profiler: cProfile.Profile, stream: io.StringIO) -> "StatsWrapper":
    import pstats

    stats = pstats.Stats(profiler, stream=stream)
    return StatsWrapper(stats)


class StatsWrapper:
    """Thin wrapper delegating to :class:`pstats.Stats` methods."""

    def __init__(self, stats: "pstats.Stats") -> None:
        self._stats = stats

    def strip_dirs(self) -> "StatsWrapper":
        self._stats.strip_dirs()
        return self

    def sort_stats(self, *keys: str) -> "StatsWrapper":
        self._stats.sort_stats(*keys)
        return self

    def print_stats(self, *args: int | float | str) -> "StatsWrapper":
        self._stats.print_stats(*args)
        return self

    def __getattr__(self, name: str):
        return getattr(self._stats, name)


__all__ = [
    "benchmark_classification",
    "benchmark_merge",
    "capture_profile",
    "profile_application",
]
