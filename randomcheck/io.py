"""Input/output helpers for reading and classifying randomness data files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
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

    entries = _strip_newlines(raw_lines)
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

    has_numeric = False
    has_alphabetic = False
    has_alphanumeric = False
    observed = False

    for entry in entries:
        category = _classify_entry_cached(entry)
        if category == "empty":
            continue
        observed = True
        if category == "mixed":
            return "mixed"
        if category == "numeric":
            has_numeric = True
        elif category == "alphabetic":
            has_alphabetic = True
        elif category == "alphanumeric":
            has_alphanumeric = True

    if not observed:
        raise InvalidInputError("Unable to classify entries because they are empty.")
    if has_numeric and not (has_alphabetic or has_alphanumeric):
        return "numeric"
    if has_alphabetic and not (has_numeric or has_alphanumeric):
        return "alphabetic"
    if has_numeric or has_alphabetic or has_alphanumeric:
        return "alphanumeric"
    return "mixed"


def _classify_entry(entry: str) -> EntryCategory:
    stripped = entry.strip()
    if not stripped:
        return "empty"
    if NUMERIC_PATTERN.fullmatch(stripped):
        return "numeric"
    if ALPHA_PATTERN.fullmatch(stripped):
        return "alphabetic"
    if ALNUM_PATTERN.fullmatch(stripped):
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


def _strip_newlines(raw_lines: Tuple[str, ...]) -> Tuple[str, ...]:
    """Strip trailing newline characters while preserving tuple semantics."""

    # Tuples are used to retain immutability guarantees for downstream stages.
    return tuple(line.rstrip("\r\n") for line in raw_lines)


@lru_cache(maxsize=2048)
def _classify_entry_cached(entry: str) -> EntryCategory:
    """Memoized wrapper around :func:`_classify_entry` for repeated tokens."""

    return _classify_entry(entry)


__all__ = [
    "EntryType",
    "InputData",
    "classify_entries",
    "read_input_file",
]
