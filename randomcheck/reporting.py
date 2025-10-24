"""Reporting utilities for console and markdown output."""

from __future__ import annotations

import re
import sys
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Sequence, TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from datetime import timedelta
    from .app import RunResult
    from .analysis import MergedTestResult


@dataclass(frozen=True)
class ReportTemplate:
    """Container for the markdown report template."""

    template: Template = Template(
        textwrap.dedent(
            """
            # Randomness Checker Report

            ## Summary
            ${summary}

            ## File Metadata
            ${file_metadata}

            ## Analysis Overview
            ${analysis_overview}

            ## Test Results
            ${test_table}
${test_notes}
            ## Interpretations
            ${interpretations}

            _Generated on ${timestamp} (duration: ${duration})._
            """
        ).strip()
    )


DEFAULT_TEMPLATE = ReportTemplate()


def print_console_summary(result: "RunResult", *, verbose: bool = False, stream: TextIO | None = None) -> None:
    """Print a short summary of the analysis to ``stream``."""

    output = stream if stream is not None else sys.stdout
    status = "RANDOM" if result.is_random else "NON-RANDOM"
    print(f"Result: {status} | Confidence: {result.overall_confidence:.1f}%", file=output)
    if not verbose:
        return

    print(f"Detected entry type: {result.entry_type}", file=output)
    for test_result in result.test_results:
        score_pct = test_result.p_value * 100
        print(
            f" - {test_result.name}: {score_pct:.1f}% (weight {test_result.weight})",
            file=output,
        )
        detail_lines = _format_detail_block(test_result.details)
        for line in detail_lines:
            print(f"   {line}", file=output)
        for note in test_result.metadata:
            print(f"   note: {note}", file=output)
    print(f"Threshold: {result.confidence_threshold * 100:.2f}%", file=output)


def build_markdown_report(result: "RunResult", *, template: Template | None = None) -> str:
    """Generate a markdown report for ``result`` using ``template``."""

    template = template or DEFAULT_TEMPLATE.template
    summary = _format_summary_section(result)
    file_metadata = _format_file_metadata(result)
    analysis_overview = _format_analysis_overview(result)
    test_table = _format_test_table(result.test_results)
    test_notes = _format_test_notes(result.test_results)
    interpretations = _format_interpretations(result.report_metadata)
    timestamp = result.started_at.astimezone(timezone.utc).isoformat()
    duration = _format_duration(result.duration)

    return template.substitute(
        summary=summary,
        file_metadata=file_metadata,
        analysis_overview=analysis_overview,
        test_table=test_table,
        test_notes=test_notes,
        interpretations=interpretations,
        timestamp=timestamp,
        duration=duration,
    )


def write_markdown_report(
    result: "RunResult",
    path: Path | None = None,
    *,
    template: Template | None = None,
) -> Path:
    """Render and persist a markdown report for ``result``."""

    target = _resolve_report_path(result, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = build_markdown_report(result, template=template)
    target.write_text(content, encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Helper formatting utilities
# ---------------------------------------------------------------------------

def _format_detail_block(details: str) -> Sequence[str]:
    stripped = details.strip()
    if not stripped:
        return ("",)
    return tuple(line for line in stripped.splitlines())


def _format_summary_section(result: "RunResult") -> str:
    verdict = "RANDOM" if result.is_random else "NON-RANDOM"
    return textwrap.dedent(
        f"""
        - **Result:** {verdict}
        - **Weighted confidence:** {result.overall_confidence:.2f}%
        - **Confidence threshold:** {result.confidence_threshold * 100:.2f}%
        """
    ).strip()


def _format_file_metadata(result: "RunResult") -> str:
    lines = [
        _metadata_line("Input", result.input_path),
        _metadata_line("Configuration", result.config_path),
        f"- **Total entries:** {result.total_entries}",
    ]
    return "\n".join(lines)


def _metadata_line(label: str, path: Path) -> str:
    try:
        stat = path.stat()
        modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        details = f"size: {stat.st_size} bytes, modified: {modified.isoformat()}"
    except OSError:
        details = "metadata unavailable"
    return f"- **{label} file:** {path} ({details})"


def _format_analysis_overview(result: "RunResult") -> str:
    lines = [
        f"- **Entry type:** {result.entry_type}",
        f"- **Tests executed:** {len(result.test_results)}",
    ]
    return "\n".join(lines)


def _format_test_table(tests: Sequence["MergedTestResult"]) -> str:
    header = "| Test | Weight | P-Value (%) | Threshold (%) | Outcome |"
    separator = "| --- | --- | --- | --- | --- |"
    rows = [
        "| {} | {:.3f} | {:.2f} | {:.2f} | {} |".format(
            test.name,
            test.weight,
            test.p_value * 100,
            test.threshold * 100,
            "PASS" if test.passed else "FAIL",
        )
        for test in tests
    ]
    if not rows:
        rows.append("| _(no tests executed)_ | - | - | - | - |")
    return "\n".join([header, separator, *rows])


def _format_test_notes(tests: Sequence["MergedTestResult"]) -> str:
    sections: list[str] = []
    for test in tests:
        notes = list(test.metadata)
        detail_lines = _format_detail_block(test.details)
        if not notes and all(not line.strip() for line in detail_lines):
            continue
        section_lines = [f"### {test.name}"]
        if any(line.strip() for line in detail_lines):
            section_lines.append("Details:")
            section_lines.extend(f"> {line}" if line else ">" for line in detail_lines)
        if notes:
            section_lines.append("Notes:")
            section_lines.extend(f"- {note}" for note in notes)
        sections.append("\n".join(section_lines))
    if not sections:
        return "\n"
    return "\n\n" + "\n\n".join(sections) + "\n"


def _format_interpretations(metadata: Sequence[str]) -> str:
    if not metadata:
        return "- No additional interpretations were recorded."
    return "\n".join(f"- {note}" for note in metadata)


def _format_duration(duration: "timedelta") -> str:
    total_seconds = duration.total_seconds()
    if total_seconds < 1:
        return f"{total_seconds * 1000:.0f} ms"
    return f"{total_seconds:.2f} s"


def _resolve_report_path(result: "RunResult", path: Path | None) -> Path:
    if path is not None:
        return Path(path).expanduser().resolve()
    base_dir = Path("reports")
    stem = result.input_path.stem or result.input_path.name or "analysis"
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", stem).strip("-") or "analysis"
    timestamp = result.started_at.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"{safe_stem}-{timestamp}.md"
    return (base_dir / filename).resolve()


__all__ = [
    "print_console_summary",
    "build_markdown_report",
    "write_markdown_report",
    "ReportTemplate",
]
