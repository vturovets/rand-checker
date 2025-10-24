"""Application orchestration for the randomness checker CLI."""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List, MutableMapping, Sequence, Tuple

from .errors import (
    InvalidConfigurationError,
    MissingFileError,
    TestExecutionError,
)


@dataclass(frozen=True)
class TestResult:
    """Container with the outcome of a single randomness test."""

    name: str
    score: float
    weight: float
    details: str

    @property
    def passed(self) -> bool:
        """Return whether the test considered the input random enough."""

        return self.score >= 0.5


@dataclass(frozen=True)
class RunResult:
    """Summary of a full application run."""

    input_path: Path
    config_path: Path
    total_entries: int
    overall_score: float
    is_random: bool
    confidence_threshold: float
    test_results: Sequence[TestResult]


class _BaseTest:
    """Base class for the built-in heuristics."""

    name: str

    def run(self, entries: Sequence[str]) -> Tuple[float, str]:
        raise NotImplementedError


class _DiversityTest(_BaseTest):
    name = "diversity"

    def run(self, entries: Sequence[str]) -> Tuple[float, str]:
        total = len(entries)
        if total == 0:
            return 0.0, "No entries provided."
        unique_count = len(set(entries))
        score = unique_count / total
        details = f"{unique_count} unique entries out of {total}."
        return score, details


class _RunsVariationTest(_BaseTest):
    name = "runs"

    def run(self, entries: Sequence[str]) -> Tuple[float, str]:
        total = len(entries)
        if total <= 1:
            return 1.0, "Not enough data for runs analysis; treating as ideal."
        changes = sum(1 for idx in range(1, total) if entries[idx] != entries[idx - 1])
        score = changes / (total - 1)
        details = f"{changes} transitions across {total - 1} comparisons."
        return score, details


class _EntropyTest(_BaseTest):
    name = "entropy"

    def run(self, entries: Sequence[str]) -> Tuple[float, str]:
        total = len(entries)
        if total == 0:
            return 0.0, "No entries available for entropy calculation."
        counts = Counter(entries)
        probabilities = [count / total for count in counts.values()]
        entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)
        unique = len(counts)
        if unique <= 1:
            return 0.0, "Entropy is zero because only a single unique entry was found."
        max_entropy = math.log2(unique)
        score = entropy / max_entropy if max_entropy > 0 else 0.0
        details = (
            f"Computed entropy {entropy:.3f} bits across {unique} unique entries (max {max_entropy:.3f})."
        )
        return score, details


DEFAULT_TESTS: Tuple[_BaseTest, ...] = (
    _DiversityTest(),
    _RunsVariationTest(),
    _EntropyTest(),
)


