"""Utility helpers shared by statistical randomness tests."""

from __future__ import annotations

import math
from collections import Counter
from typing import Iterable, List

from ..io import InputData


def extract_numeric_sequence(data: InputData) -> List[float]:
    """Convert entries to floats when possible."""

    values: List[float] = []
    for entry in data.entries:
        try:
            values.append(float(entry))
        except ValueError:
            return []
    return values


def iter_bytes(data: InputData) -> Iterable[int]:
    """Yield the UTF-8 encoded bytes for the provided entries."""

    for entry in data.entries:
        for value in entry.encode("utf-8", errors="ignore"):
            yield value


def build_byte_sequence(data: InputData) -> List[int]:
    """Return a cached list of bytes derived from the input data."""

    return list(iter_bytes(data))


def count_bytes(data: InputData) -> int:
    """Return the number of UTF-8 bytes represented by the entries."""

    return sum(len(entry.encode("utf-8", errors="ignore")) for entry in data.entries)


def build_bit_sequence(data: InputData) -> List[int]:
    """Return a list of individual bits derived from the UTF-8 bytes."""

    bits: List[int] = []
    for byte in iter_bytes(data):
        for offset in range(8):
            bits.append((byte >> (7 - offset)) & 1)
    return bits


def chi_square_sf(statistic: float, degrees_of_freedom: int) -> float:
    """Return survival function for the chi-square distribution (integer dof)."""

    if statistic < 0 or degrees_of_freedom <= 0:
        return 1.0
    k = degrees_of_freedom // 2
    if degrees_of_freedom % 2 != 0:
        # For odd degrees, use a simple approximation based on regularised gamma.
        # The approximation is sufficient for heuristic scoring without SciPy.
        half = degrees_of_freedom / 2.0
        x = statistic / 2.0
        term = math.exp(-x)
        total = term
        for i in range(1, 10):
            term *= x / (half + i - 1)
            total += term
        return min(1.0, max(0.0, total))
    x = statistic / 2.0
    term = math.exp(-x)
    total = term
    for i in range(1, k):
        term *= x / i
        total += term
    return min(1.0, max(0.0, total))


def normalise(value: float, lower: float, upper: float) -> float:
    """Normalise ``value`` into the [0, 1] range."""

    if upper <= lower:
        return 0.0
    return max(0.0, min(1.0, (value - lower) / (upper - lower)))


def shannon_entropy_from_counts(counts: Counter[int]) -> float:
    """Compute Shannon entropy from symbol counts."""

    total = sum(counts.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        probability = count / total
        if probability > 0:
            entropy -= probability * math.log2(probability)
    return entropy
