from __future__ import annotations

from pathlib import Path

import pytest

from randomcheck.config import load_config
from randomcheck.errors import InvalidConfigurationError


BASE_CONFIG = """
[tests]
monobit = true

[weights]
monobit = 1.0
""".strip()


def _write_config(tmp_path: Path, content: str) -> Path:
    config_path = tmp_path / "config.ini"
    config_path.write_text(content, encoding="utf-8")
    return config_path


def test_output_section_includes_logging_defaults(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path,
        BASE_CONFIG
        + "\n\n[output]\nlog_results = true\nlog_format = csv\nlog_retention = 5\nlog_path = logs/history.csv\n",
    )

    config = load_config(config_path)

    assert config.output.log_results is True
    assert config.output.run_log_format == "csv"
    assert config.output.run_log_retention == 5
    expected_path = (tmp_path / "logs" / "history.csv").resolve()
    assert config.output.run_log_path == expected_path


def test_logging_section_overrides_output(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path,
        BASE_CONFIG
        + "\n\n[output]\nlog_results = false\n"
        + "\n[logging]\nenabled = true\nformat = jsonl\nretention = 0\npath = custom/run.jsonl\n",
    )

    config = load_config(config_path)

    assert config.output.log_results is True  # overridden by [logging]
    assert config.output.run_log_format == "jsonl"
    assert config.output.run_log_retention is None
    expected_path = (tmp_path / "custom" / "run.jsonl").resolve()
    assert config.output.run_log_path == expected_path


def test_invalid_logging_format_raises(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path,
        BASE_CONFIG + "\n\n[logging]\nformat = invalid\n",
    )

    with pytest.raises(InvalidConfigurationError):
        load_config(config_path)
