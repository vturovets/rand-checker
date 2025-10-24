"""Command line entry point for the randomness checker application."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .app import RandomnessCheckerApp
from .errors import InvalidConfigurationError, MissingFileError, TestExecutionError

EXIT_SUCCESS = 0
EXIT_MISSING_FILE = 2
EXIT_INVALID_CONFIG = 3
EXIT_TEST_FAILURE = 4
EXIT_UNEXPECTED_ERROR = 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate the randomness of a sequence using configurable heuristics.",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Path to a text file containing the values to analyse.",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        required=True,
        help="Path to the JSON configuration file describing the test suite.",
    )
    parser.add_argument(
        "--report",
        "-r",
        type=Path,
        help="Optional path where a markdown report will be written.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed per-test information to the console output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    app = RandomnessCheckerApp()
    try:
        app.run(
            input_path=args.input,
            config_path=args.config,
            report_path=args.report,
            verbose=args.verbose,
        )
    except MissingFileError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_MISSING_FILE
    except InvalidConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_INVALID_CONFIG
    except TestExecutionError as exc:
        print(f"Test execution failed: {exc}", file=sys.stderr)
        return EXIT_TEST_FAILURE
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return EXIT_UNEXPECTED_ERROR
    return EXIT_SUCCESS


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
