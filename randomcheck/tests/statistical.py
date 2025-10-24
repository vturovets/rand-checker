"""Concrete implementations of randomness tests."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from ..io import InputData
from .base import RandomnessTest, TestResult
from .utils import (
    build_bit_sequence,
    build_byte_sequence,
    chi_square_sf,
    count_bytes,
    extract_numeric_sequence,
    normalise,
    shannon_entropy_from_counts,
)


@dataclass
class _BaseTest(RandomnessTest):
    name: str

    def is_applicable(self, data: InputData) -> bool:  # pragma: no cover - abstract
        raise NotImplementedError

    def run(self, data: InputData) -> TestResult:  # pragma: no cover - abstract
        raise NotImplementedError


class MonobitTest(_BaseTest):
    def __init__(self) -> None:
        super().__init__(name="monobit")

    def is_applicable(self, data: InputData) -> bool:
        return count_bytes(data) * 8 >= 32

    def run(self, data: InputData) -> TestResult:
        bits = build_bit_sequence(data)
        n = len(bits)
        if n == 0:
            return TestResult(0.0, "No bit data available for monobit test.")
        sum_bits = sum(1 if bit else -1 for bit in bits)
        s_obs = abs(sum_bits) / math.sqrt(n)
        p_value = math.erfc(s_obs / math.sqrt(2))
        details = f"Monobit statistic {s_obs:.3f} over {n} bits."
        return TestResult(max(0.0, min(1.0, p_value)), details)


class RunsTest(_BaseTest):
    def __init__(self) -> None:
        super().__init__(name="runs")

    def is_applicable(self, data: InputData) -> bool:
        return count_bytes(data) * 8 >= 32

    def run(self, data: InputData) -> TestResult:
        bits = build_bit_sequence(data)
        n = len(bits)
        if n < 2:
            return TestResult(0.0, "Not enough bits for runs test.")
        pi = sum(bits) / n
        if abs(pi - 0.5) >= 2 / math.sqrt(n):
            return TestResult(
                0.0,
                "Runs test precondition failed: imbalance in ones and zeros.",
            )
        runs = 1 + sum(1 for idx in range(1, n) if bits[idx] != bits[idx - 1])
        expected = 2 * n * pi * (1 - pi)
        variance = 2 * n * (2 * n - 1) * (pi * (1 - pi))**2 / (n - 1)
        if variance <= 0:
            return TestResult(0.0, "Runs test variance zero; data constant.")
        z = abs(runs - expected) / math.sqrt(variance)
        p_value = math.erfc(z / math.sqrt(2))
        details = f"Observed {runs} runs with expectation {expected:.2f}."
        return TestResult(max(0.0, min(1.0, p_value)), details)


class SerialTest(_BaseTest):
    def __init__(self) -> None:
        super().__init__(name="serial")

    def is_applicable(self, data: InputData) -> bool:
        return count_bytes(data) * 8 >= 32

    def run(self, data: InputData) -> TestResult:
        bits = build_bit_sequence(data)
        n = len(bits)
        if n < 2:
            return TestResult(0.0, "Insufficient bits for serial test.")
        counts = [0, 0, 0, 0]
        for idx in range(n - 1):
            pair = (bits[idx] << 1) | bits[idx + 1]
            counts[pair] += 1
        expected = (n - 1) / 4
        if expected == 0:
            return TestResult(0.0, "Serial test expectation zero.")
        chi_sq = sum(((count - expected) ** 2) / expected for count in counts)
        p_value = chi_square_sf(chi_sq, 3)
        details = "Serial test pair counts: " + ", ".join(str(c) for c in counts)
        return TestResult(max(0.0, min(1.0, p_value)), details)


class ChiSquareTest(_BaseTest):
    def __init__(self) -> None:
        super().__init__(name="chi_square")

    def is_applicable(self, data: InputData) -> bool:
        return count_bytes(data) >= 16

    def run(self, data: InputData) -> TestResult:
        bytes_data = build_byte_sequence(data)
        total = len(bytes_data)
        if total == 0:
            return TestResult(0.0, "No byte data for chi-square test.")
        bucket_count = 16
        counts = [0 for _ in range(bucket_count)]
        for byte in bytes_data:
            counts[byte // 16] += 1
        expected = total / bucket_count
        chi_sq = sum(((count - expected) ** 2) / expected for count in counts if expected > 0)
        p_value = chi_square_sf(chi_sq, bucket_count - 1)
        details = f"Chi-square statistic {chi_sq:.2f} across {bucket_count} buckets."
        return TestResult(max(0.0, min(1.0, p_value)), details)


class EntropyTest(_BaseTest):
    def __init__(self) -> None:
        super().__init__(name="entropy")

    def is_applicable(self, data: InputData) -> bool:
        return len(data.entries) >= 2

    def run(self, data: InputData) -> TestResult:
        total = len(data.entries)
        unique_entries = len(set(data.entries))
        if total == 0:
            return TestResult(0.0, "No entries available for entropy test.")
        if unique_entries <= 1:
            return TestResult(0.0, "All entries identical; entropy zero.")
        diversity = unique_entries / total
        p_value = max(0.0, min(1.0, diversity))
        details = f"{unique_entries} unique entries out of {total}."
        return TestResult(p_value, details)


class AutocorrelationTest(_BaseTest):
    def __init__(self) -> None:
        super().__init__(name="autocorrelation")

    def is_applicable(self, data: InputData) -> bool:
        return count_bytes(data) * 8 >= 64

    def run(self, data: InputData) -> TestResult:
        bits = build_bit_sequence(data)
        n = len(bits)
        if n < 2:
            return TestResult(0.0, "Not enough data for autocorrelation test.")
        mean = sum(bits) / n
        variance = sum((bit - mean) ** 2 for bit in bits) / n
        if variance == 0:
            return TestResult(0.0, "Variance zero; all bits identical.")
        numerator = sum((bits[i] - mean) * (bits[i + 1] - mean) for i in range(n - 1))
        autocorr = numerator / ((n - 1) * variance)
        statistic = abs(autocorr) * math.sqrt(n - 1)
        p_value = math.erfc(statistic / math.sqrt(2))
        details = f"Lag-1 autocorrelation {autocorr:.4f}."
        return TestResult(max(0.0, min(1.0, p_value)), details)


class KolmogorovSmirnovTest(_BaseTest):
    def __init__(self) -> None:
        super().__init__(name="kolmogorov_smirnov")

    def is_applicable(self, data: InputData) -> bool:
        return len(extract_numeric_sequence(data)) >= 10

    def run(self, data: InputData) -> TestResult:
        values = extract_numeric_sequence(data)
        n = len(values)
        if n == 0:
            return TestResult(0.0, "Numeric conversion failed for KS test.")
        if n < 2:
            return TestResult(0.0, "Not enough numeric entries for KS test.")
        minimum, maximum = min(values), max(values)
        if math.isclose(minimum, maximum):
            return TestResult(0.0, "All numeric values identical; KS undefined.")
        scaled = sorted((value - minimum) / (maximum - minimum) for value in values)
        max_diff = 0.0
        for idx, value in enumerate(scaled, start=1):
            empirical = idx / n
            diff = max(abs(empirical - value), abs((idx - 1) / n - value))
            if diff > max_diff:
                max_diff = diff
        statistic = math.sqrt(n) * max_diff
        # Use the first term approximation for the Kolmogorov distribution.
        p_value = 2 * math.exp(-2 * statistic**2)
        p_value = max(0.0, min(1.0, p_value))
        details = f"KS statistic {statistic:.3f} on {n} values."
        return TestResult(p_value, details)


class ShannonEntropyTest(_BaseTest):
    def __init__(self) -> None:
        super().__init__(name="shannon")

    def is_applicable(self, data: InputData) -> bool:
        return count_bytes(data) >= 8

    def run(self, data: InputData) -> TestResult:
        byte_counts = Counter(build_byte_sequence(data))
        total = sum(byte_counts.values())
        if total == 0:
            return TestResult(0.0, "No byte data for Shannon entropy test.")
        entropy = shannon_entropy_from_counts(byte_counts)
        max_entropy = math.log2(len(byte_counts)) if byte_counts else 0.0
        if max_entropy == 0:
            return TestResult(0.0, "Single symbol present; entropy zero.")
        p_value = normalise(entropy, 0.0, max_entropy)
        details = f"Shannon entropy {entropy:.3f} bits (max {max_entropy:.3f})."
        return TestResult(p_value, details)


__all__ = [
    "AutocorrelationTest",
    "ChiSquareTest",
    "EntropyTest",
    "KolmogorovSmirnovTest",
    "MonobitTest",
    "RunsTest",
    "SerialTest",
    "ShannonEntropyTest",
]