class RandomnessCheckerApp:
    """High level service wiring configuration, execution, and rendering."""

    def __init__(self, tests: Sequence[_BaseTest] | None = None) -> None:
        self._tests = {test.name: test for test in (tests or DEFAULT_TESTS)}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(
        self,
        input_path: Path,
        config_path: Path,
        report_path: Path | None = None,
        verbose: bool = False,
    ) -> RunResult:
        """Execute the randomness checker workflow."""

        entries = self._load_input(input_path)
        config = self._load_config(config_path)
        active_tests = self._resolve_tests(config)
        threshold = self._resolve_threshold(config)
        run_result = self._execute_tests(input_path, config_path, entries, active_tests, threshold)
        self._render_summary(run_result, verbose=verbose)
        if report_path is not None:
            self._render_report(run_result, report_path)
        return run_result

    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------
    def _load_input(self, path: Path) -> List[str]:
        if not path.exists():
            raise MissingFileError(f"Input file not found: {path}")
        try:
            with path.open("r", encoding="utf-8") as input_file:
                # Strip newline characters but preserve empty strings intentionally entered
                entries = [line.rstrip("\n") for line in input_file]
        except OSError as exc:
            raise MissingFileError(f"Could not read input file: {path}") from exc
        return entries

    def _load_config(self, path: Path) -> MutableMapping[str, object]:
        if not path.exists():
            raise MissingFileError(f"Configuration file not found: {path}")
        try:
            with path.open("r", encoding="utf-8") as config_file:
                data = json.load(config_file)
        except json.JSONDecodeError as exc:
            raise InvalidConfigurationError(f"Configuration is not valid JSON: {exc}") from exc
        except OSError as exc:
            raise MissingFileError(f"Could not read configuration file: {path}") from exc
        if not isinstance(data, MutableMapping):
            raise InvalidConfigurationError("Configuration root must be a JSON object.")
        return data

    def _resolve_tests(
        self, config: MutableMapping[str, object]
    ) -> List[Tuple[_BaseTest, float]]:
        tests_section = config.get("tests")
        active_tests: List[Tuple[_BaseTest, float]] = []
        if tests_section is None:
            for test in self._tests.values():
                active_tests.append((test, 1.0))
            return active_tests
        if not isinstance(tests_section, MutableMapping):
            raise InvalidConfigurationError("The 'tests' section must be a JSON object mapping names to settings.")
        for name, settings in tests_section.items():
            if name not in self._tests:
                raise InvalidConfigurationError(f"Unknown test '{name}' in configuration.")
            if settings is None:
                enabled = True
                weight = 1.0
            elif isinstance(settings, MutableMapping):
                enabled = bool(settings.get("enabled", True))
                try:
                    weight_value = settings.get("weight", 1.0)
                    weight = float(weight_value)
                except (TypeError, ValueError) as exc:
                    raise InvalidConfigurationError(
                        f"Weight for test '{name}' must be numeric."
                    ) from exc
            else:
                raise InvalidConfigurationError(
                    f"Settings for test '{name}' must be an object with 'enabled'/'weight' keys."
                )
            if not enabled:
                continue
            if weight <= 0:
                raise InvalidConfigurationError(f"Weight for test '{name}' must be greater than zero.")
            active_tests.append((self._tests[name], weight))
        if not active_tests:
            raise InvalidConfigurationError("At least one test must be enabled in the configuration.")
        return active_tests

    def _resolve_threshold(self, config: MutableMapping[str, object]) -> float:
        threshold_value = config.get("confidence_threshold", 0.6)
        try:
            threshold = float(threshold_value)
        except (TypeError, ValueError) as exc:
            raise InvalidConfigurationError("'confidence_threshold' must be numeric.") from exc
        if not 0.0 <= threshold <= 1.0:
            raise InvalidConfigurationError("'confidence_threshold' must be between 0 and 1.")
        return threshold

    def _execute_tests(
        self,
        input_path: Path,
        config_path: Path,
        entries: Sequence[str],
        tests: Sequence[Tuple[_BaseTest, float]],
        threshold: float,
    ) -> RunResult:
        test_results: List[TestResult] = []
        total_weight = 0.0
        weighted_score = 0.0
        for test, weight in tests:
            try:
                score, details = test.run(entries)
            except Exception as exc:  # pragma: no cover - defensive guard
                raise TestExecutionError(f"Test '{test.name}' failed to execute.") from exc
            score = max(0.0, min(1.0, float(score)))
            test_results.append(TestResult(name=test.name, score=score, weight=weight, details=details))
            total_weight += weight
            weighted_score += score * weight
        overall_score = weighted_score / total_weight if total_weight > 0 else 0.0
        is_random = overall_score >= threshold
        return RunResult(
            input_path=input_path,
            config_path=config_path,
            total_entries=len(entries),
            overall_score=overall_score,
            is_random=is_random,
            confidence_threshold=threshold,
            test_results=test_results,
        )

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    def _render_summary(self, result: RunResult, *, verbose: bool) -> None:
        status = "RANDOM" if result.is_random else "NON-RANDOM"
        overall = result.overall_score * 100
        print(f"Result: {status} | Confidence: {overall:.1f}%")
        if verbose:
            for test_result in result.test_results:
                score_pct = test_result.score * 100
                print(
                    f" - {test_result.name}: {score_pct:.1f}% (weight {test_result.weight})\n   {test_result.details}"
                )
            print(f"Threshold: {result.confidence_threshold:.2f}")

    def _render_report(self, result: RunResult, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Randomness Checker Report",
            "",
            f"**Input file:** {result.input_path}",
            f"**Configuration:** {result.config_path}",
            f"**Total entries:** {result.total_entries}",
            "",
            f"**Overall confidence:** {result.overall_score * 100:.2f}%",
            f"**Threshold:** {result.confidence_threshold * 100:.2f}%",
            f"**Result:** {'RANDOM' if result.is_random else 'NON-RANDOM'}",
            "",
            "## Test Breakdown",
        ]
        for test_result in result.test_results:
            lines.extend(
                [
                    f"### {test_result.name}",
                    f"Score: {test_result.score * 100:.2f}%",
                    f"Weight: {test_result.weight}",
                    "Details:",
                    f"{test_result.details}",
                    "",
                ]
            )
        report_content = "\n".join(lines)
        path.write_text(report_content, encoding="utf-8")


__all__ = ["RandomnessCheckerApp", "RunResult", "TestResult"]
