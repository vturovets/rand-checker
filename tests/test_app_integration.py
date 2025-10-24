from __future__ import annotations

from pathlib import Path

from randomcheck.app import RandomnessCheckerApp

CONFIG_TEMPLATE = """
[tests]
monobit = true
runs = true

[weights]
monobit = 0.5
runs = 0.5

[output]
log_results = false
confidence_threshold = 0.4
""".strip()


SAMPLE_DATA = """
0101010101010101
1010101010101010
""".strip()


def _write_files(tmp_path: Path) -> tuple[Path, Path]:
    config_path = tmp_path / "config.ini"
    config_path.write_text(CONFIG_TEMPLATE, encoding="utf-8")
    data_path = tmp_path / "data.txt"
    data_path.write_text(SAMPLE_DATA, encoding="utf-8")
    return data_path, config_path


def test_app_run_produces_overall_result(tmp_path: Path) -> None:
    input_path, config_path = _write_files(tmp_path)
    app = RandomnessCheckerApp()

    result = app.run(input_path=input_path, config_path=config_path, verbose=False)

    assert result.total_entries == 2
    assert result.entry_type in {"numeric", "alphanumeric", "mixed"}
    assert len(result.test_results) == 2
    assert result.overall_confidence >= 0.0
    assert result.confidence_threshold == 0.4
