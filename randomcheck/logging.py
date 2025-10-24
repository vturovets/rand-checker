"""Utilities for persisting run metadata to structured log files."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import cycle safe typing
    from .app import RunResult


LOG_FIELDNAMES = ("timestamp", "input_file", "result", "confidence", "report_path")
"""Ordered field names used for CSV and JSON payloads."""

DEFAULT_LOG_PATH = Path("logs") / "run_log.jsonl"
"""Default location for the run history log."""


@dataclass(frozen=True)
class RunLogRecord:
    """Structured representation of a logged application run."""

    timestamp: str
    input_file: str
    result: str
    confidence: float
    report_path: str

    @classmethod
    def from_run_result(cls, result: "RunResult", report_path: Path) -> "RunLogRecord":
        """Create a log record from a :class:`~randomcheck.app.RunResult`."""

        timestamp = result.started_at.astimezone(timezone.utc).isoformat()
        verdict = "RANDOM" if result.is_random else "NON-RANDOM"
        return cls(
            timestamp=timestamp,
            input_file=str(result.input_path),
            result=verdict,
            confidence=float(result.overall_confidence),
            report_path=str(report_path),
        )

    def to_dict(self) -> dict[str, str | float]:
        """Serialise the record to a mapping compatible with JSON/CSV writers."""

        return {
            "timestamp": self.timestamp,
            "input_file": self.input_file,
            "result": self.result,
            "confidence": self.confidence,
            "report_path": self.report_path,
        }


def log_run_result(
    result: "RunResult",
    report_path: Path,
    *,
    log_path: Path | None = None,
    fmt: str = "jsonl",
    retention: int | None = 100,
) -> Path:
    """Append ``result`` to the structured log and enforce retention limits."""

    record = RunLogRecord.from_run_result(result, report_path)
    target = _prepare_log_path(log_path)
    normalised_format = fmt.lower()
    if normalised_format not in {"jsonl", "csv"}:
        raise ValueError(f"Unsupported log format: {fmt}")
    _append_record(target, record, normalised_format)
    if retention is not None and retention > 0:
        trim_log(target, retention, fmt=normalised_format)
    return target


def trim_log(path: Path, max_entries: int, *, fmt: str = "jsonl") -> None:
    """Trim ``path`` so only the last ``max_entries`` records remain."""

    if max_entries <= 0:
        return
    if not path.exists():  # Nothing to trim if the log has not been created yet.
        return
    if fmt == "jsonl":
        _trim_jsonl(path, max_entries)
    elif fmt == "csv":
        _trim_csv(path, max_entries)
    else:  # pragma: no cover - defensive guard; format validated earlier
        raise ValueError(f"Unsupported log format: {fmt}")


def _prepare_log_path(path: Path | None) -> Path:
    candidate = Path(path).expanduser() if path is not None else DEFAULT_LOG_PATH
    resolved = candidate.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _append_record(path: Path, record: RunLogRecord, fmt: str) -> None:
    if fmt == "jsonl":
        payload = json.dumps(record.to_dict(), ensure_ascii=False)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(payload + "\n")
    else:
        is_new_file = not path.exists() or path.stat().st_size == 0
        with path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=LOG_FIELDNAMES)
            if is_new_file:
                writer.writeheader()
            writer.writerow(record.to_dict())


def _trim_jsonl(path: Path, max_entries: int) -> None:
    with path.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()
    if len(lines) <= max_entries:
        return
    trimmed = lines[-max_entries:]
    with path.open("w", encoding="utf-8") as handle:
        handle.writelines(trimmed)


def _trim_csv(path: Path, max_entries: int) -> None:
    with path.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()
    if not lines:
        return
    header, *data_lines = lines
    if len(data_lines) <= max_entries:
        return
    trimmed_data = data_lines[-max_entries:]
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(header)
        handle.writelines(trimmed_data)


__all__ = ["RunLogRecord", "log_run_result", "trim_log"]

