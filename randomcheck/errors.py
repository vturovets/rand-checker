"""Custom exceptions for the randomness checker application."""

from __future__ import annotations


class RandomnessCheckerError(Exception):
    """Base error type for application specific failures."""


class MissingFileError(RandomnessCheckerError):
    """Raised when a required input file could not be located."""


class InvalidConfigurationError(RandomnessCheckerError):
    """Raised when the configuration file is malformed or invalid."""


class TestExecutionError(RandomnessCheckerError):
    """Raised when one or more randomness tests fail to execute."""
