"""Input/output helpers for reading and classifying randomness data files."""

from __future__ import annotations

"""Input/output helpers for reading and classifying randomness data files."""

import re
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Iterable, Literal, Tuple

from .errors import (
    EmptyInputFileError,
    InputTooLargeError,
    InvalidInputError,
    MissingFileError,
)

EntryType = Literal["numeric", "alphabetic", "alphanumeric", "mixed"]
EntryCategory = Literal["numeric", "alphabetic", "alphanumeric", "mixed", "empty"]

DEFAULT_MAX_ENTRIES = 100_000


@dataclass(frozen=True)
class InputData:
    """Container describing the data loaded from an input file."""

    entries: Tuple[str, ...]
    raw_lines: Tuple[str, ...]
    entry_type: EntryType

    @property
    def entry_count(self) -> int:
        return len(self.entries)


NUMERIC_PATTERN = re.compile(
    r"""
    ^
    [+-]?
    (
        (?:\d+\.\d+)|
        (?:\d+\.)|
        (?:\.\d+)|
        (?:\d+)
    )
    (?:[eE][+-]?\d+)?
    $
    """,
    re.VERBOSE,
)

ALPHA_PATTERN = re.compile(r"^[A-Za-z]+$")
ALNUM_PATTERN = re.compile(r"^[A-Za-z0-9]+$")


def read_input_file(path: Path | str, *, max_entries: int = DEFAULT_MAX_ENTRIES) -> InputData:
    """Read and classify entries from ``path`` using UTF-8 encoding."""

    candidate = _normalise_path(path)
    if not candidate.exists():
        raise MissingFileError(f"Input file not found: {candidate}")
    try:
        with candidate.open("r", encoding="utf-8", newline="") as handle:
            raw_lines = tuple(handle.readlines())
    except OSError as exc:  # pragma: no cover - filesystem guard
        raise MissingFileError(f"Could not read input file: {candidate}") from exc

    entries = tuple(line.rstrip("\r\n") for line in raw_lines)
    if not entries or all(not entry.strip() for entry in entries):
        raise EmptyInputFileError(
            f"Input file '{candidate}' does not contain any non-empty entries."
        )

    if max_entries is not None and len(entries) > max_entries:
        raise InputTooLargeError(
            f"Input file '{candidate}' has {len(entries)} entries, exceeding the allowed maximum of {max_entries}."
        )

    entry_type = classify_entries(entries)
    return InputData(entries=entries, raw_lines=raw_lines, entry_type=entry_type)


def classify_entries(entries: Iterable[str]) -> EntryType:
    """Infer the dominant data type for the provided ``entries``."""

    categories = {_classify_entry(entry) for entry in entries}
    categories.discard("empty")
    if not categories:
        raise InvalidInputError("Unable to classify entries because they are empty.")
    if "mixed" in categories:
        return "mixed"
    if categories <= {"numeric"}:
        return "numeric"
    if categories <= {"alphabetic"}:
        return "alphabetic"
    if categories <= {"numeric", "alphabetic", "alphanumeric"}:
        return "alphanumeric"
    return "mixed"


def _classify_entry(entry: str) -> EntryCategory:
    stripped = entry.strip()
    if not stripped:
        return "empty"
    if NUMERIC_PATTERN.match(stripped):
        return "numeric"
    if ALPHA_PATTERN.match(stripped):
        return "alphabetic"
    if ALNUM_PATTERN.match(stripped):
        return "alphanumeric"
    return "mixed"


def _normalise_path(path: Path | str) -> Path:
    if isinstance(path, Path):
        candidate = path
    else:
        candidate = Path(path)
    if isinstance(path, str) and re.match(r"^[A-Za-z]:\\", path):
        return Path(PureWindowsPath(path))
    return candidate.expanduser().resolve()


__all__ = [
    "EntryType",
    "InputData",
    "classify_entries",
    "read_input_file",
]
