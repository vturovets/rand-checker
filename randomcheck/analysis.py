"""Utilities for merging statistical test results into an overall verdict.

The :mod:`randomcheck.tests` package exposes individual statistical tests that
return :class:`randomcheck.tests.base.TestResult` objects.  This module is
responsible for combining those raw outcomes with the configured weights so we
can provide a single confidence score for the analysed input.

Two thresholds are important during the analysis stage:

``DEFAULT_SIGNIFICANCE_LEVEL``
    The default per-test significance level (:math:`\alpha`).  A test is
    considered to *fail* when ``p_value < alpha``.  Consumers can override this
    value when calling :func:`merge_test_results`.

``confidence_threshold``
    The minimum weighted confidence that the aggregated results must reach in
    order for the analysed sequence to be considered random.  The threshold is
    expressed as a percentage when returned in :class:`OverallResult` to make it
    easier to display in reports and CLIs.

When the input data mixes different entry types (for example, alphabetic and
numeric strings), a short justification note is added to the metadata of both
the per-test results and the final summary.  This metadata can be rendered by
reporting layers to explain why the analysis may require additional scrutiny.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence, Tuple

from .io import EntryType
from .tests.base import TestResult as RawTestResult

DEFAULT_SIGNIFICANCE_LEVEL: float = 0.05
"""Default :math:`\alpha` used to evaluate individual tests."""

MIXED_DATA_JUSTIFICATION = (
    "Input classified as 'mixed'; statistical weights retain heterogeneous "
    "signals so the overall confidence remains conservative."
)
"""Explanation attached to metadata when mixed entry types are detected."""


@dataclass(frozen=True)
class MergedTestResult:
    """Result of analysing a single test outcome with weighting information."""

    name: str
    p_value: float
    weight: float
    passed: bool
    threshold: float
    details: str
    metadata: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class OverallResult:
    """Aggregate verdict built from the weighted test outcomes."""

    confidence: float
    passed: bool
    threshold: float
    tests: Tuple[MergedTestResult, ...]
    metadata: Tuple[str, ...] = field(default_factory=tuple)


def merge_test_results(
    weighted_results: Sequence[tuple[str, float, RawTestResult]],
    *,
    confidence_threshold: float,
    alpha: float = DEFAULT_SIGNIFICANCE_LEVEL,
    entry_type: EntryType | None = None,
) -> OverallResult:
    """Merge raw test results into a weighted overall score.

    Parameters
    ----------
    weighted_results:
        Sequence of ``(name, weight, result)`` tuples.  ``weight`` is the
        already normalised contribution of the test as specified in the
        configuration file.
    confidence_threshold:
        Minimum weighted confidence required to consider the input random.
        The value is expected in the ``[0.0, 1.0]`` range and converted to a
        percentage in the returned :class:`OverallResult`.
    alpha:
        Per-test significance level.  When a test returns ``p_value < alpha``
        the test is considered failed.  By default the commonly used ``0.05``
        threshold is applied.
    entry_type:
        Entry type inferred from the input data.  If the data is marked as
        ``"mixed"`` a justification note is attached to the resulting metadata.
    """

    analysed_results: list[MergedTestResult] = []
    total_weight = 0.0
    weighted_score = 0.0

    metadata: Tuple[str, ...] = ()
    if entry_type == "mixed":
        metadata = (MIXED_DATA_JUSTIFICATION,)

    for name, weight, result in weighted_results:
        p_value = max(0.0, min(1.0, float(result.p_value)))
        passed = p_value >= alpha
        result_metadata = metadata if metadata else ()
        analysed_results.append(
            MergedTestResult(
                name=name,
                p_value=p_value,
                weight=weight,
                passed=passed,
                threshold=alpha,
                details=result.details,
                metadata=result_metadata,
            )
        )
        total_weight += weight
        weighted_score += p_value * weight

    confidence = (weighted_score / total_weight) if total_weight else 0.0
    confidence_pct = confidence * 100.0
    threshold_pct = confidence_threshold * 100.0
    passed_overall = confidence_pct >= threshold_pct if total_weight else False

    return OverallResult(
        confidence=confidence_pct,
        passed=passed_overall,
        threshold=threshold_pct,
        tests=tuple(analysed_results),
        metadata=metadata,
    )


__all__ = [
    "DEFAULT_SIGNIFICANCE_LEVEL",
    "MIXED_DATA_JUSTIFICATION",
    "MergedTestResult",
    "OverallResult",
    "merge_test_results",
]
