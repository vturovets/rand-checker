"""Application orchestration for the randomness checker CLI."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from .config import RandomCheckConfig, load_config
from .errors import InvalidConfigurationError, TestExecutionError
from .io import EntryType, InputData, read_input_file
from .tests import DEFAULT_TESTS, RandomnessTest, build_test_suite


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
    entry_type: EntryType
    overall_score: float
    is_random: bool
    confidence_threshold: float
    test_results: Sequence[TestResult]


class RandomnessCheckerApp:
    """High level service wiring configuration, execution, and rendering."""

    def __init__(self, tests: Sequence[RandomnessTest] | Mapping[str, RandomnessTest] | None = None) -> None:
        if tests is None:
            available: Iterable[RandomnessTest] = DEFAULT_TESTS.values()
        elif isinstance(tests, Mapping):
            available = tests.values()
        else:
            available = tests
        self._tests: Dict[str, RandomnessTest] = {test.name: test for test in available}

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

        input_data = self._load_input(input_path)
        config = self._load_config(config_path)
        for warning in config.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        active_tests = self._resolve_tests(config, input_data)
        threshold = self._resolve_threshold(config)
        effective_report = report_path or config.output.report_path
        verbose_output = verbose or config.output.log_results
        run_result = self._execute_tests(
            input_path,
            config_path,
            input_data,
            active_tests,
            threshold,
        )
        self._render_summary(run_result, verbose=verbose_output)
        if effective_report is not None:
            self._render_report(run_result, effective_report)
        return run_result

    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------
    def _load_input(self, path: Path) -> InputData:
        return read_input_file(path)

    def _load_config(self, path: Path) -> RandomCheckConfig:
        return load_config(path)

    def _resolve_tests(
        self, config: RandomCheckConfig, input_data: InputData
    ) -> List[Tuple[RandomnessTest, float]]:
        return build_test_suite(config, input_data, registry=self._tests)

    def _resolve_threshold(self, config: RandomCheckConfig) -> float:
        return config.output.confidence_threshold

    def _execute_tests(
        self,
        input_path: Path,
        config_path: Path,
        input_data: InputData,
        tests: Sequence[Tuple[RandomnessTest, float]],
        threshold: float,
    ) -> RunResult:
        test_results: List[TestResult] = []
        total_weight = 0.0
        weighted_score = 0.0
        for test, weight in tests:
            try:
                outcome = test.run(input_data)
            except Exception as exc:  # pragma: no cover - defensive guard
                raise TestExecutionError(f"Test '{test.name}' failed to execute.") from exc
            score = max(0.0, min(1.0, float(outcome.p_value)))
            test_results.append(
                TestResult(
                    name=test.name,
                    score=score,
                    weight=weight,
                    details=outcome.details,
                )
            )
            total_weight += weight
            weighted_score += score * weight
        overall_score = weighted_score / total_weight if total_weight > 0 else 0.0
        is_random = overall_score >= threshold
        return RunResult(
            input_path=input_path,
            config_path=config_path,
            total_entries=input_data.entry_count,
            entry_type=input_data.entry_type,
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
            print(f"Detected entry type: {result.entry_type}")
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
            f"**Detected type:** {result.entry_type}",
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
