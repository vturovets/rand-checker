"""Tests for :mod:`randomcheck.reporting`."""

from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from randomcheck import reporting
from randomcheck.analysis import MergedTestResult
from randomcheck.app import RunResult


def _build_run_result(tmp_path: Path) -> RunResult:
    input_path = tmp_path / "data.csv"
    input_path.write_text("1\n2\n", encoding="utf-8")
    config_path = tmp_path / "config.ini"
    config_path.write_text("[tests]\n", encoding="utf-8")
    started_at = datetime(2023, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    test_result = MergedTestResult(
        name="frequency",
        p_value=0.8123,
        weight=0.5,
        passed=True,
        threshold=0.05,
        details="All good",
        metadata=("note about data",),
    )
    return RunResult(
        input_path=input_path,
        config_path=config_path,
        total_entries=2,
        entry_type="numeric",
        overall_confidence=81.23,
        is_random=True,
        confidence_threshold=0.7,
        test_results=(test_result,),
        report_metadata=("Interpretation 1",),
        started_at=started_at,
        duration=timedelta(seconds=1.234),
    )


def test_print_console_summary_verbose(tmp_path: Path) -> None:
    result = _build_run_result(tmp_path)
    buffer = io.StringIO()
    reporting.print_console_summary(result, verbose=True, stream=buffer)
    output = buffer.getvalue()

    assert "Result: RANDOM | Confidence: 81.2%" in output
    assert "Detected entry type: numeric" in output
    assert "frequency" in output
    assert "All good" in output
    assert "note about data" in output
    assert "Threshold: 70.00%" in output


def test_write_markdown_report_default_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _build_run_result(tmp_path)
    monkeypatch.chdir(tmp_path)

    report_path = reporting.write_markdown_report(result)

    expected = (tmp_path / "reports" / "data-20230102-030405.md").resolve()
    assert report_path == expected
    content = report_path.read_text(encoding="utf-8")

    assert "# Randomness Checker Report" in content
    assert "- **Result:** RANDOM" in content
    assert "- **Total entries:** 2" in content
    assert "| Test | Weight | P-Value (%) |" in content
    assert "Interpretation 1" in content
    assert "Generated on 2023-01-02T03:04:05+00:00 (duration: 1.23 s)" in content
    assert "note about data" in content


def test_write_markdown_report_custom_path(tmp_path: Path) -> None:
    result = _build_run_result(tmp_path)
    custom_path = tmp_path / "custom" / "report.md"

    written_path = reporting.write_markdown_report(result, path=custom_path)

    assert written_path == custom_path
    assert custom_path.exists()
