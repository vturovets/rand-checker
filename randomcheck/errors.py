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


class InvalidInputError(RandomnessCheckerError):
    """Raised when the provided input data does not meet application constraints."""


class EmptyInputFileError(InvalidInputError):
    """Raised when the input file does not contain any usable entries."""


class InputTooLargeError(InvalidInputError):
    """Raised when the input file exceeds the supported number of entries."""
