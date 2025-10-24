"""Unit tests for :mod:`randomcheck.analysis`."""

from __future__ import annotations

import pytest

from randomcheck.analysis import (
    DEFAULT_SIGNIFICANCE_LEVEL,
    MIXED_DATA_JUSTIFICATION,
    merge_test_results,
)
from randomcheck.tests.base import TestResult as RawTestResult


def test_merge_test_results_weights_and_confidence() -> None:
    """Weighted confidence is averaged and converted into a percentage."""

    outcomes = [
        ("frequency", 0.6, RawTestResult(p_value=0.8, details="ok")),
        ("runs", 0.4, RawTestResult(p_value=0.2, details="borderline")),
    ]

    result = merge_test_results(outcomes, confidence_threshold=0.5)

    expected_confidence = (0.8 * 0.6 + 0.2 * 0.4) * 100
    assert result.confidence == pytest.approx(expected_confidence)
    assert result.threshold == pytest.approx(50.0)
    assert result.passed is True
    assert len(result.tests) == 2
    assert all(test.passed for test in result.tests)


def test_merge_test_results_respects_significance_threshold() -> None:
    """Per-test failure occurs when the p-value drops below alpha."""

    low_p_value = DEFAULT_SIGNIFICANCE_LEVEL / 2
    outcomes = [("frequency", 1.0, RawTestResult(p_value=low_p_value, details="fail"))]

    result = merge_test_results(outcomes, confidence_threshold=0.9)

    assert result.confidence == pytest.approx(low_p_value * 100)
    assert result.threshold == pytest.approx(90.0)
    assert result.passed is False
    assert result.tests[0].passed is False
    assert result.tests[0].threshold == DEFAULT_SIGNIFICANCE_LEVEL


def test_merge_test_results_includes_mixed_data_metadata() -> None:
    """Mixed entry types add justification notes to the metadata fields."""

    outcomes = [("frequency", 1.0, RawTestResult(p_value=0.5, details="ok"))]

    result = merge_test_results(outcomes, confidence_threshold=0.5, entry_type="mixed")

    assert MIXED_DATA_JUSTIFICATION in result.metadata
    assert MIXED_DATA_JUSTIFICATION in result.tests[0].metadata
