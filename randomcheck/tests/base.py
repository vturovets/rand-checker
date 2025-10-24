"""Common interfaces and data structures for randomness tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..io import InputData


@dataclass(frozen=True)
class TestResult:
    """Result from executing a randomness test."""

    p_value: float
    details: str


class RandomnessTest(Protocol):
    """Protocol implemented by all statistical tests."""

    name: str

    def is_applicable(self, data: InputData) -> bool:
        """Return whether this test can be executed for the provided data."""

    def run(self, data: InputData) -> TestResult:
        """Execute the randomness test returning a p-value and description."""
