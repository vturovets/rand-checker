from __future__ import annotations

from randomcheck.perf import (
    benchmark_classification,
    benchmark_merge,
    capture_profile,
)
from randomcheck.tests.base import TestResult as RandomTestResult


def test_benchmark_classification_returns_statistics() -> None:
    stats = benchmark_classification(["1", "2", "3"], repeat=2)

    assert set(stats) == {"min", "max", "mean"}
    assert stats["max"] >= stats["min"]


def test_benchmark_merge_returns_statistics() -> None:
    weighted_results = (
        ("monobit", 0.6, RandomTestResult(p_value=0.8, details="ok")),
        ("runs", 0.4, RandomTestResult(p_value=0.7, details="ok")),
    )

    stats = benchmark_merge(weighted_results, repeat=2)

    assert set(stats) == {"min", "max", "mean"}
    assert stats["mean"] >= 0.0


def test_capture_profile_returns_profile_output() -> None:
    with capture_profile() as (app, exporter):
        # Execute a trivial operation while profiling.
        app._resolve_threshold  # attribute access to ensure object used

    profile_output = exporter()

    assert "function calls" in profile_output
