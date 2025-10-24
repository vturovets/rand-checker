"""Configuration parsing utilities for the randomness checker."""

from __future__ import annotations

import configparser
import math
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Tuple

from .errors import InvalidConfigurationError, MissingFileError


@dataclass(frozen=True)
class TestsSection:
    """Configuration data describing which tests are enabled."""

    enabled_tests: Tuple[str, ...]


@dataclass(frozen=True)
class WeightsSection:
    """Normalised weighting information for the configured tests."""

    values: Mapping[str, float]
    normalised: bool = False


@dataclass(frozen=True)
class OutputSection:
    """Options controlling how results should be presented to the user."""

    log_results: bool
    confidence_threshold: float
    report_path: Path | None


@dataclass(frozen=True)
class RandomCheckConfig:
    """Aggregate configuration container returned by :func:`load_config`."""

    tests: TestsSection
    weights: WeightsSection
    output: OutputSection
    warnings: Tuple[str, ...] = field(default_factory=tuple)


def load_config(path: Path) -> RandomCheckConfig:
    """Load and validate an INI configuration file."""

    parser = configparser.ConfigParser()
    try:
        with path.open("r", encoding="utf-8") as config_file:
            parser.read_file(config_file)
    except FileNotFoundError as exc:  # pragma: no cover - filesystem guard
        raise MissingFileError(f"Configuration file not found: {path}") from exc
    except OSError as exc:  # pragma: no cover - filesystem guard
        raise MissingFileError(f"Could not read configuration file: {path}") from exc

    tests_section = _parse_tests(parser)
    weights_section, warnings = _parse_weights(parser, tests_section)
    output_section = _parse_output(parser, path)

    return RandomCheckConfig(
        tests=tests_section,
        weights=weights_section,
        output=output_section,
        warnings=tuple(warnings),
    )


def _parse_tests(parser: configparser.ConfigParser) -> TestsSection:
    if not parser.has_section("tests"):
        raise InvalidConfigurationError("Configuration missing required [tests] section.")

    enabled: list[str] = []
    for name, _ in parser.items("tests"):
        try:
            is_enabled = parser.getboolean("tests", name)
        except ValueError as exc:
            raise InvalidConfigurationError(
                f"Test '{name}' in [tests] must be a boolean value."
            ) from exc
        if is_enabled:
            enabled.append(name)

    if not enabled:
        raise InvalidConfigurationError("At least one test must be enabled in [tests] section.")

    return TestsSection(enabled_tests=tuple(enabled))


def _parse_weights(
    parser: configparser.ConfigParser, tests: TestsSection
) -> tuple[WeightsSection, list[str]]:
    if not parser.has_section("weights"):
        raise InvalidConfigurationError("Configuration missing required [weights] section.")

    raw_weights: dict[str, float] = {}
    for name, value in parser.items("weights"):
        try:
            weight = float(value)
        except ValueError as exc:
            raise InvalidConfigurationError(
                f"Weight for test '{name}' must be a numeric value."
            ) from exc
        if weight <= 0:
            raise InvalidConfigurationError(
                f"Weight for test '{name}' must be greater than zero."
            )
        raw_weights[name] = weight

    missing_weights = [name for name in tests.enabled_tests if name not in raw_weights]
    if missing_weights:
        formatted = ", ".join(sorted(missing_weights))
        raise InvalidConfigurationError(
            f"Missing weight entries for enabled tests: {formatted}."
        )

    enabled_weights = {name: raw_weights[name] for name in tests.enabled_tests}
    total_weight = sum(enabled_weights.values())
    if total_weight <= 0:
        raise InvalidConfigurationError("Sum of enabled test weights must be greater than zero.")

    warnings: list[str] = []
    normalised = False
    if not math.isclose(total_weight, 1.0, rel_tol=1e-9, abs_tol=1e-9):
        normalised = True
        enabled_weights = {
            name: value / total_weight for name, value in enabled_weights.items()
        }
        warnings.append(
            "Weights for enabled tests did not sum to 1.0; normalised automatically."
        )

    weights_section = WeightsSection(
        values=MappingProxyType(dict(enabled_weights)),
        normalised=normalised,
    )
    return weights_section, warnings


def _parse_output(
    parser: configparser.ConfigParser, config_path: Path
) -> OutputSection:
    log_results = False
    confidence_threshold = 0.6
    report_path: Path | None = None

    if parser.has_section("output"):
        section = parser["output"]
        if "log_results" in section:
            try:
                log_results = section.getboolean("log_results")
            except ValueError as exc:
                raise InvalidConfigurationError(
                    "Option 'log_results' in [output] must be a boolean value."
                ) from exc
        if "confidence_threshold" in section:
            raw_threshold = section["confidence_threshold"].strip()
            try:
                confidence_threshold = float(raw_threshold)
            except ValueError as exc:
                raise InvalidConfigurationError(
                    "Option 'confidence_threshold' in [output] must be numeric."
                ) from exc
        if "report_path" in section:
            raw_report = section["report_path"].strip()
            if raw_report:
                candidate = Path(raw_report).expanduser()
                if not candidate.is_absolute():
                    candidate = (config_path.parent / candidate).resolve()
                report_path = candidate

    if not 0.0 <= confidence_threshold <= 1.0:
        raise InvalidConfigurationError(
            "Option 'confidence_threshold' in [output] must be between 0 and 1."
        )

    return OutputSection(
        log_results=log_results,
        confidence_threshold=confidence_threshold,
        report_path=report_path,
    )


__all__ = [
    "RandomCheckConfig",
    "TestsSection",
    "WeightsSection",
    "OutputSection",
    "load_config",
]
