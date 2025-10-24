from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from randomcheck.app import RunResult
from randomcheck.logging import log_run_result


def _make_run_result(base_dir: Path, *, is_random: bool = True, idx: int = 0) -> RunResult:
    started_at = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=idx)
    return RunResult(
        input_path=base_dir / f"input-{idx}.txt",
        config_path=base_dir / "config.ini",
        total_entries=10,
        entry_type="numeric",
        overall_confidence=87.5,
        is_random=is_random,
        confidence_threshold=0.6,
        test_results=(),
        report_metadata=(),
        started_at=started_at,
        duration=timedelta(seconds=5),
    )


def test_log_run_result_appends_jsonl(tmp_path: Path) -> None:
    report_path = tmp_path / "report.md"
    result = _make_run_result(tmp_path)

    log_file = log_run_result(result, report_path, log_path=tmp_path / "log.jsonl", fmt="jsonl")

    assert log_file.exists()
    payload = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(payload) == 1
    entry = json.loads(payload[0])
    assert entry["result"] == "RANDOM"
    assert pytest.approx(entry["confidence"], rel=1e-6) == 87.5
    assert entry["report_path"] == str(report_path)


def test_log_run_result_enforces_jsonl_retention(tmp_path: Path) -> None:
    log_path = tmp_path / "history.jsonl"
    report_path = tmp_path / "report.md"

    for idx in range(5):
        result = _make_run_result(tmp_path, idx=idx)
        log_run_result(result, report_path, log_path=log_path, fmt="jsonl", retention=3)

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    timestamps = [json.loads(line)["timestamp"] for line in lines]
    assert timestamps == sorted(timestamps)


def test_log_run_result_supports_csv(tmp_path: Path) -> None:
    report_path = tmp_path / "report.md"
    log_path = tmp_path / "runs.csv"
    result = _make_run_result(tmp_path, is_random=False)

    log_run_result(result, report_path, log_path=log_path, fmt="csv", retention=5)

    content = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert content[0] == "timestamp,input_file,result,confidence,report_path"
    assert len(content) == 2
    row = content[1].split(",")
    assert row[2] == "NON-RANDOM"


def test_log_run_result_enforces_csv_retention(tmp_path: Path) -> None:
    report_path = tmp_path / "report.md"
    log_path = tmp_path / "runs.csv"

    for idx in range(6):
        result = _make_run_result(tmp_path, idx=idx)
        log_run_result(result, report_path, log_path=log_path, fmt="csv", retention=2)

    content = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(content) == 3  # header + two retained rows
    timestamps = [row.split(",")[0] for row in content[1:]]
    assert timestamps == sorted(timestamps)
