"""Application orchestration for the randomness checker CLI."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from .analysis import MergedTestResult, OverallResult, merge_test_results
from .config import RandomCheckConfig, load_config
from .errors import TestExecutionError
from .io import EntryType, InputData, read_input_file
from .tests import DEFAULT_TESTS, RandomnessTest, build_test_suite
from .tests.base import TestResult as RawTestResult
from . import reporting


@dataclass(frozen=True)
class RunResult:
    """Summary of a full application run."""

    input_path: Path
    config_path: Path
    total_entries: int
    entry_type: EntryType
    overall_confidence: float
    is_random: bool
    confidence_threshold: float
    test_results: Sequence[MergedTestResult]
    report_metadata: Sequence[str]
    started_at: datetime
    duration: timedelta


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

        started_at = datetime.now(timezone.utc)
        timer_start = time.perf_counter()
        input_data = self._load_input(input_path)
        config = self._load_config(config_path)
        for warning in config.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        active_tests = self._resolve_tests(config, input_data)
        threshold = self._resolve_threshold(config)
        effective_report = report_path or config.output.report_path
        verbose_output = verbose or config.output.log_results
        overall = self._execute_tests(
            input_path,
            config_path,
            input_data,
            active_tests,
            threshold,
        )
        duration = timedelta(seconds=time.perf_counter() - timer_start)
        run_result = RunResult(
            input_path=input_path,
            config_path=config_path,
            total_entries=input_data.entry_count,
            entry_type=input_data.entry_type,
            overall_confidence=overall.confidence,
            is_random=overall.passed,
            confidence_threshold=overall.threshold / 100.0,
            test_results=overall.tests,
            report_metadata=overall.metadata,
            started_at=started_at,
            duration=duration,
        )
        self._render_summary(run_result, verbose=verbose_output)
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
    ) -> OverallResult:
        weighted_outcomes: List[Tuple[str, float, RawTestResult]] = []
        for test, weight in tests:
            try:
                outcome = test.run(input_data)
            except Exception as exc:  # pragma: no cover - defensive guard
                raise TestExecutionError(f"Test '{test.name}' failed to execute.") from exc
            weighted_outcomes.append((test.name, weight, outcome))

        overall: OverallResult = merge_test_results(
            weighted_outcomes,
            confidence_threshold=threshold,
            entry_type=input_data.entry_type,
        )
        return overall

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    def _render_summary(self, result: RunResult, *, verbose: bool) -> None:
        reporting.print_console_summary(result, verbose=verbose)

    def _render_report(self, result: RunResult, path: Path | None) -> None:
        reporting.write_markdown_report(result, path=path)


__all__ = ["RandomnessCheckerApp", "RunResult", "MergedTestResult"]
