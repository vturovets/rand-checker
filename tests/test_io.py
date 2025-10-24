from __future__ import annotations

from pathlib import Path

import pytest

from randomcheck.errors import EmptyInputFileError, InputTooLargeError, InvalidInputError
from randomcheck.io import classify_entries, read_input_file


def test_read_input_file_numeric_classification(tmp_path: Path) -> None:
    input_path = tmp_path / "data.txt"
    input_path.write_text("123\n456\n", encoding="utf-8")

    data = read_input_file(input_path, max_entries=10_000)

    assert data.entry_type == "numeric"
    assert data.entry_count == 2
    assert data.entries == ("123", "456")


def test_read_input_file_enforces_max_entries(tmp_path: Path) -> None:
    input_path = tmp_path / "data.txt"
    input_path.write_text("\n".join(str(i) for i in range(5)), encoding="utf-8")

    with pytest.raises(InputTooLargeError):
        read_input_file(input_path, max_entries=2)


def test_classify_entries_detects_mixed_sequences() -> None:
    entries = ["abc", "123", "#!"]

    assert classify_entries(entries) == "mixed"


def test_classify_entries_handles_generators() -> None:
    entries = (str(value) for value in range(10))

    assert classify_entries(entries) == "numeric"


def test_classify_entries_rejects_empty_sequences() -> None:
    with pytest.raises(InvalidInputError):
        classify_entries([" ", "\t"])


def test_read_input_file_rejects_empty_files(tmp_path: Path) -> None:
    input_path = tmp_path / "empty.txt"
    input_path.write_text("\n\n", encoding="utf-8")

    with pytest.raises(EmptyInputFileError):
        read_input_file(input_path)
