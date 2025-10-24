"""Factory utilities for registering and instantiating randomness tests."""

from __future__ import annotations

from typing import Dict, List, Mapping, MutableMapping, Tuple

from ..config import RandomCheckConfig
from ..errors import InvalidConfigurationError
from ..io import InputData
from .base import RandomnessTest
from .statistical import (
    AutocorrelationTest,
    ChiSquareTest,
    EntropyTest,
    KolmogorovSmirnovTest,
    MonobitTest,
    RunsTest,
    SerialTest,
    ShannonEntropyTest,
)


def _default_registry() -> Dict[str, RandomnessTest]:
    return {
        test.name: test
        for test in (
            MonobitTest(),
            RunsTest(),
            SerialTest(),
            ChiSquareTest(),
            EntropyTest(),
            AutocorrelationTest(),
            KolmogorovSmirnovTest(),
            ShannonEntropyTest(),
        )
    }


DEFAULT_TESTS: Mapping[str, RandomnessTest] = _default_registry()


def build_test_suite(
    config: RandomCheckConfig,
    input_data: InputData,
    *,
    registry: Mapping[str, RandomnessTest] | None = None,
) -> List[Tuple[RandomnessTest, float]]:
    """Construct a sequence of applicable tests with their weights."""

    tests: MutableMapping[str, RandomnessTest]
    tests = dict(registry or DEFAULT_TESTS)
    active: List[Tuple[RandomnessTest, float]] = []
    for name in config.tests.enabled_tests:
        test = tests.get(name)
        if test is None:
            raise InvalidConfigurationError(f"Unknown test '{name}' in configuration.")
        weight = config.weights.values.get(name)
        if weight is None:
            raise InvalidConfigurationError(
                f"No weight provided for enabled test '{name}'.",
            )
        if not test.is_applicable(input_data):
            raise InvalidConfigurationError(
                f"Test '{name}' is not applicable to entry type '{input_data.entry_type}'.",
            )
        active.append((test, weight))
    if not active:
        raise InvalidConfigurationError("At least one test must be enabled in configuration.")
    return active
__all__ = ["DEFAULT_TESTS", "build_test_suite"]
